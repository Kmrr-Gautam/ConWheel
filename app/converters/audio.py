from __future__ import annotations
import re
import subprocess
from pathlib import Path
from .base import Conversion, ConversionError, Options, find_exe, run_cancellable

AUDIO_FORMATS = ["mp3", "wav", "flac", "aac", "m4a", "ogg", "opus"]
# target -> ffmpeg codec args (bitrate appended for lossy)
_CODEC = {
    "mp3": (["-c:a", "libmp3lame"], True), "wav": (["-c:a", "pcm_s16le"], False),
    "flac": (["-c:a", "flac"], False), "aac": (["-c:a", "aac", "-f", "adts"], True),
    "m4a": (["-c:a", "aac"], True), "ogg": (["-c:a", "libvorbis"], True),
    "opus": (["-c:a", "libopus"], True),
}
_LOSSLESS_SRC = {"wav", "flac"}

def ffmpeg() -> str | None:
    return find_exe("ffmpeg", "ffmpeg.exe")

def _duration(src: Path) -> float | None:
    probe = find_exe("ffprobe", "ffprobe.exe")
    if not probe:
        return None
    try:
        r = subprocess.run([probe, "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=nw=1:nk=1", str(src)], capture_output=True,
                           text=True, timeout=30,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return float(r.stdout.strip())
    except Exception:
        return None

def run_ffmpeg(args_after_input: list, src: Path, out: Path, cancel, progress, pre=()):
    exe = ffmpeg()
    if not exe:
        raise ConversionError("FFmpeg is not installed. Install FFmpeg or place ffmpeg.exe next to conWheel.")
    dur = _duration(src)
    cmd = [exe, "-hide_banner", "-nostdin", "-y", "-loglevel", "error", "-progress", "pipe:1",
           *pre, "-i", str(src), *args_after_input, str(out)]
    def on_line(ln):
        m = re.match(r"out_time_(?:us|ms)=(\d+)", ln)
        if m and dur:
            progress(min(0.99, int(m.group(1)) / 1_000_000 / dur))
    code, log = run_cancellable(cmd, cancel, line_cb=on_line)
    if code != 0 or not out.exists() or out.stat().st_size == 0:
        tail = [l for l in log.splitlines() if l and "=" not in l[:20]][-3:]
        raise ConversionError("FFmpeg could not convert this file. " + " ".join(tail))
    progress(1.0)

def _audio_func(target):
    def run(src, out, o: Options, cancel, progress):
        codec, lossy = _CODEC[target]
        args = ["-vn", *codec]
        if target == "ogg":      # libvorbis is quality-based; fixed bitrates fail at low sample rates
            kb = o.audio_bitrate_kbps
            args += ["-q:a", str(3 if kb <= 96 else 4 if kb <= 128 else 5 if kb <= 160 else 6 if kb <= 192 else 7 if kb <= 256 else 8)]
        elif lossy:
            args += ["-b:a", f"{o.audio_bitrate_kbps}k"]
        if o.preserve_metadata:
            args += ["-map_metadata", "0"]
        else:
            args += ["-map_metadata", "-1"]
        run_ffmpeg(args, src, out, cancel, progress)
    return run

def conversions_for(src_fmt: str) -> list[Conversion]:
    if src_fmt not in AUDIO_FORMATS or not ffmpeg():
        return []
    res = []
    for t in AUDIO_FORMATS:
        if t == src_fmt:
            continue
        lossy = _CODEC[t][1]
        note = ("Re-encoding a lossless file to a lossy format reduces quality." if lossy and src_fmt in _LOSSLESS_SRC
                else "Converting between lossy formats can reduce quality further." if lossy
                else "Lossless target, but a lossy source cannot regain lost quality." if src_fmt not in _LOSSLESS_SRC else "")
        res.append(Conversion(src_fmt, t, "ffmpeg", _audio_func(t), lossy=lossy,
                              keeps_metadata=True, notes=note, recommended=t in ("mp3", "wav", "flac")))
    return res
