"""Rip de CD audio : cd-paranoia -> WAV -> MP3 (FFmpeg) avec tags ID3."""

import glob
import os
import re

from .runner import Runner

try:
    import discid  # type: ignore
    import musicbrainzngs  # type: ignore
    HAS_MB = True
except ImportError:
    HAS_MB = False


def fetch_metadata(device: str) -> dict | None:
    """Métadonnées MusicBrainz via l'ID du disque (optionnel)."""
    if not HAS_MB:
        return None
    try:
        musicbrainzngs.set_useragent("JellyRip", "1.0.0", "jellyrip@local")
        disc = discid.read(device)
        result = musicbrainzngs.get_releases_by_discid(
            disc.id, includes=["recordings", "artist-credits"]
        )
        if "disc" in result:
            release = result["disc"]["release-list"][0]
            artist = release["artist-credit"][0]["artist"]["name"]
            medium = release.get("medium-list", [{}])[0]
            return {
                "album": release.get("title", "Album inconnu"),
                "artist": artist,
                "date": release.get("date", ""),
                "tracks": [
                    (m["recording"]["title"], artist)
                    for m in medium.get("track-list", [])
                ],
            }
        if "cdstub" in result:
            stub = result["cdstub"]
            artist = stub.get("artist", "Artiste inconnu")
            return {
                "album": stub.get("title", "Album inconnu"),
                "artist": artist,
                "date": "",
                "tracks": [
                    (t.get("title", f"Piste {i + 1}"), artist)
                    for i, t in enumerate(stub.get("track-list", []))
                ],
            }
    except Exception:
        return None
    return None


def rip_cd(device: str, dest_dir: str, cfg: dict, runner: Runner) -> list[str]:
    """Extrait les pistes en MP3 optimisés Jellyfin (dossier Artiste/Album/)."""
    tmp_dir = os.path.join(dest_dir, "_wav_tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    runner.run([cfg["cdparanoia"], "-B", "-d", device], cwd=tmp_dir)
    wavs = sorted(glob.glob(os.path.join(tmp_dir, "*.wav")))
    if not wavs:
        raise RuntimeError("Aucune piste audio extraite du CD")

    meta = fetch_metadata(device) if cfg.get("musicbrainz", True) else None
    if meta:
        runner.log_cb(f"Album identifié : {meta['artist']} — {meta['album']}")
    else:
        runner.log_cb(
            "Métadonnées MusicBrainz indisponibles (installez 'pip install"
            " discid musicbrainzngs' + libdiscid) : noms génériques utilisés"
        )

    artist = (meta or {}).get("artist", "Artiste inconnu")
    album = (meta or {}).get("album", "Album inconnu")
    album_dir = os.path.join(dest_dir, artist, album)
    os.makedirs(album_dir, exist_ok=True)

    from .tools import which
    ffmpeg = which("ffmpeg", cfg)
    if not ffmpeg:
        raise RuntimeError("FFmpeg est requis pour l'encodage MP3")

    mp3s = []
    for i, wav in enumerate(wavs, start=1):
        runner.progress_cb((i - 1) / len(wavs) * 100)
        track_title, track_artist = f"Piste {i:02d}", artist
        if meta and i <= len(meta["tracks"]):
            track_title, track_artist = meta["tracks"][i - 1]
        safe_title = re.sub(r'[<>:"/\\|?*]', "_", track_title) or f"Piste {i:02d}"
        out = os.path.join(album_dir, f"{i:02d} - {safe_title}.mp3")
        cmd = [
            ffmpeg, "-y", "-i", wav,
            "-c:a", "libmp3lame", "-b:a", cfg.get("mp3_bitrate", "320k"),
            "-id3v2_version", "3",
            "-metadata", f"title={track_title}",
            "-metadata", f"artist={track_artist}",
            "-metadata", f"album={album}",
            "-metadata", f"track={i}/{len(wavs)}",
            "-metadata", f"album_artist={artist}",
        ]
        if meta and meta.get("date"):
            cmd += ["-metadata", f"date={meta['date']}"]
        cmd += [out]
        runner.run(cmd)
        mp3s.append(out)
    Runner.rmtree(tmp_dir)
    runner.progress_cb(100)
    return mp3s
