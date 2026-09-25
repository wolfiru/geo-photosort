from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Callable


def _ask_yes_no(prompt: str, default: bool) -> bool:
    suffix = "J/n" if default else "j/N"
    answer = input(f"{prompt} ({suffix}): ").strip().lower()
    if not answer:
        return default
    return answer.startswith("j")


def run_wizard() -> dict:
    print("=" * 60)
    print("  Geo-Photosort - Fotos/Videos geografisch sortieren")
    print("=" * 60)
    print()
    print("Keine Parameter angegeben - hier die interaktive Einrichtung.")
    print()

    while True:
        source = input("In welchem Ordner liegen die Fotos/Videos? ").strip().strip('"')
        if source and Path(source).is_dir():
            break
        print(f"Ordner nicht gefunden: {source!r}. Bitte erneut versuchen.\n")

    default_output = str(Path(source) / "GeoSort")
    output = input(f"Zielordner [{default_output}]: ").strip().strip('"') or default_output

    move = _ask_yes_no("Dateien verschieben statt kopieren (Originale werden dabei entfernt)?", default=False)
    mode = "move" if move else "copy"

    bubble_in = input("Bubble-Radius in km, wie nah Orte zusammengefasst werden [20]: ").strip()
    try:
        bubble_km = float(bubble_in) if bubble_in else 20.0
    except ValueError:
        print("Ungueltige Zahl, verwende 20.")
        bubble_km = 20.0

    language = input("Sprache der Ortsnamen [de]: ").strip() or "de"

    write_tags = _ask_yes_no(
        "Ort zusaetzlich in die Dateien schreiben (durchsuchbar in Explorer/Fotos-Apps/Lightroom)?",
        default=False,
    )

    return {
        "source_dir": source,
        "output_dir": output,
        "mode": mode,
        "bubble_distance_km": bubble_km,
        "language": language,
        "write_location_tags": write_tags,
    }


def offer_scan_and_confirm(config, run_fn: Callable[[object], None]) -> bool:
    """Bietet einen Dry-Run an, zeigt das Ergebnis und fragt danach, ob der
    echte Lauf (kopieren/verschieben) gestartet werden soll.
    Gibt True zurueck, wenn der echte Lauf ausgefuehrt werden soll."""
    print()
    if _ask_yes_no("Zuerst nur simulieren (Scan, keine Aenderungen, empfohlen)?", default=True):
        print("\n--- Scan laeuft ---")
        run_fn(replace(config, dry_run=True))
        print(f"\nBericht zur Kontrolle: {config.output_dir / 'geosort_report.csv'}")
        action = "verschoben" if config.mode == "move" else "kopiert"
        return _ask_yes_no(f"\nJetzt wirklich {action}?", default=False)
    return True
