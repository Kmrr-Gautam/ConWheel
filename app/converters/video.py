from __future__ import annotations
from .audio import AUDIO_FORMATS, _audio_func, _CODEC, ffmpeg, run_ffmpeg
from .base import Conversion, Options

VIDEO_FORMATS = ["mp4", "mkv", "mov", "avi", "webm", "gif"]
_CRF = {"small": 28, "balanced": 23, "quality": 18}

def _video_func(target):
    def run(src, out, o: Options, cancel, progress):
        crf = _CRF.get(o.video_preset, 23)
        meta = ["-map_metadata", "0" if o.preserve_metadata else "-1"]
        if target in ("mp4", "mov", "mkv"):
            args = ["-map", "0:v:0", "-map", "0:a?", "-c:v", "libx264", "-preset", "medium",
                    "-crf", str(crf), "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", *meta]
            if target == "mp4":
                args += ["-movflags", "+faststart"]
            if target == "mkv":
                args += ["-map", "0:s?", "-c:s", "copy"]
        elif target == "webm":
            args = ["-map", "0:v:0", "-map", "0:a?", "-c:v", "libvpx-vp9", "-crf", str(crf + 7),
                    "-b:v", "0", "-c:a", "libopus", "-b:a", "128k", *meta]
        elif target == "avi":
            args = ["-map", "0:v:0", "-map", "0:a?", "-c:v", "mpeg4", "-q:v", str({"small": 8, "balanced": 4, "quality": 2}[o.video_preset]),
                    "-c:a", "libmp3lame", "-b:a", "192k", *meta]
        else:  # gif
            args = ["-an", "-vf", "fps=12,scale=480:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse"]
        run_ffmpeg(args, src, out, cancel, progress)
    return run

def conversions_for(src_fmt: str) -> list[Conversion]:
    if src_fmt not in VIDEO_FORMATS or not ffmpeg():
        return []
    res = []
    for t in VIDEO_FORMATS:
        if t == src_fmt:
            continue
        note = "Re-encodes the video; quality depends on the selected preset."
        if t == "gif":
            note = "Audio is dropped; 12 fps, 480 px wide to keep GIF size reasonable."
        res.append(Conversion(src_fmt, t, "ffmpeg", _video_func(t), lossy=True, keeps_metadata=t != "gif",
                              notes=note, recommended=t in ("mp4", "webm")))
    if src_fmt != "gif":
        for t in ("mp3", "wav", "m4a"):
            res.append(Conversion(src_fmt, t, "ffmpeg", _audio_func(t), lossy=_CODEC[t][1], keeps_metadata=True,
                                  notes="Extracts the audio track only.", recommended=t == "mp3"))
    return res
