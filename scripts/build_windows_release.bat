@echo off
setlocal
cd /d "%~dp0\.."

REM Prefer a fresh venv: old environments may still have PySide6-Addons installed.
python -m pip install -r requirements.txt
if errorlevel 1 exit /b %errorlevel%

python -m PyInstaller --noconfirm --clean --onedir --windowed --name Kanyx --icon assets\kanyx.ico --add-data "assets\kanyx.png;assets" main.py
if errorlevel 1 exit /b %errorlevel%

copy /Y LICENSE dist\Kanyx\LICENSE >nul
if errorlevel 1 exit /b %errorlevel%
copy /Y THIRD_PARTY_NOTICES.md dist\Kanyx\THIRD_PARTY_NOTICES.md >nul
if errorlevel 1 exit /b %errorlevel%
if not exist dist\Kanyx\licenses mkdir dist\Kanyx\licenses
copy /Y licenses\LGPL-3.0.txt dist\Kanyx\licenses\LGPL-3.0.txt >nul
if errorlevel 1 exit /b %errorlevel%
copy /Y licenses\GPL-3.0.txt dist\Kanyx\licenses\GPL-3.0.txt >nul
if errorlevel 1 exit /b %errorlevel%
copy /Y licenses\Apache-2.0.txt dist\Kanyx\licenses\Apache-2.0.txt >nul
if errorlevel 1 exit /b %errorlevel%

python -m pip freeze > dist\Kanyx\BUILD_DEPENDENCIES.txt
if errorlevel 1 exit /b %errorlevel%
python scripts\audit_release_bundle.py dist\Kanyx --report dist\Kanyx\BUNDLE_AUDIT.json
if errorlevel 1 (
    echo ERROR: License audit found forbidden modules or missing notices. Do not distribute this build.
    exit /b 1
)

echo Windows candidate: dist\Kanyx - review docs\RELEASE_COMPLIANCE.md before distribution.
