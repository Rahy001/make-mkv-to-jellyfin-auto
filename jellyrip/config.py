"""Configuration persistante de JellyRip (JSON dans ~/.jellyrip/config.json)."""

import json
import os
import sys

CONFIG_DIR = os.path.join(
    os.path.expanduser("~"), ".jellyrip" if os.name != "nt" else "JellyRip"
)
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

DEFAULTS = {
    "output_dir": os.path.join(os.path.expanduser("~"), "JellyRip"),
    "makemkvcon": "makemkvcon",
    "ffmpeg": "ffmpeg",
    "ffprobe": "ffprobe",
    "cdparanoia": "cd-paranoia",
    "realesrgan": "realesrgan-ncnn-vulkan",
    "vaapi_device": "/dev/dri/renderD128",
    "hw_accel": True,
    "video_codec": "h264",          # h264 | hevc
    "audio_bitrate": "192k",
    "loudnorm": True,
    "denoise": True,
    "sharpen": True,
    "upscale_target": "none",       # none | 1080 | 2160
    "ai_upscale": False,
    "mp3_bitrate": "320k",
    "musicbrainz": True,
}


def load() -> dict:
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except (OSError, ValueError):
        pass
    return cfg


def save(cfg: dict) -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    data = {k: cfg.get(k, DEFAULTS[k]) for k in DEFAULTS}
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def log(message: str) -> None:
    print(message, file=sys.stderr)
