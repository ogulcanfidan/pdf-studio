@echo off
REM Font teshisi - CV dosyasini BU DOSYANIN UZERINE SURUKLE BIRAK.
REM Ciktiyi teshis-cikti.txt dosyasina yazar ve Not Defteri'nde acar.
cd /d "%~dp0"
chcp 65001 >nul

set "PDF=%~1"
if "%PDF%"=="" (
    echo.
    echo   Bu pencereye PDF dosyasini surukleyip birak, sonra Enter'a bas.
    echo   (Ya da dosyayi dogrudan TESHIS.bat uzerine surukleyebilirsin.)
    echo.
    set /p "PDF=PDF yolu: "
)

set "PDF=%PDF:"=%"
if not exist "%PDF%" (
    echo.
    echo   HATA: dosya bulunamadi: %PDF%
    echo.
    pause
    exit /b 1
)

set "KELIME=%~2"
if "%KELIME%"=="" set "KELIME=Fidan"

echo.
echo   Inceleniyor: %PDF%
echo   Aranan kelime: %KELIME%
echo.

set PYTHONIOENCODING=utf-8
".venv\Scripts\python.exe" teshis.py "%PDF%" "%KELIME%" > teshis-cikti.txt 2>&1

echo   Bitti. Cikti: %CD%\teshis-cikti.txt
echo   Bu dosyanin ICINDE BELGE METNI YOKTUR; yalnizca font adlari ve sayilar.
echo.
start "" notepad.exe "teshis-cikti.txt"
