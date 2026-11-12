"""Transcodage MKV/VOB -> MP4 optimisé Jellyfin, avec accélération GPU AMD."""

import os
import re

from . import enhance
from .runner import Runner

TIME_RE = re.compile(r"time=(\d+):(\d+):(\d+)")


class Transcoder:
    def __init__(self, ffmpeg: str, ffprobe: str | None, cfg: dict,
                 runner: Runner):
        self.ffmpeg = ffmpeg
        self.ffprobe = ffprobe
        self.cfg = cfg
        self.runner = runner
        self._duration = 0.0

    def to_mp4(self, src: str, dest: str, title: str = "") -> str:
        os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
        cmd = [self.ffmpeg, "-y", "-i", src]
        backend = self._gpu_backend()
        vf = enhance.video_filters(self.cfg)
        af = enhance.audio_filters(self.cfg)

        if backend == "vaapi":
            from .tools import vaapi_device
            cmd += ["-vaapi_device", vaapi_device(self.cfg)]
            vf = self._with_hwupload(vf)
            cmd += ["-vf", vf, "-c:v", self._codec() + "_vaapi",
                    "-global_quality", "20"]
        elif backend == "amf":
            cmd += ["-init_hw_device", "d3d11va=dx11",
                    "-filter_hw_device", "dx11"]
            vf = self._with_hwupload(vf)
            cmd += ["-vf", vf, "-c:v", self._codec() + "_amf",
                    "-quality", "quality", "-rc", "cqp",
                    "-qp_i", "18", "-qp_p", "20"]
        else:
            codec = self._codec()
            vcodec = "libx264" if codec == "h264" else "libx265"
            cmd += ["-vf", vf, "-c:v", vcodec, "-crf", "18", "-preset", "slow"]

        cmd += [
            "-map", "0:v:0", "-map", "0:a:0?", "-map", "0:s:0?",
            "-c:a", "aac", "-b:a", self.cfg.get("audio_bitrate", "192k"),
            "-ac", "2",
        ]
        if af:
            cmd += ["-af", af]
        cmd += ["-c:s", "mov_text", "-movflags", "+faststart"]
        if title:
            cmd += ["-metadata", f"title={title}"]
        cmd += [dest]

        self._duration = self._probe_duration(src)
        self.runner.run(
            cmd, progress_fn=self._time_to_percent if self._duration else None
        )
        return dest

    @staticmethod
    def _with_hwupload(vf: str) -> str:
        tail = "format=nv12,hwupload=extra_hw_frames=64"
        return f"{vf},{tail}" if vf else tail

    def _codec(self) -> str:
        return self.cfg.get("video_codec", "h264")

    def _gpu_backend(self) -> str | None:
        from .tools import encoder_available, gpu_backend
        backend = gpu_backend(self.cfg)
        if backend is None:
            return None
        encoder = self._codec() + ("_vaapi" if backend == "vaapi" else "_amf")
        if encoder_available(self.ffmpeg, encoder):
            return backend
        self.runner.log_cb(
            f"Encodeur {encoder} indisponible dans ce FFmpeg :"
            " encodage logiciel utilisé"
        )
        return None

    def _probe_duration(self, src: str) -> float:
        if not self.ffprobe:
            return 0.0
        try:
            out = self.runner.run_quiet(
                [self.ffprobe, "-v", "error", "-show_entries",
                 "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
                 src], timeout=30
            )
            return float(out.strip())
        except (ValueError, OSError, RuntimeError):
            return 0.0

    def _time_to_percent(self, line: str) -> float | None:
        match = TIME_RE.search(line)
        if not match or self._duration <= 0:
            return None
        h, m, s = (int(g) for g in match.groups())
        seconds = h * 3600 + m * 60 + s
        return min(100.0, seconds / self._duration * 100.0)
