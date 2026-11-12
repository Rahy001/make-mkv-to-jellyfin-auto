"""Recherche des binaires externes et détection des capacités GPU."""

import os
import platform
import shutil
import subprocess


def which(name: str, cfg: dict) -> str | None:
    """Renvoie le chemin complet d'un binaire, ou None s'il est absent."""
    custom = cfg.get(name)
    if custom and custom != name:
        if os.path.isfile(custom) and os.access(custom, os.X_OK):
            return custom
        path = shutil.which(custom)
        if path:
            return path
    path = shutil.which(name)
    if path:
        return path
    if platform.system() == "Windows":
        for ext in (".exe", ".bat", ".cmd"):
            path = shutil.which(name + ext)
            if path:
                return path
        for extra in (
            r"C:\Program Files\MakeMKV",
            r"C:\Program Files\FFmpeg\bin",
            r"C:\ffmpeg\bin",
            r"C:\Program Files\libcdio\bin",
        ):
            candidate = os.path.join(extra, name + ".exe")
            if os.path.isfile(candidate):
                return candidate
    return None


def ffmpeg_version(path: str) -> str | None:
    try:
        out = subprocess.run(
            [path, "-version"], capture_output=True, text=True, timeout=15
        ).stdout
        return out.splitlines()[0] if out else None
    except (OSError, subprocess.SubprocessError):
        return None


def encoder_available(ffmpeg: str, encoder: str) -> bool:
    try:
        out = subprocess.run(
            [ffmpeg, "-hide_banner", "-encoders"], capture_output=True, text=True,
            timeout=30,
        ).stdout
        return any(line.split()[1] == encoder for line in out.splitlines()
                   if line.strip() and len(line.split()) > 1)
    except (OSError, subprocess.SubprocessError):
        return False


def gpu_backend(cfg: dict) -> str | None:
    """Retourne 'vaapi' (Linux/AMD Mesa), 'amf' (Windows/AMD) ou None."""
    if not cfg.get("hw_accel", True):
        return None
    system = platform.system()
    if system == "Linux":
        device = cfg.get("vaapi_device", "/dev/dri/renderD128")
        if os.path.exists(device):
            return "vaapi"
        dri = "/dev/dri"
        if os.path.isdir(dri):
            for entry in sorted(os.listdir(dri)):
                if entry.startswith("renderD"):
                    return "vaapi"
        return None
    if system == "Windows":
        return "amf"
    return None


def vaapi_device(cfg: dict) -> str:
    device = cfg.get("vaapi_device", "/dev/dri/renderD128")
    if os.path.exists(device):
        return device
    dri = "/dev/dri"
    if os.path.isdir(dri):
        for entry in sorted(os.listdir(dri)):
            if entry.startswith("renderD"):
                return os.path.join(dri, entry)
    return device
