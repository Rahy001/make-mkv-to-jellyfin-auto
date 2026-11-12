"""Upscaling IA optionnel via realesrgan-ncnn-vulkan (compatible AMD/Vulkan).

Nécessite le binaire realesrgan-ncnn-vulkan :
https://github.com/xinntao/Real-ESRGAN/releases (modèle realesr-animevideov3
ou realesrgan-x4v3). Pipeline : MP4 -> images -> IA -> réassemblage FFmpeg.
Très gourmand en temps : à réserver aux vidéos courtes.
"""

import glob
import os
import shutil
import tempfile

from .runner import Runner


def available(cfg: dict) -> bool:
    from .tools import which
    return which("realesrgan-ncnn-vulkan", cfg) is not None


def upscale_video(src: str, dest: str, cfg: dict, runner: Runner,
                  model: str = "realesrgan-x4v3") -> str:
    from .tools import which
    binary = which("realesrgan-ncnn-vulkan", cfg)
    if not binary:
        raise RuntimeError(
            "realesrgan-ncnn-vulkan introuvable : téléchargez-le depuis"
            " https://github.com/xinntao/Real-ESRGAN/releases et indiquez son"
            " chemin dans ~/.jellyrip/config.json (clé 'realesrgan')"
        )
    ffmpeg = cfg.get("ffmpeg", "ffmpeg")
    tmp = tempfile.mkdtemp(prefix="jellyrip_ai_")
    frames_in = os.path.join(tmp, "in")
    frames_out = os.path.join(tmp, "out")
    os.makedirs(frames_in)
    os.makedirs(frames_out)
    try:
        runner.log_cb("Extraction des images (étape 1/3)...")
        runner.run([ffmpeg, "-y", "-i", src, "-qscale:v", "2",
                    os.path.join(frames_in, "%08d.png")])
        runner.log_cb("Upscaling IA (étape 2/3) — ceci est très long...")
        runner.run([binary, "-i", frames_in, "-o", frames_out,
                    "-n", model, "-s", "2"])
        runner.log_cb("Réassemblage (étape 3/3)...")
        runner.run([ffmpeg, "-y", "-framerate", "25", "-i",
                    os.path.join(frames_out, "%08d.png"), "-i", src,
                    "-map", "0:v:0", "-map", "1:a:0?", "-c:v", "libx264",
                    "-crf", "18", "-preset", "medium", "-c:a", "copy",
                    "-movflags", "+faststart", dest])
        return dest
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def count_frames(frames_dir: str) -> int:
    return len(glob.glob(os.path.join(frames_dir, "*.png")))
