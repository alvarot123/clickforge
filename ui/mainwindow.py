from __future__ import annotations

import sys
import urllib.request
from datetime import datetime
from importlib import import_module
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QEasingCurve, QObject, QPoint, QPropertyAnimation, QTimer, Qt, pyqtSignal
from PyQt6.QtCore import QLocale
from PyQt6.QtGui import QCloseEvent, QFont, QFontDatabase, QIcon, QKeyEvent
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QScrollArea,
)

CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app_meta import APP_NAME, APP_VERSION  # noqa: E402
from core.clicker import (  # noqa: E402
    AutoClicker,
    ClickConfig,
    GlobalHotkeyManager,
    hotkey_label,
    normalize_hotkey_name,
)
from core.settings import AppSettings, SettingsStore  # noqa: E402


FONT_SOURCES = {
    "Inter": "https://raw.githubusercontent.com/google/fonts/main/ofl/inter/Inter%5Bopsz,wght%5D.ttf",
    "JetBrains Mono": "https://raw.githubusercontent.com/google/fonts/main/ofl/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf",
}


SPECIAL_QT_KEYS = {
    Qt.Key.Key_Space: "space",
    Qt.Key.Key_Tab: "tab",
    Qt.Key.Key_Return: "enter",
    Qt.Key.Key_Enter: "enter",
    Qt.Key.Key_Escape: "esc",
    Qt.Key.Key_Delete: "delete",
    Qt.Key.Key_Insert: "insert",
    Qt.Key.Key_Home: "home",
    Qt.Key.Key_End: "end",
    Qt.Key.Key_PageUp: "pageup",
    Qt.Key.Key_PageDown: "pagedown",
    Qt.Key.Key_Left: "left",
    Qt.Key.Key_Right: "right",
    Qt.Key.Key_Up: "up",
    Qt.Key.Key_Down: "down",
    Qt.Key.Key_CapsLock: "capslock",
}


class EventBridge(QObject):
    event_signal = pyqtSignal(str, dict)

    def emit_event(self, event: str, payload: dict) -> None:
        self.event_signal.emit(event, payload)


def load_font_family(name: str) -> str:
    try:
        with urllib.request.urlopen(FONT_SOURCES[name], timeout=4) as response:
            font_data = response.read()
    except Exception:
        return name

    font_id = QFontDatabase.addApplicationFontFromData(font_data)
    if font_id < 0:
        return name

    families = QFontDatabase.applicationFontFamilies(font_id)
    return families[0] if families else name


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings_store = SettingsStore()
        self.settings = self.settings_store.load()
        self.clicker = AutoClicker(self._settings_to_config(self.settings))
        self.hotkeys = GlobalHotkeyManager(self.clicker)
        self.bridge = EventBridge()
        self.bridge.event_signal.connect(self._handle_core_event)
        self.clicker.set_event_callback(self.bridge.emit_event)
        self.hotkeys.set_event_callback(self.bridge.emit_event)

        self.mouse_controller = import_module("pynput.mouse").Controller()
        self.recording_hotkey = False
        self.status_state = "idle"
        self.current_light_theme = self.settings.theme == "light"

        self.inter_family = load_font_family("Inter")
        self.mono_family = load_font_family("JetBrains Mono")

        self.setWindowTitle(APP_NAME)
        self.setFixedSize(420, 760)
        self.setWindowIcon(self._load_icon())
        self._apply_window_flags()

        self.root = QWidget(objectName="Root")
        self.root.setProperty("theme", "light" if self.current_light_theme else "dark")
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setWidget(self.root)
        self.setCentralWidget(self.scroll_area)

        self._build_ui()
        self.pulse_animation = QPropertyAnimation(self.status_dot, b"pos", self)
        self.pulse_animation.setDuration(900)
        self.pulse_animation.setStartValue(QPoint(0, 0))
        self.pulse_animation.setEndValue(QPoint(0, -2))
        self.pulse_animation.setLoopCount(-1)
        self.pulse_animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._apply_fonts()
        self._load_stylesheet()
        self._populate_from_settings()
        self._connect_signals()
        self.hotkeys.start()
        self._set_status("idle", "IDLE")
        self._add_history("Settings loaded")

        self.ui_timer = QTimer(self)
        self.ui_timer.setInterval(100)
        self.ui_timer.timeout.connect(self._refresh_metrics)
        self.ui_timer.start()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self.root)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)

        header_card = QFrame(objectName="Card")
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(16, 16, 16, 16)
        header_layout.setSpacing(14)

        top_row = QHBoxLayout()
        title_col = QVBoxLayout()
        self.title_label = QLabel(APP_NAME, objectName="Title")
        self.subtitle_label = QLabel(f"Modern desktop auto clicker v{APP_VERSION}", objectName="Subtitle")
        title_col.addWidget(self.title_label)
        title_col.addWidget(self.subtitle_label)
        top_row.addLayout(title_col)
        top_row.addStretch(1)

        self.theme_button = QPushButton("L/D", objectName="IconButton")
        self.theme_button.setToolTip("Toggle theme")
        top_row.addWidget(self.theme_button)
        header_layout.addLayout(top_row)

        status_row = QHBoxLayout()
        self.status_wrap = QWidget()
        status_wrap_layout = QHBoxLayout(self.status_wrap)
        status_wrap_layout.setContentsMargins(0, 0, 0, 0)
        status_wrap_layout.setSpacing(8)
        self.status_dot = QLabel(objectName="StatusDot")
        self.status_text = QLabel("IDLE", objectName="StatusText")
        status_wrap_layout.addWidget(self.status_dot)
        status_wrap_layout.addWidget(self.status_text)
        status_row.addWidget(self.status_wrap)
        status_row.addStretch(1)
        self.always_on_top = QCheckBox("Always on top")
        status_row.addWidget(self.always_on_top)
        header_layout.addLayout(status_row)

        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(12)
        metrics_row.addWidget(self._build_metric_card("Clicks", "0", "CounterValue", attr_name="click_count_label"))
        metrics_row.addWidget(self._build_metric_card("Live CPS", "0.0", "CounterValue", attr_name="live_cps_label"))
        header_layout.addLayout(metrics_row)

        self.primary_button = QPushButton("START", objectName="PrimaryButton")
        self.primary_button.setProperty("running", "false")
        self.primary_button.setMinimumHeight(56)
        header_layout.addWidget(self.primary_button)
        layout.addWidget(header_card)

        config_card = QFrame(objectName="Card")
        config_layout = QGridLayout(config_card)
        config_layout.setContentsMargins(16, 16, 16, 16)
        config_layout.setHorizontalSpacing(12)
        config_layout.setVerticalSpacing(12)

        config_layout.addWidget(self._section_label("Rate"), 0, 0)
        config_layout.addWidget(self._section_label("Stop at"), 0, 1)

        self.cps_input = QDoubleSpinBox()
        self.cps_input.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        self.cps_input.setDecimals(1)
        self.cps_input.setRange(0.1, 50.0)
        self.cps_input.setSingleStep(0.1)
        self.stop_at_input = QSpinBox()
        self.stop_at_input.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        self.stop_at_input.setRange(0, 1_000_000_000)
        config_layout.addWidget(self.cps_input, 1, 0)
        config_layout.addWidget(self.stop_at_input, 1, 1)

        self.realtime_cps_label = QLabel("Target CPS: 0.0", objectName="RealtimeCps")
        config_layout.addWidget(self.realtime_cps_label, 2, 0, 1, 2)

        config_layout.addWidget(self._section_label("Hotkey"), 3, 0)
        config_layout.addWidget(self._section_label("Button"), 3, 1)

        hotkey_row = QHBoxLayout()
        hotkey_row.setSpacing(8)
        self.hotkey_badge = QLabel("F6", objectName="Badge")
        self.hotkey_badge.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.record_button = QPushButton("Record key", objectName="RecordButton")
        hotkey_row.addWidget(self.hotkey_badge)
        hotkey_row.addWidget(self.record_button)
        hotkey_widget = QWidget()
        hotkey_widget.setLayout(hotkey_row)
        config_layout.addWidget(hotkey_widget, 4, 0)

        self.mouse_button_combo = QComboBox()
        self.mouse_button_combo.addItems(["Left", "Middle", "Right"])
        config_layout.addWidget(self.mouse_button_combo, 4, 1)

        mode_label = self._section_label("Mode")
        config_layout.addWidget(mode_label, 5, 0, 1, 2)
        mode_row = QHBoxLayout()
        self.mode_hold = QRadioButton("Hold to click")
        self.mode_toggle = QRadioButton("Toggle")
        mode_row.addWidget(self.mode_hold)
        mode_row.addWidget(self.mode_toggle)
        mode_widget = QWidget()
        mode_widget.setLayout(mode_row)
        config_layout.addWidget(mode_widget, 6, 0, 1, 2)

        pos_label = self._section_label("Click position")
        config_layout.addWidget(pos_label, 7, 0, 1, 2)
        self.position_cursor = QRadioButton("Use cursor position")
        self.position_fixed = QRadioButton("Use fixed coordinates")
        config_layout.addWidget(self.position_cursor, 8, 0, 1, 2)
        config_layout.addWidget(self.position_fixed, 9, 0, 1, 2)

        self.fixed_x_input = QSpinBox()
        self.fixed_x_input.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        self.fixed_x_input.setRange(-100_000, 100_000)
        self.fixed_y_input = QSpinBox()
        self.fixed_y_input.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        self.fixed_y_input.setRange(-100_000, 100_000)
        self.capture_button = QPushButton("Capture", objectName="CaptureButton")
        config_layout.addWidget(self.fixed_x_input, 10, 0)
        config_layout.addWidget(self.fixed_y_input, 10, 1)
        config_layout.addWidget(self.capture_button, 11, 0, 1, 2)
        layout.addWidget(config_card)

        history_card = QFrame(objectName="Card")
        history_layout = QVBoxLayout(history_card)
        history_layout.setContentsMargins(16, 16, 16, 16)
        history_layout.setSpacing(10)
        history_layout.addWidget(self._section_label("History"))
        self.history_list = QListWidget()
        history_layout.addWidget(self.history_list)
        self.help_label = QLabel("Hold ESC for 2s for emergency stop", objectName="Muted")
        history_layout.addWidget(self.help_label)
        layout.addWidget(history_card)
        layout.addStretch(1)

        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.mode_hold)
        self.mode_group.addButton(self.mode_toggle)
        self.position_group = QButtonGroup(self)
        self.position_group.addButton(self.position_cursor)
        self.position_group.addButton(self.position_fixed)

    def _build_metric_card(self, title: str, initial_value: str, object_name: str, attr_name: str) -> QFrame:
        card = QFrame(objectName="Card")
        card.setMinimumHeight(110)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(8)
        card_layout.addWidget(QLabel(title, objectName="SectionTitle"))
        label = QLabel(initial_value, objectName=object_name)
        setattr(self, attr_name, label)
        card_layout.addWidget(label)
        card_layout.addStretch(1)
        return card

    def _section_label(self, text: str) -> QLabel:
        return QLabel(text, objectName="SectionTitle")

    def _connect_signals(self) -> None:
        self.primary_button.clicked.connect(self._toggle_clicker)
        self.capture_button.clicked.connect(self._capture_coordinates)
        self.record_button.clicked.connect(self._start_hotkey_recording)
        self.theme_button.clicked.connect(self._toggle_theme)
        self.always_on_top.toggled.connect(self._toggle_always_on_top)

        self.cps_input.valueChanged.connect(self._on_settings_changed)
        self.stop_at_input.valueChanged.connect(self._on_settings_changed)
        self.mouse_button_combo.currentIndexChanged.connect(self._on_settings_changed)
        self.mode_hold.toggled.connect(self._on_settings_changed)
        self.position_cursor.toggled.connect(self._on_settings_changed)
        self.fixed_x_input.valueChanged.connect(self._on_settings_changed)
        self.fixed_y_input.valueChanged.connect(self._on_settings_changed)

    def _populate_from_settings(self) -> None:
        self.cps_input.setValue(self.settings.cps)
        self.stop_at_input.setValue(self.settings.stop_at)
        self.hotkey_badge.setText(hotkey_label(self.settings.hotkey))
        self.mode_toggle.setChecked(self.settings.mode == "toggle")
        self.mode_hold.setChecked(self.settings.mode == "hold")
        self.position_cursor.setChecked(self.settings.position_mode == "cursor")
        self.position_fixed.setChecked(self.settings.position_mode == "fixed")
        self.fixed_x_input.setValue(self.settings.fixed_x)
        self.fixed_y_input.setValue(self.settings.fixed_y)
        self.always_on_top.setChecked(self.settings.always_on_top)
        self.mouse_button_combo.setCurrentIndex({"left": 0, "middle": 1, "right": 2}[self.settings.mouse_button])
        self._update_position_inputs()
        self._sync_realtime_target_cps()

    def _apply_fonts(self) -> None:
        app = QApplication.instance()
        if app:
            app.setFont(QFont(self.inter_family, 10))
        self.click_count_label.setFont(QFont(self.mono_family, 22, QFont.Weight.Bold))
        self.live_cps_label.setFont(QFont(self.mono_family, 22, QFont.Weight.Bold))
        self.hotkey_badge.setFont(QFont(self.mono_family, 10, QFont.Weight.Bold))

    def _load_stylesheet(self) -> None:
        qss_path = CURRENT_DIR / "styles.qss"
        self.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    def _load_icon(self) -> QIcon:
        icon_path = ROOT_DIR / "assets" / "icon.png"
        return QIcon(str(icon_path))

    def _settings_to_config(self, settings: AppSettings) -> ClickConfig:
        return ClickConfig(
            cps=settings.cps,
            stop_at=settings.stop_at,
            hotkey=settings.hotkey,
            mode=settings.mode,
            mouse_button=settings.mouse_button,
            position_mode=settings.position_mode,
            fixed_x=settings.fixed_x,
            fixed_y=settings.fixed_y,
        )

    def _collect_settings(self) -> AppSettings:
        return AppSettings(
            cps=round(self.cps_input.value(), 1),
            stop_at=int(self.stop_at_input.value()),
            hotkey=normalize_hotkey_name(self.hotkey_badge.text()),
            mode="hold" if self.mode_hold.isChecked() else "toggle",
            mouse_button={0: "left", 1: "middle", 2: "right"}[self.mouse_button_combo.currentIndex()],
            position_mode="cursor" if self.position_cursor.isChecked() else "fixed",
            fixed_x=int(self.fixed_x_input.value()),
            fixed_y=int(self.fixed_y_input.value()),
            always_on_top=self.always_on_top.isChecked(),
            theme="light" if self.current_light_theme else "dark",
        )

    def _on_settings_changed(self) -> None:
        self._update_position_inputs()
        self._sync_realtime_target_cps()
        self._save_settings()

    def _save_settings(self) -> None:
        self.settings = self._collect_settings()
        self.settings_store.save(self.settings)
        self.clicker.update_config(self._settings_to_config(self.settings))
        self.hotkeys.update_hotkey(self.settings.hotkey)

    def _sync_realtime_target_cps(self) -> None:
        self.realtime_cps_label.setText(f"Target CPS: {self.cps_input.value():.1f}")

    def _toggle_clicker(self) -> None:
        valid, error = self.clicker.validate()
        if not valid:
            self._set_status("error", "ERROR")
            self._add_history(error or "Invalid configuration")
            return

        if self.clicker.is_running:
            self.clicker.stop(reset_counter=True, reason="button")
            return

        if self.clicker.start():
            self._add_history(f"Started - {self.cps_input.value():.1f} CPS")

    def _capture_coordinates(self) -> None:
        x, y = self.mouse_controller.position
        self.fixed_x_input.setValue(int(x))
        self.fixed_y_input.setValue(int(y))
        self.position_fixed.setChecked(True)
        self._save_settings()
        self._add_history(f"Captured coordinates - X:{x} Y:{y}")

    def _start_hotkey_recording(self) -> None:
        self.recording_hotkey = True
        self.record_button.setText("Press any key...")
        self._set_status("idle", "RECORDING")

    def _toggle_theme(self) -> None:
        self.current_light_theme = not self.current_light_theme
        self.root.setProperty("theme", "light" if self.current_light_theme else "dark")
        self.style().unpolish(self.root)
        self.style().polish(self.root)
        self._save_settings()

    def _toggle_always_on_top(self, checked: bool) -> None:
        self.settings.always_on_top = checked
        self._apply_window_flags()
        self.show()
        self._save_settings()

    def _update_position_inputs(self) -> None:
        fixed_enabled = self.position_fixed.isChecked()
        self.fixed_x_input.setEnabled(fixed_enabled)
        self.fixed_y_input.setEnabled(fixed_enabled)
        self.capture_button.setEnabled(fixed_enabled)

    def _refresh_metrics(self) -> None:
        self.click_count_label.setText(str(self.clicker.click_count))
        self.live_cps_label.setText(f"{self.clicker.real_cps():.1f}")
        if self.status_state != "error" and not self.clicker.is_running and not self.recording_hotkey:
            self._set_status("idle", "IDLE")
        elif self.clicker.is_running:
            self._set_status("running", "ACTIVE")

    def _set_status(self, state: str, text: str) -> None:
        self.status_state = state
        self.status_text.setText(text)
        self.status_dot.setProperty("statusState", state)
        self.status_dot.style().unpolish(self.status_dot)
        self.status_dot.style().polish(self.status_dot)

        if state == "running":
            if self.pulse_animation.state() != QPropertyAnimation.State.Running:
                self.pulse_animation.start()
        else:
            self.pulse_animation.stop()
            self.status_dot.move(0, 0)

        is_running = "true" if self.clicker.is_running else "false"
        self.primary_button.setProperty("running", is_running)
        self.primary_button.setText("STOP" if self.clicker.is_running else "START")
        self.primary_button.style().unpolish(self.primary_button)
        self.primary_button.style().polish(self.primary_button)

    def _add_history(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        item = QListWidgetItem(f"{stamp} - {message}")
        self.history_list.insertItem(0, item)
        while self.history_list.count() > 5:
            self.history_list.takeItem(self.history_list.count() - 1)

    def _handle_core_event(self, event: str, payload: dict[str, Any]) -> None:
        if event == "started":
            self._set_status("running", "ACTIVE")
            return

        if event == "stopped":
            reason = payload.get("reason", "manual")
            if payload.get("reset"):
                self._add_history("Stopped and counter reset")
            elif reason == "hold_release":
                self._add_history("Stopped after releasing the hotkey")
            elif reason == "toggle":
                self._add_history("Stopped via toggle")
            elif reason == "emergency":
                self._add_history("Emergency stop triggered")
            elif reason == "target_reached":
                self._add_history("Click target reached")
            self._set_status("idle", "IDLE")
            return

        if event == "target_reached":
            self._set_status("idle", "IDLE")
            return

        if event == "error":
            self._set_status("error", "ERROR")
            self._add_history(payload.get("message", "Unknown error"))
            return

        if event == "emergency_stop":
            self._set_status("error", "ERROR")
            self._add_history(payload.get("message", "Emergency stop"))
            return

        if event == "hotkey_triggered":
            state = payload.get("state")
            if state == "running":
                self._add_history("Started via hotkey")
            elif state == "stopped":
                self._add_history("Stopped via hotkey")
            return

        if event == "hotkey_changed":
            self._add_history(f"Hotkey set - {hotkey_label(payload.get('hotkey', ''))}")

    def _apply_window_flags(self) -> None:
        flags = Qt.WindowType.Window | Qt.WindowType.MSWindowsFixedSizeDialogHint
        if self.settings.always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self.recording_hotkey:
            hotkey = self._hotkey_from_qt_event(event)
            if hotkey:
                self.recording_hotkey = False
                self.record_button.setText("Record key")
                self.hotkey_badge.setText(hotkey_label(hotkey))
                self._save_settings()
                self._set_status("idle", "IDLE")
            return
        super().keyPressEvent(event)

    def _hotkey_from_qt_event(self, event: QKeyEvent) -> str | None:
        key = event.key()
        if key in SPECIAL_QT_KEYS:
            return SPECIAL_QT_KEYS[key]
        if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F35:
            return f"f{key - Qt.Key.Key_F1 + 1}"

        text = event.text().strip().lower()
        if len(text) == 1:
            return normalize_hotkey_name(text)
        return None

    def closeEvent(self, event: QCloseEvent) -> None:
        self._save_settings()
        self.clicker.stop(reason="exit")
        self.hotkeys.stop()
        super().closeEvent(event)
