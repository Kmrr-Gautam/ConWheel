"""Registry: which outputs are valid for a detected source, given installed engines."""
from __future__ import annotations
from pathlib import Path
from ..constants import COMMON_FORMATS, FORMAT_CATEGORY
from ..converters import (archives, audio, documents, images, pdf, presentations,
                          spreadsheets, text_data, video)
from ..converters.base import Conversion
from .file_detection import Detected, detect

_PROVIDERS = [images, text_data, audio, video, documents, spreadsheets, presentations, archives, pdf]
_PLUGINS: list = []

def register_plugin(module) -> None:
    """Plugin modules expose conversions_for(fmt) -> list[Conversion]."""
    _PLUGINS.append(module)

def conversions_for(fmt: str) -> list[Conversion]:
    seen, out = set(), []
    for prov in [*_PROVIDERS, *_PLUGINS]:
        for c in prov.conversions_for(fmt):
            if c.target not in seen:      # first provider wins for a given target
                seen.add(c.target); out.append(c)
    out.sort(key=lambda c: (not c.recommended, c.target not in COMMON_FORMATS, c.target))
    return out

def options_for(path) -> tuple[Detected | None, list[Conversion]]:
    d = detect(Path(path))
    return d, (conversions_for(d.fmt) if d else [])

def grouped(convs: list[Conversion]) -> dict[str, list[Conversion]]:
    g: dict[str, list[Conversion]] = {}
    for c in convs:
        g.setdefault(FORMAT_CATEGORY.get(c.target, "Other"), []).append(c)
    return g

def engine_status() -> dict[str, dict]:
    import subprocess, sys
    def ver(cmd):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=20,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return (r.stdout or r.stderr).strip().splitlines()[0]
        except Exception:
            return ""
    ff, so = audio.ffmpeg(), documents.soffice()
    def mod(n):
        try:
            m = __import__(n); return True, getattr(m, "__version__", "")
        except ImportError:
            return False, ""
    pil, pilv = mod("PIL"); fz, fzv = mod("fitz")
    return {
        "Pillow": {"ok": pil, "version": pilv, "help": "pip install Pillow"},
        "FFmpeg": {"ok": bool(ff), "version": ver([ff, "-version"]) if ff else "",
                   "help": "Install FFmpeg (ffmpeg.org) and add it to PATH, or place ffmpeg.exe beside conWheel.exe. Needed for audio/video."},
        "LibreOffice": {"ok": bool(so), "version": ver([so, "--version"]) if so else "",
                        "help": "Install LibreOffice (libreoffice.org). Needed for DOCX/XLSX/PPTX/PDF office conversions."},
        "PyMuPDF": {"ok": fz, "version": fzv, "help": "pip install pymupdf. Needed for PDF to TXT."},
        "OCR (Tesseract)": {"ok": bool(__import__("shutil").which("tesseract")), "version": "",
                            "help": "Optional. Not used by current converters."},
    }
