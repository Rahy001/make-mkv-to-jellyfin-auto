"""Point d'entrée JellyRip : interface graphique par défaut, CLI en option."""

import argparse
import sys

from . import __version__, pipeline
from .config import load
from .disc import scan
from .runner import Cancelled, Runner


def build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jellyrip",
        description="Rip DVD/CD (ISO, MKV, MP4, MP3) optimisé Jellyfin,"
                    " avec accélération GPU AMD.",
    )
    parser.add_argument("--version", action="version",
                        version=f"JellyRip {__version__}")
    parser.add_argument("--gui", action="store_true", help="lancer l'interface")
    parser.add_argument("--scan", action="store_true",
                        help="lister les lecteurs optiques et quitter")
    parser.add_argument("--dry-run", action="store_true",
                        help="vérifier outils et configuration sans rien faire")
    parser.add_argument("--mode", choices=["iso", "mkv", "mp4", "mp3"],
                        help="action à effectuer")
    parser.add_argument("--device", help="périphérique (ex. /dev/sr0 ou D:)")
    parser.add_argument("--title", default="", help="titre du film/album")
    parser.add_argument("--year", default="", help="année de sortie")
    parser.add_argument("--output", help="dossier de sortie")
    parser.add_argument("--no-hw", action="store_true",
                        help="désactiver l'accélération GPU")
    parser.add_argument("--codec", choices=["h264", "hevc"])
    parser.add_argument("--upscale", choices=["none", "1080", "2160"])
    return parser


def cli_main(argv=None) -> int:
    args = build_cli().parse_args(argv)
    cfg = load()
    if args.output:
        cfg["output_dir"] = args.output
    if args.no_hw:
        cfg["hw_accel"] = False
    if args.codec:
        cfg["video_codec"] = args.codec
    if args.upscale:
        cfg["upscale_target"] = args.upscale

    if args.scan:
        discs = scan()
        if not discs:
            print("Aucun lecteur optique détecté.")
        for disc in discs:
            print(disc)
        return 0

    if args.dry_run:
        from .tools import which
        for key, human in (("makemkvcon", "MakeMKV"), ("ffmpeg", "FFmpeg"),
                           ("ffprobe", "FFprobe"),
                           ("cdparanoia", "cd-paranoia")):
            path = which(key, cfg)
            print(f"{human :<14}: {'OK — ' + path if path else 'ABSENT'}")
        from .tools import gpu_backend
        backend = gpu_backend(cfg)
        print(f"GPU            : {backend or 'aucun (encodage logiciel)'}")
        print(f"Sortie         : {cfg['output_dir']}")
        return 0

    if args.gui or (not args.mode and not argv):
        from .gui import run_gui
        run_gui()
        return 0

    if not args.mode:
        build_cli().error("--mode est requis sans --gui")
    discs = scan()
    if not discs:
        print("Aucun lecteur optique détecté.", file=sys.stderr)
        return 1
    if args.device:
        discs = [d for d in discs if d.device.lower() == args.device.lower()]
        if not discs:
            print(f"Lecteur {args.device} introuvable.", file=sys.stderr)
            return 1
    disc = discs[0]

    runner = Runner(log_cb=print,
                    progress_cb=lambda p: print(f"[{p:5.1f} %]"))
    jobs = {
        "iso": lambda: pipeline.job_backup_iso(cfg, disc, runner,
                                               args.title, args.year),
        "mkv": lambda: pipeline.job_rip_mkv(cfg, disc, runner),
        "mp4": lambda: pipeline.job_dvd_to_mp4(cfg, disc, runner,
                                               args.title, args.year),
        "mp3": lambda: pipeline.job_cd_to_mp3(cfg, disc, runner),
    }
    try:
        result = jobs[args.mode]()
        print(f"✔ Terminé : {result}")
        return 0
    except Cancelled:
        print("✖ Annulé")
        return 130
    except Exception as exc:
        print(f"✖ Erreur : {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(cli_main())
