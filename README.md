# JellyRip

Logiciel libre et multiplateforme (Windows 11 + Ubuntu) pour ripper vos DVD et
CD et les préparer pour **Jellyfin** :

| Mode | Résultat | Usage Jellyfin |
|------|----------|----------------|
| **ISO** | Copie complète et déchiffrée du disque en `.iso` | archivage / lecture directe |
| **MKV** | Extraction des titres en `.mkv` via MakeMKV | archivage |
| **MP4** | DVD → `.mp4` H.264/HEVC + AAC, `faststart` | lecture directe optimisée |
| **MP3** | CD → `.mp3` 320 kbps tagués ID3 | bibliothèque musique |

## Fonctionnalités

- **Détection automatique** des lecteurs optiques et des disques insérés (Linux et Windows).
- **MakeMKV** pour le déchiffrement (DVD vidéo protégés) et la sauvegarde ISO.
- **FFmpeg** pour l'encodage, avec **accélération GPU AMD** :
  - Ubuntu : **VAAPI** (pilotes Mesa/Radeon, encodeurs `h264_vaapi` / `hevc_vaapi`)
  - Windows 11 : **AMF** (encodeurs `h264_amf` / `hevc_amf`)
- **Amélioration de qualité locale** :
  - débruitage `hqdn3d`, upscale Lanczos (720p→1080p, 1080p→4K), netteté `unsharp`
  - son normalisé **EBU R128** (`loudnorm`, -16 LUFS — idéal pour Jellyfin)
  - upscale **IA** optionnel via `realesrgan-ncnn-vulkan` (compatible AMD via Vulkan)
- **Nommage Jellyfin** : `Films/Titre (Année)/Titre (Année).mp4` et
  `Musique/Artiste/Album/01 - Piste.mp3`.
- Interface graphique (Tkinter) **et** ligne de commande.

## Installation des outils requis

### Ubuntu / Debian

```bash
sudo apt update
sudo apt install makemkv-bin makemkv-oss ffmpeg libcdio-utils vorbis-tools python3-tk genisoimage
# libdvdcss pour les DVD commerciaux (dépôt Videolan) :
sudo apt install libdvd-pkg && sudo dpkg-reconfigure libdvd-pkg
pip install -r requirements.txt   # métadonnées MusicBrainz (optionnel)
```

> MakeMKV est gratuit en bêta avec une clé d'évaluation renouvelable ; la clé
> officielle se configure dans l'interface MakeMKV ou via
> `MAKEMKV_CON_KEY`/`~/.MakeMKV/settings.conf`.

### Windows 11

1. **Python 3.11+** : https://www.python.org/downloads/ (cocher « Add to PATH », inclut Tkinter).
2. **MakeMKV** : https://www.makemkv.com/download/ (installer `makemkvcon.exe`).
3. **FFmpeg** : https://www.gyan.dev/ffmpeg/builds/ (build « full ») — ajouter `bin` au PATH, ou déposer dans `C:\ffmpeg\bin`.
4. `pip install -r requirements.txt` (optionnel, métadonnées CD).
5. Facultatif (upscaling IA) : `realesrgan-ncnn-vulkan` depuis
   https://github.com/xinntao/Real-ESRGAN/releases — le chemin se règle dans `%USERPROFILE%\JellyRip\config.json`.

## Utilisation

```bash
# Interface graphique
python jellyrip.py

# Lister les lecteurs
python jellyrip.py --scan

# Vérifier que tout est bien installé (outils + GPU)
python jellyrip.py --dry-run

# DVD -> MP4 optimisé Jellyfin, sur GPU, avec upscale 1080p
python jellyrip.py --mode mp4 --title "Mon Film" --year 2010 --upscale 1080

# Sauvegarde ISO
python jellyrip.py --mode iso --title "Mon Film" --year 2010

# CD -> MP3
python jellyrip.py --mode mp3

# Convertir des MKV déjà extraits en MP4 Jellyfin : utilisez l'interface
# graphique (mode MP4 sans disque), ou placez les MKV et relancez le mode mp4
# après extraction.
```

La configuration est enregistrée dans `~/.jellyrip/config.json` (Linux) ou
`%USERPROFILE%\JellyRip\config.json` (Windows) : chemins des outils, dossier de
sortie, codec, etc.

## Notes techniques

- L'accélération GPU est utilisée pour l'**encodage** (le décodage DVD est
  volontairement logiciel : il est peu coûteux et plus fiable avec les filtres).
  Si l'encodeur VAAPI/AMF n'est pas présent dans votre FFmpeg, JellyRip bascule
  automatiquement en encodage logiciel (`libx264`/`libx265`).
- Sous Ubuntu, vérifiez le GPU avec `vainfo` (paquet `vainfo`) ; le périphérique
  par défaut est `/dev/dri/renderD128` (modifiable dans la config).
- L'upscaling IA est extrêmement long (une image à la fois) : réservez-le aux
  vidéos courtes.
- Rippez uniquement les œuvres dont vous possédez légalement la copie.
