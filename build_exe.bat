@echo off
cd /d "%~dp0"
if not exist .venv ( py -3.12 -m venv .venv )
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt || exit /b 1
python tools_make_icon.py || exit /b 1
rem Optional: place ffmpeg.exe / ffprobe.exe in vendor\ffmpeg\ to bundle them (see LICENSES.md)
pyinstaller --noconfirm --clean conWheel.spec || exit /b 1
if exist dist\conWheel\conWheel.exe ( echo Built: %CD%\dist\conWheel\conWheel.exe ) else ( echo BUILD FAILED & exit /b 1 )
