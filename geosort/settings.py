from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

SETTINGS_PATH = Path(__file__).resolve().parent.parent / "geosort_settings.json"


def load_settings() -> dict:
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_settings(settings: dict) -> None:
    SETTINGS_PATH.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def _exiftool_works(path: str) -> bool:
    if not path:
        return False
    try:
        proc = subprocess.run([path, "-ver"], capture_output=True, text=True, timeout=10)
        return proc.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _auto_detect_exiftool() -> Optional[str]:
    found = shutil.which("exiftool") or shutil.which("exiftool.exe")
    if found:
        return found
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "ExifTool" / "ExifTool.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


def resolve_exiftool_path(
    settings: dict, cli_override: Optional[str] = None, interactive: bool = True
) -> str:
    """Ermittelt den exiftool-Pfad, ohne ihn im Programmcode fest zu verdrahten:
    1. explizit uebergebener Pfad (--exiftool-path / YAML-Config)
    2. zuvor in geosort_settings.json gespeicherter Pfad
    3. automatische Suche (PATH, bekannte winget-Installation)
    4. interaktive Nachfrage (nur wenn interactive=True), Ergebnis wird gespeichert
    """
    if cli_override and _exiftool_works(cli_override):
        settings["exiftool_path"] = cli_override
        save_settings(settings)
        return cli_override

    saved = settings.get("exiftool_path")
    if saved and _exiftool_works(saved):
        return saved

    detected = _auto_detect_exiftool()
    if detected and _exiftool_works(detected):
        settings["exiftool_path"] = detected
        save_settings(settings)
        return detected

    if not interactive:
        raise RuntimeError(
            "exiftool wurde nicht gefunden.\n"
            "Installation: winget install -e --id OliverBetz.ExifTool\n"
            "Danach erneut starten, oder Pfad mit --exiftool-path angeben."
        )

    print()
    print("exiftool wurde nicht gefunden.")
    print("Installation: winget install -e --id OliverBetz.ExifTool")
    print("(oder Download von https://exiftool.org)")
    while True:
        path = input("Voller Pfad zur exiftool.exe (leer = abbrechen): ").strip().strip('"')
        if not path:
            print("Abgebrochen.")
            sys.exit(1)
        if _exiftool_works(path):
            settings["exiftool_path"] = path
            save_settings(settings)
            print(f"Gespeichert in {SETTINGS_PATH.name} - wird kuenftig automatisch verwendet.")
            return path
        print("Das hat nicht funktioniert (exiftool -ver ist fehlgeschlagen). Bitte erneut versuchen.")
