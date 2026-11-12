"""Chaînes de filtres FFmpeg pour améliorer image et son."""

TARGETS = {"none": None, "1080": 1080, "2160": 2160}


def video_filters(cfg: dict) -> str:
    """hqdn3d (débruitage) -> upscale lanczos -> unsharp (netteté)."""
    parts = []
    if cfg.get("denoise", True):
        parts.append("hqdn3d=1.5:1.5:6:6")
    target = TARGETS.get(cfg.get("upscale_target", "none"))
    if target:
        parts.append(f"scale=-2:{target}:flags=lanczos")
    if cfg.get("sharpen", True):
        parts.append("unsharp=5:5:0.8:5:5:0.4")
    return ",".join(parts)


def audio_filters(cfg: dict) -> str:
    """Loudnorm EBU R128 : volume normalisé, idéal pour la lecture Jellyfin."""
    if cfg.get("loudnorm", True):
        return "loudnorm=I=-16:TP=-1.5:LRA=11"
    return ""
