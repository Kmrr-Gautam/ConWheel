"""Hook-independent shortcut matcher: tracks only modifier state, never records keystrokes."""
from __future__ import annotations
import threading, time

class ShortcutMatcher:
    def __init__(self, modifiers=("ctrl", "alt"), button="right", debounce=0.4):
        self.modifiers, self.button, self.debounce = set(modifiers), button, debounce
        self.enabled = True
        self._down: set[str] = set()
        self._last = 0.0
        self._lock = threading.Lock()

    def key_event(self, name: str, pressed: bool):
        name = name.lower().replace("_l", "").replace("_r", "").replace("_gr", "")
        if name in ("ctrl", "alt", "shift", "cmd", "win"):
            with self._lock:
                (self._down.add if pressed else self._down.discard)(name)

    def mouse_event(self, button: str, pressed: bool) -> bool:
        """True when this click should trigger the wheel (debounced, enabled, modifiers held)."""
        if not (pressed and self.enabled and button == self.button):
            return False
        with self._lock:
            if not self.modifiers.issubset(self._down):
                return False
            now = time.monotonic()
            if now - self._last < self.debounce:
                return False
            self._last = now
            return True
