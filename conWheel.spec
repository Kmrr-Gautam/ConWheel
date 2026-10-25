# PyInstaller spec: one-folder, windowed build
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files
block_cipher = None
datas = [("app/resources", "app/resources"), ("app/ui/styles", "app/ui/styles")] + collect_data_files("pymupdf")
binaries = []
for exe in ("ffmpeg.exe", "ffprobe.exe"):
    p = os.path.join("vendor", "ffmpeg", exe)
    if os.path.exists(p):
        binaries.append((p, "."))        # next to conWheel.exe so find_exe() locates it via PATH-less lookup
hidden = collect_submodules("pynput") + ["win32com.client", "pythoncom", "markdown"]
a = Analysis(["run_app.py"], pathex=["."], binaries=binaries, datas=datas, hiddenimports=hidden, noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="conWheel", console=False,
          icon="app/resources/icons/conWheel.ico", version=None)
coll = COLLECT(exe, a.binaries, a.datas, name="conWheel")
