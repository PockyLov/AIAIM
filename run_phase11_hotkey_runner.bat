@echo off
setlocal
cd /d D:\桌面desktop\AIAIM
if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv\Scripts\python.exe. Create and install the project environment first.
  exit /b 1
)
".venv\Scripts\python.exe" scripts\phase11_hotkey_runner.py --config configs\phase11_hotkey_runner.json
