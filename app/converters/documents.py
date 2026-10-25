"""LibreOffice headless bridge used by documents, spreadsheets and presentations."""
from __future__ import annotations
import os
import shutil
import tempfile
from pathlib import Path
from .base import Conversion, ConversionError, find_exe, run_cancellable

def soffice() -> str | None:
    exe = find_exe("soffice", "soffice.exe", "libreoffice")
    if exe:
        return exe
    for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
        if base:
            c = Path(base) / "LibreOffice" / "program" / "soffice.exe"
            if c.exists():
                return str(c)
    return None

# target ext -> filter spec passed to --convert-to
_TARGET = {"pdf": "pdf", "docx": "docx", "odt": "odt", "rtf": "rtf", "txt": "txt:Text",
           "html": "html", "xlsx": "xlsx", "ods": "ods", "csv": "csv", "pptx": "pptx", "odp": "odp"}
_INFILTER = {"html": "HTML (StarWriter)"}

def lo_convert(src: Path, out: Path, target: str, cancel, progress):
    exe = soffice()
    if not exe:
        raise ConversionError("LibreOffice is not installed. Install LibreOffice to convert office documents.")
    work = Path(tempfile.mkdtemp(prefix="conwheel_lo_"))
    try:
        profile = work / "profile"
        outdir = work / "out"
        outdir.mkdir()
        # copy source to a plain ASCII name: avoids LibreOffice issues with odd paths
        tmp_src = work / ("input" + (src.suffix.lower() or ".bin"))
        shutil.copyfile(src, tmp_src)
        cmd = [exe, f"-env:UserInstallation={profile.resolve().as_uri()}", "--headless",
               "--norestore", "--nolockcheck"]
        if src.suffix.lower() == ".html":
            cmd += ["--infilter=" + _INFILTER["html"]]
        cmd += ["--convert-to", _TARGET[target], "--outdir", str(outdir), str(tmp_src)]
        progress(0.1)
        code, log = run_cancellable(cmd, cancel, timeout=600)
        produced = list(outdir.glob("*"))
        if code != 0 or not produced:
            raise ConversionError("LibreOffice could not convert this file." + (f" {log.strip()[-200:]}" if log.strip() else ""))
        shutil.move(str(produced[0]), str(out))
        progress(1.0)
    finally:
        shutil.rmtree(work, ignore_errors=True)

def _lo(target):
    return lambda src, out, o, cancel, progress: lo_convert(src, out, target, cancel, progress)

def build(src_fmt: str, targets: list[str], notes: dict, recommended=()) -> list[Conversion]:
    if not soffice():
        return []
    return [Conversion(src_fmt, t, "libreoffice", _lo(t), lossy=notes.get(t, "") != "",
                       batch=True, keeps_metadata=True, notes=notes.get(t, ""),
                       recommended=t in recommended) for t in targets if t != src_fmt]

_DOC_NOTE = {"pdf": "Output is fixed-layout; text remains selectable.",
             "txt": "All formatting, images and tables are dropped.",
             "html": "Layout may differ from the original document.",
             "rtf": "Some advanced Word features may be simplified."}

def conversions_for(src_fmt: str):
    if src_fmt in ("docx", "doc", "odt", "rtf"):
        return build(src_fmt, ["pdf", "docx", "odt", "rtf", "txt", "html"], _DOC_NOTE, ("pdf", "docx"))
    if src_fmt == "txt":
        return build(src_fmt, ["pdf", "docx", "odt", "rtf"], {}, ("pdf", "docx"))
    if src_fmt == "html":
        return build(src_fmt, ["pdf", "docx", "odt"], {"pdf": "Rendered by LibreOffice, not a web browser; modern CSS may not apply."}, ("pdf",))
    return []
