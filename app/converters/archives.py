"""Archive repackaging (zip/tar/tgz) and safe extraction. Treats archives as untrusted."""
from __future__ import annotations
import gzip
import shutil
import tarfile
import tempfile
import zipfile
from pathlib import Path
from .base import Cancelled, Conversion, ConversionError

MAX_ENTRIES = 100_000
MAX_TOTAL = 20 * 1024**3   # 20 GiB uncompressed safety ceiling

def _safe_target(root: Path, name: str) -> Path:
    name = name.replace("\\", "/")
    if name.startswith("/") or (len(name) > 1 and name[1] == ":"):
        raise ConversionError(f"Unsafe path in archive: {name}")
    dest = (root / name).resolve()
    if root.resolve() != dest and root.resolve() not in dest.parents:
        raise ConversionError(f"Unsafe path in archive (path traversal blocked): {name}")
    return dest

def safe_extract(src: Path, dest: Path, fmt: str, cancel) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    total = 0
    if fmt == "zip":
        with zipfile.ZipFile(src) as z:
            infos = z.infolist()
            if len(infos) > MAX_ENTRIES:
                raise ConversionError("Archive has too many entries.")
            for i in infos:
                if cancel.is_set(): raise Cancelled()
                t = _safe_target(dest, i.filename)
                total += i.file_size
                if total > MAX_TOTAL:
                    raise ConversionError("Archive expands to an unsafe size.")
                if i.is_dir() or i.filename.endswith("/"):
                    t.mkdir(parents=True, exist_ok=True); continue
                t.parent.mkdir(parents=True, exist_ok=True)
                with z.open(i) as s, open(t, "wb") as d:
                    shutil.copyfileobj(s, d)
    elif fmt in ("tar", "tgz"):
        mode = "r:gz" if fmt == "tgz" else "r:"
        with tarfile.open(src, mode) as t:
            n = 0
            for m in t:
                if cancel.is_set(): raise Cancelled()
                n += 1
                if n > MAX_ENTRIES:
                    raise ConversionError("Archive has too many entries.")
                if m.issym() or m.islnk() or m.isdev() or m.isfifo():
                    continue                      # links/devices are never extracted
                tgt = _safe_target(dest, m.name)
                total += max(m.size, 0)
                if total > MAX_TOTAL:
                    raise ConversionError("Archive expands to an unsafe size.")
                if m.isdir():
                    tgt.mkdir(parents=True, exist_ok=True); continue
                tgt.parent.mkdir(parents=True, exist_ok=True)
                f = t.extractfile(m)
                if f is not None:
                    with f, open(tgt, "wb") as d:
                        shutil.copyfileobj(f, d)
    else:
        raise ConversionError("Unsupported archive type for extraction.")

def _pack(tree: Path, out: Path, target: str, cancel):
    files = sorted(p for p in tree.rglob("*"))
    if target == "zip":
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for p in files:
                if cancel.is_set(): raise Cancelled()
                z.write(p, p.relative_to(tree).as_posix())
    else:
        with tarfile.open(out, "w:gz" if target == "tgz" else "w:") as t:
            for p in files:
                if cancel.is_set(): raise Cancelled()
                t.add(p, p.relative_to(tree).as_posix(), recursive=False)

def _repack(src_fmt, target):
    def run(src, out, o, cancel, progress):
        work = Path(tempfile.mkdtemp(prefix="conwheel_arc_"))
        try:
            try:
                safe_extract(src, work, src_fmt, cancel)
            except (zipfile.BadZipFile, tarfile.TarError, EOFError, OSError) as e:
                raise ConversionError(f"Archive is corrupted or unreadable: {e}") from e
            progress(0.5)
            _pack(work, out, target, cancel)
            progress(1.0)
        finally:
            shutil.rmtree(work, ignore_errors=True)
    return run

def _gunzip(src, out, o, cancel, progress):
    try:
        with gzip.open(src, "rb") as s, open(out, "wb") as d:
            while chunk := s.read(1024 * 1024):
                if cancel.is_set(): raise Cancelled()
                d.write(chunk)
    except (OSError, EOFError) as e:
        raise ConversionError(f"GZ file is corrupted: {e}") from e

def conversions_for(fmt: str):
    note = "Archive is extracted to a temporary folder and repackaged; permissions/links are not preserved."
    if fmt in ("zip", "tar", "tgz"):
        return [Conversion(fmt, t, "builtin", _repack(fmt, t), notes=note, recommended=(t == "zip"))
                for t in ("zip", "tar", "tgz") if t != fmt]
    if fmt == "gz":
        return [Conversion("gz", "raw", "builtin", _gunzip, notes="Decompresses the single file inside the .gz.")]
    return []

def extract_archive(src: Path, dest_dir: Path, fmt: str, cancel) -> Path:
    """Separate 'extract' operation: unpack into a new folder next to dest_dir."""
    from ..core.output_manager import resolve_output
    folder = resolve_output(dest_dir, src.stem if fmt != "tgz" else src.name.split(".")[0])
    safe_extract(src, folder, fmt, cancel)
    return folder
