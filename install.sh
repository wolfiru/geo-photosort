#!/usr/bin/env bash
# Geo-Photosort - Einrichtung fuer Linux/macOS.
# Die grafische Oberflaeche (geosort.gui) ist Windows-only - dieses Skript
# richtet nur die Kommandozeile / den interaktiven Assistenten ein.
set -e
cd "$(dirname "$0")"

echo "============================================================"
echo "  Geo-Photosort - Einrichtung"
echo "============================================================"
echo

if ! command -v python3 >/dev/null 2>&1; then
    echo "[Fehler] python3 wurde nicht gefunden. Bitte Python 3.10 oder neuer installieren."
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "Erstelle virtuelle Umgebung ..."
    python3 -m venv .venv
fi

echo "Installiere Abhaengigkeiten ..."
.venv/bin/python -m pip install --upgrade pip --quiet
.venv/bin/python -m pip install -r requirements.txt --quiet

echo
echo "Pruefe exiftool ..."
if command -v exiftool >/dev/null 2>&1; then
    echo "exiftool gefunden."
else
    echo "exiftool wurde nicht gefunden."
    if [ "$(uname)" = "Darwin" ]; then
        echo "Installation: brew install exiftool"
    else
        echo "Installation (Debian/Ubuntu): sudo apt install libimage-exiftool-perl"
        echo "(andere Distributionen: siehe https://exiftool.org)"
    fi
fi

echo
echo "============================================================"
echo "  Fertig! Starten mit:"
echo "    ./geosort_starten.sh   (interaktiver Assistent im Terminal)"
echo "  Grafische Oberflaeche ist nur unter Windows verfuegbar."
echo "============================================================"
