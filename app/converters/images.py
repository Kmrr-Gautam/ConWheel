from __future__ import annotations
from pathlib import Path
from .base import Conversion, ConversionError, Options

_PIL_FMT = {"png": "PNG", "jpg": "JPEG", "webp": "WEBP", "bmp": "BMP",
            "tiff": "TIFF", "gif": "GIF", "ico": "ICO"}
IMAGE_FORMATS = list(_PIL_FMT)
_NO_ALPHA = {"jpg", "bmp"}
_LOSSY = {"jpg", "webp"}

def available() -> bool:
    try:
        import PIL  # noqa
        return True
    except ImportError:
        return False

def _convert(target):
    def run(src: Path, out: Path, o: Options, cancel, progress):
        from PIL import Image, ImageSequence
        try:
            im = Image.open(src)
            im.load()
        except Exception as e:
            raise ConversionError(f"Could not read image: {e}") from e
        animated = getattr(im, "is_animated", False) and target in ("gif", "webp")
        if o.resize:
            w, h = o.resize
            im.thumbnail((w, h)) if not animated else None
        kw = {}
        if target in _LOSSY:
            kw["quality"] = max(1, min(100, o.image_quality))
        exif = im.info.get("exif") if o.preserve_metadata else None
        if exif and target in ("jpg", "webp", "png", "tiff"):
            kw["exif"] = exif
        if animated:
            frames = [f.copy().convert("RGBA") for f in ImageSequence.Iterator(im)]
            dur = im.info.get("duration", 100)
            frames[0].save(out, _PIL_FMT[target], save_all=True,
                           append_images=frames[1:], duration=dur,
                           loop=im.info.get("loop", 0), **kw)
            return
        if target in _NO_ALPHA and (im.mode in ("RGBA", "LA", "P")):
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.getchannel("A"))
            im = bg
        elif target == "jpg" and im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        elif target == "gif" and im.mode not in ("P", "L"):
            im = im.convert("RGBA") if im.mode == "RGBA" else im.convert("RGB")
        if target == "ico":
            m = max(im.size)
            if m > 256:
                im.thumbnail((256, 256))
            kw["sizes"] = [(s, s) for s in (16, 32, 48, 64, 128, 256) if s <= max(im.size)] or [im.size]
        try:
            im.save(out, _PIL_FMT[target], **kw)
        except Exception as e:
            raise ConversionError(f"Could not write {target.upper()}: {e}") from e
        progress(1.0)
    return run

def conversions_for(src_fmt: str) -> list[Conversion]:
    if src_fmt not in _PIL_FMT or not available():
        return []
    out = []
    for t in IMAGE_FORMATS:
        if t == src_fmt:
            continue
        note = ""
        if t in _NO_ALPHA:
            note = "Transparency is replaced by a white background."
        elif t == "gif":
            note = "GIF is limited to 256 colors."
        elif t == "ico":
            note = "Images larger than 256 px are downscaled."
        out.append(Conversion(src_fmt, t, "pillow", _convert(t), lossy=t in _LOSSY or t == "gif",
                              keeps_metadata=t in ("jpg", "png", "webp", "tiff"),
                              notes=note, recommended=t in ("png", "jpg", "webp")))
    return out
