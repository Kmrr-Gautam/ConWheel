from __future__ import annotations
import shutil
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

ProgressCb = Callable[[float], None]   # 0.0 .. 1.0

class ConversionError(Exception):
    """User-presentable conversion failure."""

class Cancelled(Exception):
    pass

@dataclass
class Options:
    image_quality: int = 90
    resize: Optional[tuple] = None        # (w, h) or None
    preserve_metadata: bool = True
    audio_bitrate_kbps: int = 192
    video_preset: str = "balanced"        # small | balanced | quality
    encoding: str = "utf-8"

@dataclass
class Conversion:
    src: str
    target: str
    engine: str                            # "builtin", "pillow", "ffmpeg", "libreoffice", ...
    func: Callable                         # func(src, out, opts, cancel, progress)
    lossy: bool = False
    batch: bool = True
    keeps_metadata: bool = False
    notes: str = ""
    recommended: bool = False

def find_exe(*names: str) -> Optional[str]:
    import sys
    from pathlib import Path
    if getattr(sys, "frozen", False):          # bundled copy next to conWheel.exe wins
        for d in (Path(sys.executable).parent, Path(getattr(sys, "_MEIPASS", "."))):
            for n in names:
                if (d / n).is_file():
                    return str(d / n)
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    return None

def run_cancellable(cmd: list, cancel: threading.Event, timeout: float = 3600,
                    line_cb=None) -> tuple[int, str]:
    """Run a subprocess with a list argv (never a shell string); poll for cancel."""
    import time
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace",
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    lines: list[str] = []
    def reader():
        for ln in proc.stdout:
            lines.append(ln)
            if line_cb:
                line_cb(ln.strip())
    t = threading.Thread(target=reader, daemon=True)
    t.start()
    start = time.monotonic()
    while proc.poll() is None:
        if cancel.is_set():
            proc.kill(); proc.wait(); t.join(2); proc.stdout.close()
            raise Cancelled()
        if time.monotonic() - start > timeout:
            proc.kill(); proc.wait(); t.join(2); proc.stdout.close()
            raise ConversionError("The conversion engine timed out.")
        time.sleep(0.05)
    t.join(5)
    proc.stdout.close()
    return proc.returncode, "".join(lines[-200:])
