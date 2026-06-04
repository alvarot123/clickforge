from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


SETTINGS_DIR = Path.home() / ".clickforge"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"


@dataclass(slots=True)
class AppSettings:
    cps: float = 10.0
    stop_at: int = 0
    hotkey: str = "f6"
    mode: str = "toggle"
    mouse_button: str = "left"
    position_mode: str = "cursor"
    fixed_x: int = 0
    fixed_y: int = 0
    always_on_top: bool = True
    theme: str = "dark"


class SettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or SETTINGS_FILE

    def load(self) -> AppSettings:
        if not self.path.exists():
            return AppSettings()

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return AppSettings()

        defaults = asdict(AppSettings())
        merged: dict[str, Any] = {**defaults, **payload}
        return AppSettings(**merged)

    def save(self, settings: AppSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(asdict(settings), indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
        temp_path.replace(self.path)
