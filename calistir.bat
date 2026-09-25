@echo off
REM PDF Studio - cift tiklayarak calistir.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Ilk kurulum yapiliyor, bu birkac dakika surebilir...
    python -m venv .venv
    if errorlevel 1 (
        echo HATA: Python bulunamadi. python.org uzerinden Python 3.10+ kurun.
        pause
        exit /b 1
    )
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

start "" ".venv\Scripts\pythonw.exe" main.py %*
