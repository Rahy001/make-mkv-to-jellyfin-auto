"""Détection des lecteurs optiques et des disques insérés (Linux + Windows)."""

import json
import platform
import re
import subprocess


class Disc:
    def __init__(self, device, label="", kind="unknown", media=False,
                 size_bytes=0, filesystem=""):
        self.device = device
        self.label = label
        self.kind = kind          # dvd | cd | bd | unknown
        self.media = media        # un disque est-il inséré ?
        self.size_bytes = size_bytes
        self.filesystem = filesystem

    def __str__(self):
        state = "disque présent" if self.media else "vide"
        label = f" — {self.label}" if self.label else ""
        return f"{self.device} ({self.kind.upper()}{label}, {state})"


def _guess_kind(name: str, label: str, filesystem: str) -> str:
    text = f"{name} {label} {filesystem}".lower()
    if "udf" in filesystem.lower() or "bd" in name.lower():
        return "bd"
    if "iso9660" in filesystem.lower():
        return "dvd"
    if "cdfs" in filesystem.lower() or filesystem.lower() == "iso9660":
        return "dvd"
    if re.search(r"\b(sr\d+|cdrom)\b", text):
        return "dvd"
    return "unknown"


def scan_linux() -> list[Disc]:
    discs: list[Disc] = []
    try:
        out = subprocess.run(
            ["lsblk", "-P", "-b", "-o",
             "NAME,PATH,TYPE,RM,SIZE,LABEL,FSTYPE"],
            capture_output=True, text=True, timeout=15,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        out = ""
    for line in out.splitlines():
        fields = dict(re.findall(r'(\w+)="([^"]*)"', line))
        if fields.get("TYPE") != "rom":
            continue
        path = fields.get("PATH") or "/dev/" + fields.get("NAME", "")
        fstype = fields.get("FSTYPE", "")
        kind = _guess_kind(fields.get("NAME", ""), fields.get("LABEL", ""), fstype)
        try:
            size = int(fields.get("SIZE") or 0)
        except ValueError:
            size = 0
        # Un fstype présent + une taille > 0 => un disque est inséré et monté
        media = bool(fstype) and size > 0
        if not media:
            media = _linux_has_media(path)
        discs.append(Disc(
            device=path,
            label=fields.get("LABEL", ""),
            kind=kind,
            media=media,
            size_bytes=size,
            filesystem=fstype,
        ))
    return discs


def _linux_has_media(device: str) -> bool:
    """Test brut : un read de 2048 octets réussit si un disque lisible est présent."""
    try:
        with open(device, "rb") as f:
            data = f.read(2048)
        return bool(data)
    except OSError:
        return False


def scan_windows() -> list[Disc]:
    ps = (
        "Get-CimInstance Win32_CDROMDrive | Select-Object Drive, Caption, "
        "MediaLoaded, Size, MediaType | ConvertTo-Json -Compress"
    )
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=30,
        )
        payload = json.loads(proc.stdout or "[]")
    except (OSError, subprocess.SubprocessError, ValueError):
        return []
    if isinstance(payload, dict):
        payload = [payload]
    discs = []
    for item in payload:
        drive = (item.get("Drive") or "").rstrip("\\")
        if not drive:
            continue
        media_type = (item.get("MediaType") or "").lower()
        if "dvd" in media_type or "bd" in media_type or "cd-r" in media_type:
            kind = "bd" if "bd" in media_type else "dvd"
        else:
            kind = "dvd" if item.get("MediaLoaded") else "unknown"
        discs.append(Disc(
            device=drive,
            label=item.get("Caption") or "",
            kind=kind,
            media=bool(item.get("MediaLoaded")),
            size_bytes=int(item.get("Size") or 0),
        ))
    return discs


def scan() -> list[Disc]:
    if platform.system() == "Windows":
        return scan_windows()
    return scan_linux()
