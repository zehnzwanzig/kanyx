#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Prefer a fresh venv: old environments may still have PySide6-Addons installed.
python3 -m pip install -r requirements.txt
python3 -m PyInstaller --noconfirm --clean --onedir --windowed --name Kanyx-linux --add-data 'assets/kanyx.png:assets' main.py
cp LICENSE THIRD_PARTY_NOTICES.md dist/Kanyx-linux/
mkdir -p dist/Kanyx-linux/licenses
cp licenses/LGPL-3.0.txt licenses/GPL-3.0.txt licenses/Apache-2.0.txt dist/Kanyx-linux/licenses/
python3 scripts/prepare_runtime_notices.py dist/Kanyx-linux
# Include source-verified Qt third-party copyright and license notices.
python3 scripts/prepare_qt_third_party_notices.py dist/Kanyx-linux
python3 -m pip freeze > dist/Kanyx-linux/BUILD_DEPENDENCIES.txt
python3 scripts/audit_release_bundle.py dist/Kanyx-linux --report dist/Kanyx-linux/BUNDLE_AUDIT.json
printf '%s\n' 'Linux candidate: dist/Kanyx-linux - review docs/RELEASE_COMPLIANCE.md before distribution.'
