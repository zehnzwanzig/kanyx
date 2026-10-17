@echo off
setlocal
cd /d "%~dp0\.."
python -m pip install -r requirements.txt
if errorlevel 1 exit /b %errorlevel%
python -m PyInstaller --noconfirm --clean --onedir --windowed --name Kanyx --icon assets\kanyx.ico --add-data "assets\kanyx.png;assets" main.py
if errorlevel 1 exit /b %errorlevel%
copy /Y LICENSE dist\Kanyx\LICENSE >nul
copy /Y THIRD_PARTY_NOTICES.md dist\Kanyx\THIRD_PARTY_NOTICES.md >nul
if not exist dist\Kanyx\licenses mkdir dist\Kanyx\licenses
copy /Y licenses\LGPL-3.0.txt dist\Kanyx\licenses\LGPL-3.0.txt >nul
copy /Y licenses\GPL-3.0.txt dist\Kanyx\licenses\GPL-3.0.txt >nul
echo Portable folder: dist\Kanyx (ZIP the entire folder, not just the EXE)
echo IMPORTANT: Complete the docs\RELEASE_COMPLIANCE.md checklist before distributing.
