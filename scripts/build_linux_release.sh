#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m pip install -r requirements.txt
python3 -m PyInstaller --noconfirm --clean --onedir --windowed --name Kanyx-linux --add-data 'assets/kanyx.png:assets' main.py
cp LICENSE THIRD_PARTY_NOTICES.md dist/Kanyx-linux/
mkdir -p dist/Kanyx-linux/licenses
cp licenses/LGPL-3.0.txt licenses/GPL-3.0.txt dist/Kanyx-linux/licenses/
echo 'Portable directory: dist/Kanyx-linux (package the entire directory)'
echo 'IMPORTANT: Complete docs/RELEASE_COMPLIANCE.md before distribution.'
