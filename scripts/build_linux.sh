#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m pip install -r requirements.txt
python3 -m PyInstaller --noconfirm --clean --onefile --windowed --name Kanyx-linux --add-data "assets/kanyx.png:assets" main.py
echo "Fertig: dist/Kanyx-linux"
