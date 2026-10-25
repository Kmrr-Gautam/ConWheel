"""Detect real file type from content (magic bytes), not just the extension."""
from __future__ import annotations
import json
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

# kind values: image, document, spreadsheet, presentation, audio, video,
# text_data, archive, pdf, unknown
@dataclass(frozen=True)
class Detected:
    fmt: str          # canonical format key, e.g. "png", "docx", "tgz"
    kind: str
    description: str
    extension_mismatch: bool = False

_KIND = {
    "png": "image", "jpg": "image", "gif": "image", "bmp": "image", "tiff": "image",
    "webp": "image", "ico": "image",
    "pdf": "document", "docx": "document", "doc": "document", "odt": "document",
    "rtf": "document",
    "xlsx": "spreadsheet", "xls": "spreadsheet", "ods": "spreadsheet",
    "pptx": "presentation", "ppt": "presentation", "odp": "presentation",
    "mp3": "audio", "wav": "audio", "flac": "audio", "aac": "audio", "m4a": "audio",
    "ogg": "audio", "opus": "audio",
    "mp4": "video", "mkv": "video", "mov": "video", "avi": "video", "webm": "video",
    "zip": "archive", "tar": "archive", "tgz": "archive", "gz": "archive",
    "txt": "text_data", "md": "text_data", "html": "text_data", "json": "text_data",
    "xml": "text_data", "csv": "text_data", "tsv": "text_data",
}
_EXT_ALIAS = {"jpeg": "jpg", "jpe": "jpg", "tif": "tiff", "htm": "html",
              "markdown": "md", "oga": "ogg", "tar.gz": "tgz", "mpeg4": "mp4"}

def ext_of(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".tar.gz"):
        return "tgz"
    e = path.suffix.lower().lstrip(".")
    return _EXT_ALIAS.get(e, e)

def _zip_kind(path: Path, ext: str) -> str | None:
    try:
        with zipfile.ZipFile(path) as z:
            names = set(z.namelist())
            if "mimetype" in names:
                mt = z.read("mimetype")[:100].decode("ascii", "ignore")
                return {"application/vnd.oasis.opendocument.text": "odt",
                        "application/vnd.oasis.opendocument.spreadsheet": "ods",
                        "application/vnd.oasis.opendocument.presentation": "odp"}.get(mt, "zip")
            if "[Content_Types].xml" in names:
                if any(n.startswith("word/") for n in names):
                    return "docx"
                if any(n.startswith("xl/") for n in names):
                    return "xlsx"
                if any(n.startswith("ppt/") for n in names):
                    return "pptx"
            return "zip"
    except zipfile.BadZipFile:
        return None

def _sniff_binary(path: Path, head: bytes, ext: str) -> str | None:
    if head.startswith(b"\x89PNG\r\n\x1a\n"): return "png"
    if head.startswith(b"\xff\xd8\xff"): return "jpg"
    if head[:6] in (b"GIF87a", b"GIF89a"): return "gif"
    if head[:2] == b"BM" and ext == "bmp": return "bmp"
    if head[:4] in (b"II*\x00", b"MM\x00*"): return "tiff"
    if head[:4] == b"\x00\x00\x01\x00": return "ico"
    if head[:4] == b"%PDF": return "pdf"
    if head[:5] == b"{\\rtf": return "rtf"
    if head[:4] == b"fLaC": return "flac"
    if head[:4] == b"OggS": return "opus" if (ext == "opus" or b"OpusHead" in head) else "ogg"
    if head[:4] == b"RIFF":
        if head[8:12] == b"WEBP": return "webp"
        if head[8:12] == b"WAVE": return "wav"
        if head[8:12] == b"AVI ": return "avi"
    if head[:3] == b"ID3" or (len(head) > 1 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0):
        return "aac" if (ext == "aac" and head[0] == 0xFF and head[1] & 0xF6 == 0xF0) else "mp3"
    if head[4:8] == b"ftyp":
        brand = head[8:12]
        if brand in (b"qt  ",): return "mov"
        if brand in (b"M4A ", b"M4B "): return "m4a"
        return "m4a" if ext == "m4a" else ("mov" if ext == "mov" else "mp4")
    if head[:4] == b"\x1aE\xdf\xa3":
        return "webm" if (b"webm" in head[:64] or ext == "webm") else "mkv"
    if head[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":  # legacy OLE container
        return ext if ext in ("doc", "xls", "ppt") else None
    if head[:2] == b"PK":
        return _zip_kind(path, ext)
    if head[:2] == b"\x1f\x8b":
        return "tgz" if ext == "tgz" or _is_tar_gz(path) else "gz"
    try:
        if tarfile.is_tarfile(path) and ext == "tar": return "tar"
    except Exception:
        pass
    return None

def _is_tar_gz(path: Path) -> bool:
    try:
        with tarfile.open(path, "r:gz") as t:
            t.next()
        return True
    except Exception:
        return False

def _sniff_text(path: Path, ext: str) -> str | None:
    try:
        with open(path, "rb") as f:
            raw = f.read(65536)
    except OSError:
        return None
    if b"\x00" in raw:
        return None
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = raw.decode("cp1252")
        except UnicodeDecodeError:
            return None
    s = text.lstrip()
    if ext == "json" or s[:1] in "{[":
        if ext == "json":
            return "json"
        try:
            json.loads(path.read_text(encoding="utf-8-sig")); return "json"
        except Exception:
            pass
    if s.startswith("<?xml") or (ext == "xml" and s.startswith("<")): return "xml"
    low = s[:200].lower()
    if low.startswith("<!doctype html") or "<html" in low or ext == "html": return "html"
    if ext in ("csv", "tsv", "md", "txt"): return ext
    return "txt"

def detect(path) -> Detected | None:
    """Return Detected or None when the type is unknown/unsupported."""
    path = Path(path)
    ext = ext_of(path)
    try:
        with open(path, "rb") as f:
            head = f.read(4096)
    except OSError:
        return None
    fmt = _sniff_binary(path, head, ext)
    if fmt is None:
        fmt = _sniff_text(path, ext)
    if fmt is None:
        return None
    # ext/text-only refinements for ambiguous containers
    if fmt in _KIND:
        mism = bool(ext) and ext != fmt and not (fmt == "txt" and ext in ("csv", "tsv", "md", "txt", "json", "xml", "html"))
        return Detected(fmt, _KIND[fmt], fmt.upper(), mism)
    return None
