"""Windows Explorer integration.
1. get_selected_paths(): reads the selection of the foreground Explorer window through the
   Shell.Application COM object (requires pywin32). Returns [] when it cannot be determined;
   callers must then show a message / file picker, never guess.
2. install_context_menu(): adds 'Convert with conWheel' for files under HKCU (no admin rights)."""
from __future__ import annotations
import sys

def get_selected_paths() -> list[str]:
    if sys.platform != "win32":
        return []
    try:
        import ctypes, pythoncom, win32com.client
        pythoncom.CoInitialize()
        fg = ctypes.windll.user32.GetForegroundWindow()
        shell = win32com.client.Dispatch("Shell.Application")
        for w in shell.Windows():
            try:
                if int(w.HWND) == int(fg):
                    return [i.Path for i in w.Document.SelectedItems() if i.Path and not i.IsFolder]
            except Exception:
                continue
    except Exception:
        pass
    return []

_KEY = r"Software\Classes\*\shell\conWheel"

def install_context_menu(exe_path: str) -> bool:
    if sys.platform != "win32":
        return False
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _KEY) as k:
        winreg.SetValueEx(k, "MUIVerb", 0, winreg.REG_SZ, "Convert with conWheel")
        winreg.SetValueEx(k, "Icon", 0, winreg.REG_SZ, exe_path)
        winreg.SetValueEx(k, "MultiSelectModel", 0, winreg.REG_SZ, "Player")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _KEY + r"\command") as k:
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, f'"{exe_path}" --convert "%1"')
    return True

def uninstall_context_menu() -> bool:
    if sys.platform != "win32":
        return False
    import winreg
    for sub in (_KEY + r"\command", _KEY):
        try: winreg.DeleteKey(winreg.HKEY_CURRENT_USER, sub)
        except OSError: pass
    return True

def set_launch_at_login(exe_path: str, on: bool) -> bool:
    if sys.platform != "win32":
        return False
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE) as k:
        if on: winreg.SetValueEx(k, "conWheel", 0, winreg.REG_SZ, f'"{exe_path}" --tray')
        else:
            try: winreg.DeleteValue(k, "conWheel")
            except OSError: pass
    return True
