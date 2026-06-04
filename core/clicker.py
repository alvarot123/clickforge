from __future__ import annotations

import importlib
import threading
import time
from collections import deque
from dataclasses import asdict
from dataclasses import dataclass
from typing import Any, Callable


CoreEventCallback = Callable[[str, dict], None]


SPECIAL_KEY_ALIASES = {
    "caps_lock": "capslock",
    "page_up": "pageup",
    "page_down": "pagedown",
    "num_lock": "numlock",
    "print_screen": "printscreen",
    "scroll_lock": "scrolllock",
}


DISPLAY_LABELS = {
    "capslock": "Caps Lock",
    "delete": "Delete",
    "down": "Down",
    "end": "End",
    "enter": "Enter",
    "esc": "Esc",
    "home": "Home",
    "insert": "Insert",
    "left": "Left",
    "pagedown": "Page Down",
    "pageup": "Page Up",
    "right": "Right",
    "space": "Space",
    "tab": "Tab",
    "up": "Up",
}


def normalize_hotkey_name(name: str) -> str:
    value = (name or "").strip().lower().replace(" ", "_")
    return SPECIAL_KEY_ALIASES.get(value, value)


def hotkey_label(name: str) -> str:
    normalized = normalize_hotkey_name(name)
    if not normalized:
        return "Unassigned"
    if normalized in DISPLAY_LABELS:
        return DISPLAY_LABELS[normalized]
    if normalized.startswith("f") and normalized[1:].isdigit():
        return normalized.upper()
    if len(normalized) == 1:
        return normalized.upper()
    return normalized.replace("_", " ").title()


def _pynput_keyboard_module() -> Any:
    return importlib.import_module("pynput.keyboard")


def _pynput_mouse_module() -> Any:
    return importlib.import_module("pynput.mouse")


def _mouse_button(button_name: str) -> Any:
    mouse_module = _pynput_mouse_module()
    button_map = {
        "left": mouse_module.Button.left,
        "middle": mouse_module.Button.middle,
        "right": mouse_module.Button.right,
    }
    return button_map.get(button_name, mouse_module.Button.left)


def hotkey_name_from_pynput(key: Any) -> str | None:
    keyboard_module = _pynput_keyboard_module()
    if isinstance(key, keyboard_module.KeyCode):
        if key.char:
            return normalize_hotkey_name(key.char)
        if key.vk is not None:
            return normalize_hotkey_name(str(key.vk))
        return None

    key_name = getattr(key, "name", None) or str(key).split(".")[-1]
    return normalize_hotkey_name(key_name)


@dataclass(slots=True)
class ClickConfig:
    cps: float = 10.0
    stop_at: int = 0
    hotkey: str = "f6"
    mode: str = "toggle"
    mouse_button: str = "left"
    position_mode: str = "cursor"
    fixed_x: int = 0
    fixed_y: int = 0


class AutoClicker:
    def __init__(self, config: ClickConfig | None = None) -> None:
        self._config = config or ClickConfig()
        self._mouse = _pynput_mouse_module().Controller()
        self._callback: CoreEventCallback | None = None
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._running = False
        self._click_count = 0
        self._recent_clicks: deque[float] = deque(maxlen=256)
        self._last_error: str | None = None

    def set_event_callback(self, callback: CoreEventCallback | None) -> None:
        self._callback = callback

    def update_config(self, config: ClickConfig) -> None:
        with self._lock:
            self._config = config

    def validate(self) -> tuple[bool, str | None]:
        with self._lock:
            cps = self._config.cps
        if cps < 0.1 or cps > 50:
            return False, "CPS must be between 0.1 and 50."
        return True, None

    def start(self) -> bool:
        valid, error = self.validate()
        if not valid:
            self._set_error(error or "Invalid configuration.")
            return False

        with self._lock:
            if self._running:
                return True
            self._stop_event.clear()
            self._running = True
            self._last_error = None
            self._thread = threading.Thread(target=self._run_loop, name="clickforge-clicker", daemon=True)
            self._thread.start()

        self._emit("started", {"cps": self.config.cps})
        return True

    def stop(self, reset_counter: bool = False, reason: str = "manual") -> None:
        thread: threading.Thread | None = None
        with self._lock:
            was_running = self._running
            self._running = False
            self._stop_event.set()
            thread = self._thread

        if thread and thread.is_alive() and threading.current_thread() is not thread:
            thread.join(timeout=0.5)

        if reset_counter:
            with self._lock:
                self._click_count = 0
                self._recent_clicks.clear()

        if was_running or reset_counter:
            self._emit("stopped", {"reason": reason, "reset": reset_counter})

    def toggle(self) -> bool:
        if self.is_running:
            self.stop(reason="toggle")
            return False
        return self.start()

    @property
    def config(self) -> ClickConfig:
        with self._lock:
            return ClickConfig(**asdict(self._config))

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running

    @property
    def click_count(self) -> int:
        with self._lock:
            return self._click_count

    @property
    def last_error(self) -> str | None:
        with self._lock:
            return self._last_error

    def real_cps(self) -> float:
        now = time.monotonic()
        with self._lock:
            while self._recent_clicks and now - self._recent_clicks[0] > 1.0:
                self._recent_clicks.popleft()
            return float(len(self._recent_clicks))

    def _run_loop(self) -> None:
        try:
            while not self._stop_event.is_set():
                with self._lock:
                    config = ClickConfig(**asdict(self._config))
                    count = self._click_count

                if config.stop_at > 0 and count >= config.stop_at:
                    self.stop(reason="target_reached")
                    self._emit("target_reached", {"count": count})
                    break

                interval = max(1.0 / config.cps, 0.001)
                button = _mouse_button(config.mouse_button)

                if config.position_mode == "fixed":
                    self._mouse.position = (config.fixed_x, config.fixed_y)

                self._mouse.click(button)

                with self._lock:
                    self._click_count += 1
                    self._recent_clicks.append(time.monotonic())

                time.sleep(interval)
        except Exception as exc:  # pragma: no cover
            self._set_error(str(exc))
            self.stop(reason="error")
            self._emit("error", {"message": str(exc)})
        finally:
            with self._lock:
                self._running = False
                self._thread = None
                self._stop_event.set()

    def _set_error(self, message: str) -> None:
        with self._lock:
            self._last_error = message
        self._emit("error", {"message": message})

    def _emit(self, event: str, payload: dict) -> None:
        if self._callback:
            self._callback(event, payload)


class GlobalHotkeyManager:
    def __init__(self, clicker: AutoClicker) -> None:
        self._clicker = clicker
        self._callback: CoreEventCallback | None = None
        self._hotkey_name = normalize_hotkey_name(clicker.config.hotkey)
        self._listener: Any | None = None
        self._lock = threading.RLock()
        self._esc_pressed_at: float | None = None
        self._hold_is_active = False
        self._emergency_fired = False
        self._monitor_stop = threading.Event()
        self._monitor_thread = threading.Thread(
            target=self._emergency_monitor,
            name="clickforge-esc-monitor",
            daemon=True,
        )
        self._monitor_thread.start()

    def set_event_callback(self, callback: CoreEventCallback | None) -> None:
        self._callback = callback

    def start(self) -> None:
        if self._listener:
            return
        keyboard_module = _pynput_keyboard_module()
        self._listener = keyboard_module.Listener(on_press=self._on_press, on_release=self._on_release)
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        self._monitor_stop.set()
        if self._listener:
            self._listener.stop()
            self._listener = None

    def update_hotkey(self, hotkey_name: str) -> None:
        with self._lock:
            self._hotkey_name = normalize_hotkey_name(hotkey_name)
        self._emit("hotkey_changed", {"hotkey": self._hotkey_name})

    def _on_press(self, key: Any) -> None:
        key_name = hotkey_name_from_pynput(key)
        if key_name == "esc":
            with self._lock:
                if self._esc_pressed_at is None:
                    self._esc_pressed_at = time.monotonic()
                    self._emergency_fired = False

        with self._lock:
            hotkey_name = self._hotkey_name

        if key_name != hotkey_name:
            return

        mode = self._clicker.config.mode
        if mode == "hold":
            if not self._hold_is_active:
                self._hold_is_active = True
                if self._clicker.start():
                    self._emit("hotkey_triggered", {"mode": "hold"})
            return

        if self._clicker.toggle():
            self._emit("hotkey_triggered", {"mode": "toggle", "state": "running"})
        else:
            self._emit("hotkey_triggered", {"mode": "toggle", "state": "stopped"})

    def _on_release(self, key: Any) -> None:
        key_name = hotkey_name_from_pynput(key)
        if key_name == "esc":
            with self._lock:
                self._esc_pressed_at = None
                self._emergency_fired = False

        if key_name != self._hotkey_name:
            return

        if self._clicker.config.mode == "hold" and self._hold_is_active:
            self._hold_is_active = False
            self._clicker.stop(reason="hold_release")
            self._emit("hotkey_released", {"mode": "hold"})

    def _emergency_monitor(self) -> None:
        while not self._monitor_stop.is_set():
            time.sleep(0.1)
            with self._lock:
                esc_pressed_at = self._esc_pressed_at
                emergency_fired = self._emergency_fired
            if esc_pressed_at is None or emergency_fired:
                continue
            if time.monotonic() - esc_pressed_at >= 2.0:
                self._clicker.stop(reason="emergency")
                with self._lock:
                    self._emergency_fired = True
                self._emit("emergency_stop", {"message": "ESC held for 2 seconds."})

    def _emit(self, event: str, payload: dict) -> None:
        if self._callback:
            self._callback(event, payload)
