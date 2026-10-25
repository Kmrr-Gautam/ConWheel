import gzip, io, json, shutil, struct, tarfile, tempfile, wave, zipfile, subprocess
from pathlib import Path
from PIL import Image

def tmpdir():
    return Path(tempfile.mkdtemp(prefix="cwtest_"))

def make_png(p, alpha=True, size=(64, 48)):
    Image.new("RGBA" if alpha else "RGB", size, (200, 30, 30, 128) if alpha else (200, 30, 30)).save(p, "PNG")
    return p

def make_wav(p, secs=1):
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000)
        w.writeframes(struct.pack("<h", 1000) * 8000 * secs)
    return p

def make_video(p):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=160x120:rate=10:duration=1",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=1", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-shortest", str(p)], check=True)
    return p
