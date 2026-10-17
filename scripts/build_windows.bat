@echo off
cd /d "%~dp0\.."
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean --onefile --windowed --name Kanyx --icon assets\kanyx.ico --add-data "assets\kanyx.png;assets" main.py
if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%
echo Fertig: dist\Kanyx.exe
