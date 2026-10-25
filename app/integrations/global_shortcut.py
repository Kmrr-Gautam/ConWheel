"""Global modifier+mouse-button listener using pynput (WH_MOUSE_LL / WH_KEYBOARD_LL under the hood).
Privacy: only modifier-key state (ctrl/alt/shift/win) is tracked; no other keystrokes are stored,
logged or transmitted. The hook is event-driven (no polling) and is released in stop()."""
from __future__ import annotations
from typing import Callable
from .shortcut_logic import ShortcutMatcher

class GlobalShortcut:
    def __init__(self, on_trigger: Callable[[int, int], None], modifiers=("ctrl", "alt"), button="right"):
        self.matcher = ShortcutMatcher(modifiers, button)
        self.on_trigger = on_trigger
        self._kb = self._ms = None
        self.status = "stopped"

    def start(self) -> bool:
        if self._kb or self._ms:
            return True
        try:
            from pynput import keyboard, mouse
        except ImportError:
            self.status = "pynput is not installed; use tray menu, drag-and-drop or the Explorer context menu"
            return False
        def norm(k):
            n = getattr(k, "name", "") or ""
            return n if n in ("ctrl", "ctrl_l", "ctrl_r", "alt", "alt_l", "alt_r", "alt_gr", "shift", "shift_l",
                              "shift_r", "cmd", "cmd_l", "cmd_r") else ""
        def on_press(k):
            n = norm(k)
            if n: self.matcher.key_event(n.replace("cmd", "win"), True)
        def on_release(k):
            n = norm(k)
            if n: self.matcher.key_event(n.replace("cmd", "win"), False)
        def on_click(x, y, button, pressed):
            if self.matcher.mouse_event(button.name, pressed):
                self.on_trigger(int(x), int(y))
        try:
            self._kb = keyboard.Listener(on_press=on_press, on_release=on_release)
            self._ms = mouse.Listener(on_click=on_click)
            self._kb.start(); self._ms.start()
        except Exception as e:                       # e.g. blocked by security software
            self.stop(); self.status = f"could not install input listener: {e}"
            return False
        self.status = "active"
        return True

    def stop(self):
        for l in (self._kb, self._ms):
            if l:
                try: l.stop()
                except Exception: pass
        self._kb = self._ms = None
        self.status = "stopped"

    def set_enabled(self, on: bool): self.matcher.enabled = on
    def reconfigure(self, modifiers, button):
        self.matcher.modifiers, self.matcher.button = set(modifiers), button
