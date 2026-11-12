"""Pilotage de MakeMKV (makemkvcon) : sauvegarde ISO, extraction MKV."""

import glob
import os
import platform
import re
from shutil import which

from .runner import Runner

PRGV = re.compile(r"PRGV:(\d+),(\d+),")


class MakeMkv:
    def __init__(self, makemkvcon: str, runner: Runner):
        self.bin = makemkvcon
        self.runner = runner

    def info(self, disc_index: int) -> list[dict]:
        out = self.runner.run_quiet(
            [self.bin, "-r", "info", f"disc:{disc_index}"], timeout=120
        )
        titles: list[dict] = []
        for line in out.splitlines():
            if not line.startswith("TINFO:"):
                continue
            parts = line.split(",")
            if len(parts) < 3:
                continue
            index = int(parts[1])
            while len(titles) <= index:
                titles.append({})
            code, value = parts[2], ",".join(parts[3:]).strip('"')
            if code == "30":
                titles[index]["name"] = value
            elif code == "27":
                titles[index]["seconds"] = value
        return titles

    def backup_iso(self, device: str, dest_dir: str) -> str:
        """Sauvegarde complète déchiffrée du disque, puis création d'un .iso."""
        os.makedirs(dest_dir, exist_ok=True)
        backup_dir = os.path.join(dest_dir, "_backup_tmp")
        cmd = [self.bin, "-r", "backup", "--decrypt", f"--device={device}",
               backup_dir]
        self.runner.run(cmd, progress_re=PRGV)
        iso_path = self._build_iso(backup_dir, dest_dir)
        if iso_path:
            Runner.rmtree(backup_dir)
            return iso_path
        self.runner.log_cb(
            "Outil de création d'ISO introuvable (mkisofs/genisoimage/xorriso"
            " sous Linux, oscdimg sous Windows) : la sauvegarde déchiffrée est"
            f" conservée dans le dossier {backup_dir}"
        )
        return backup_dir

    def _build_iso(self, src_dir: str, dest_dir: str) -> str | None:
        iso_path = os.path.join(dest_dir, "disque.iso")
        if platform.system() == "Linux":
            for tool in ("genisoimage", "mkisofs", "xorrisofs"):
                if which(tool):
                    self.runner.run([tool, "-dvd-video", "-o", iso_path, src_dir])
                    return iso_path
        else:
            oscdimg = which("oscdimg")
            if oscdimg:
                self.runner.run([oscdimg, "-n", src_dir, iso_path])
                return iso_path
        return None

    def rip_mkv(self, disc_index: int, dest_dir: str, title="all") -> list[str]:
        os.makedirs(dest_dir, exist_ok=True)
        before = set(glob.glob(os.path.join(dest_dir, "*.mkv")))
        cmd = [self.bin, "-r", "mkv", f"disc:{disc_index}", title, dest_dir]
        self.runner.run(cmd, progress_re=PRGV)
        return sorted(set(glob.glob(os.path.join(dest_dir, "*.mkv"))) - before)
