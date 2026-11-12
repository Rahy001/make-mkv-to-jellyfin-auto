#!/usr/bin/env bash
# Installation des dépendances JellyRip sur Ubuntu / Debian
set -e
sudo apt update
sudo apt install -y makemkv-bin makemkv-oss ffmpeg libcdio-utils python3-tk genisoimage
if apt-cache show libdvd-pkg >/dev/null 2>&1; then
  sudo apt install -y libdvd-pkg || true
  sudo dpkg-reconfigure libdvd-pkg || true
fi
python3 -m pip install --user -r "$(dirname "$0")/requirements.txt" || true
echo "Vérification :"
python3 "$(dirname "$0")/jellyrip.py" --dry-run
