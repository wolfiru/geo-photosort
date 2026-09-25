@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo   Geo-Photosort - Einrichtung
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [Fehler] Python wurde nicht gefunden.
    echo Bitte zuerst Python 3.10 oder neuer installieren: https://www.python.org/downloads/
    echo Wichtig: beim Installieren "Add python.exe to PATH" aktivieren.
    echo.
    pause
    exit /b 1
)

if not exist ".venv" (
    echo Erstelle virtuelle Umgebung ...
    python -m venv .venv
)

echo Installiere Abhaengigkeiten ...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
".venv\Scripts\python.exe" -m pip install -r requirements.txt -r requirements-gui.txt --quiet

echo.
echo Pruefe exiftool ...
where exiftool >nul 2>nul
if errorlevel 1 (
    echo exiftool wurde nicht im PATH gefunden.
    echo Installation ueber winget: winget install -e --id OliverBetz.ExifTool
    echo ^(Alternativ manuell von https://exiftool.org - Geo-Photosort fragt beim ersten Start danach.^)
) else (
    echo exiftool gefunden.
)

echo.
echo ============================================================
echo   Fertig! Starten mit Doppelklick auf:
echo     Geosort_GUI.bat       (grafische Oberflaeche)
echo     Geosort_starten.bat   (interaktiver Assistent im Terminal)
echo ============================================================
echo.
pause
