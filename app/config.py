"""Settings and history persisted as JSON. History stores metadata only, never contents."""
from __future__ import annotations
import json
import os
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

def app_dir() -> Path:
    base = os.environ.get("APPDATA") or os.path.join(Path.home(), ".config")
    p = Path(base) / "conWheel"
    p.mkdir(parents=True, exist_ok=True)
    return p

def _atomic_write(path: Path, data: str):
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(data)
    os.replace(tmp, path)

@dataclass
class Settings:
    launch_at_startup: bool = False
    minimize_to_tray: bool = False
    default_output_dir: str = ""            # empty => same folder as source
    naming_template: str = "{name}_converted"
    theme: str = "dark"
    shortcut_modifiers: list = field(default_factory=lambda: ["ctrl", "alt"])
    shortcut_button: str = "right"
    shortcut_enabled: bool = True
    image_quality: int = 90
    audio_bitrate_kbps: int = 192
    video_preset: str = "balanced"
    preserve_metadata: bool = True
    ask_before_overwrite: bool = True
    open_folder_after: bool = False
    notifications: bool = True
    favorites: list = field(default_factory=list)

    @classmethod
    def load(cls, path: Path | None = None) -> "Settings":
        path = path or app_dir() / "settings.json"
        s = cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for k, v in data.items():
                if hasattr(s, k): setattr(s, k, v)
        except (OSError, json.JSONDecodeError):
            pass
        return s

    def save(self, path: Path | None = None):
        path = path or app_dir() / "settings.json"
        _atomic_write(path, json.dumps(asdict(self), indent=2))

class History:
    def __init__(self, path: Path | None = None, limit: int = 500):
        self.path = path or app_dir() / "history.json"
        self.limit = limit
        self.items: list[dict] = []
        try:
            self.items = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self.items = []

    def add(self, src, target, output, ok, message=""):
        self.items.insert(0, {"source": str(src), "target": target, "output": str(output or ""),
                              "ok": ok, "message": message, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        del self.items[self.limit:]
        self._save()

    def clear(self):
        self.items = []; self._save()

    def _save(self):
        _atomic_write(self.path, json.dumps(self.items, ensure_ascii=False, indent=1))
