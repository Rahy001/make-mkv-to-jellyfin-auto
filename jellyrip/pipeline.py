"""Orchestration des tâches : disque -> ISO / MKV / MP4 / MP3."""

import os

from . import ai_upscale, cdrip, jellyfin
from .config import CONFIG_PATH
from .makemkv import MakeMkv
from .runner import Runner
from .tools import which
from .transcode import Transcoder


def _check_tool(cfg: dict, key: str, human: str) -> str:
    path = which(key, cfg)
    if not path:
        raise RuntimeError(
            f"{human} introuvable. Installez-le ou renseignez son chemin dans"
            f" {CONFIG_PATH}"
        )
    return path


def job_backup_iso(cfg: dict, disc, runner: Runner, title: str = "",
                   year: str = "") -> str:
    makemkvcon = _check_tool(cfg, "makemkvcon", "MakeMKV (makemkvcon)")
    mk = MakeMkv(makemkvcon, runner)
    dest = os.path.join(cfg["output_dir"], "ISO")
    result = mk.backup_iso(disc.device, dest)
    if title:
        named = os.path.join(dest, jellyfin.sanitize(
            f"{title} ({year})" if year else title)) + ".iso"
        if result.endswith(".iso"):
            os.replace(result, named)
            result = named
    runner.log_cb(f"ISO prêt : {result}")
    return result


def job_rip_mkv(cfg: dict, disc, runner: Runner, title: str = "") -> list[str]:
    makemkvcon = _check_tool(cfg, "makemkvcon", "MakeMKV (makemkvcon)")
    mk = MakeMkv(makemkvcon, runner)
    session = jellyfin.sanitize(title) if title else _timestamp()
    dest = os.path.join(cfg["output_dir"], "MKV", session)
    files = mk.rip_mkv(_disc_index(disc), dest)
    runner.log_cb(f"{len(files)} fichier(s) MKV extraits dans {dest}")
    return files


def job_dvd_to_mp4(cfg: dict, disc, runner: Runner, title: str = "",
                   year: str = "") -> list[str]:
    """DVD -> MKV (MakeMKV) -> MP4 optimisé Jellyfin (GPU AMD si dispo)."""
    mkv_files = job_rip_mkv(cfg, disc, runner, title)
    return convert_to_mp4(cfg, mkv_files, runner, title, year)


def convert_to_mp4(cfg: dict, sources: list[str], runner: Runner,
                   title: str = "", year: str = "") -> list[str]:
    ffmpeg = _check_tool(cfg, "ffmpeg", "FFmpeg")
    ffprobe = which("ffprobe", cfg)
    transcoder = Transcoder(ffmpeg, ffprobe, cfg, runner)
    outputs = []
    for i, src in enumerate(sources):
        base = title or os.path.splitext(os.path.basename(src))[0]
        name = f"{base} ({year})" if year else base
        dest = os.path.join(cfg["output_dir"], "Films",
                            jellyfin.sanitize(name),
                            f"{jellyfin.sanitize(name)}.mp4")
        runner.log_cb(f"Transcodage {i + 1}/{len(sources)} : {src}")
        out = transcoder.to_mp4(src, dest, title=base)
        outputs.append(out)
        runner.log_cb(f"MP4 prêt : {out}")
    if cfg.get("ai_upscale") and outputs:
        if not ai_upscale.available(cfg):
            runner.log_cb("Upscaling IA demandé mais realesrgan-ncnn-vulkan"
                          " est introuvable : étape ignorée")
        else:
            for src in list(outputs):
                dest = src.replace(".mp4", ".IA.mp4")
                runner.log_cb(f"Upscaling IA : {src}")
                ai_upscale.upscale_video(src, dest, cfg, runner)
                outputs[outputs.index(src)] = dest
    runner.progress_cb(100)
    return outputs


def job_cd_to_mp3(cfg: dict, disc, runner: Runner) -> list[str]:
    cdparanoia = _check_tool(cfg, "cdparanoia",
                             "cdparanoia / cd-paranoia (paquet libcdio)")
    cfg = dict(cfg)
    cfg["cdparanoia"] = cdparanoia
    dest = os.path.join(cfg["output_dir"], "Musique")
    files = cdrip.rip_cd(disc.device, dest, cfg, runner)
    runner.log_cb(f"{len(files)} piste(s) MP3 créées dans {dest}")
    return files


def _disc_index(disc) -> int:
    """MakeMKV numérote les lecteurs ; on déduit l'index depuis /dev/srN."""
    import re
    match = re.search(r"sr(\d+)$", disc.device)
    return int(match.group(1)) if match else 0


def _timestamp() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d-%H%M%S")
