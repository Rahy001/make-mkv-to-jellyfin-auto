"""Conventions de nommage Jellyfin (films et musique)."""

import os
import re


def sanitize(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', "_", name).strip(" .")
    return name or "Sans titre"


def movie_path(dest_root: str, title: str, year: str | None, ext: str) -> str:
    """Films : 'Titre (Année)/Titre (Année).mp4' — schéma recommandé Jellyfin."""
    name = f"{title} ({year})" if year else title
    folder = os.path.join(dest_root, sanitize(name))
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{sanitize(name)}.{ext}")


def music_path(dest_root: str, artist: str, album: str) -> str:
    """Musique : 'Artiste/Album/' — schéma recommandé Jellyfin."""
    folder = os.path.join(dest_root, sanitize(artist), sanitize(album))
    os.makedirs(folder, exist_ok=True)
    return folder
