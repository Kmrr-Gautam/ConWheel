@echo off
cd /d "%~dp0"
call build_exe.bat || exit /b 1
set ISCC=
for %%P in ("%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "%ProgramFiles%\Inno Setup 6\ISCC.exe") do if exist %%P set ISCC=%%~P
if "%ISCC%"=="" ( echo Inno Setup 6 not found. Install it from jrsoftware.org then re-run. & exit /b 1 )
"%ISCC%" installer\conWheel.iss || exit /b 1
echo Built: %CD%\installer\Output\conWheel-Setup.exe
