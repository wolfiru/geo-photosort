from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional


def _chunks(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def write_location_tags(
    file_paths: List[Path],
    country: Optional[str],
    state: Optional[str],
    city: Optional[str],
    exiftool_path: str = "exiftool",
    batch_size: int = 200,
) -> None:
    """Schreibt Ortsangaben als IPTC/XMP-Felder + Keywords in die Zieldateien.

    -P erhaelt den Datei-Zeitstempel (Windows "Geaendert am"); das
    EXIF-Aufnahmedatum (DateTimeOriginal) wird nicht angefasst.

    Die Argumente werden ueber eine UTF-8-Argumentdatei (mit BOM) an exiftool
    uebergeben statt direkt auf der Kommandozeile: exiftool erkennt eine
    UTF-8-BOM in einer @-Argumentdatei und liest sie dann korrekt als UTF-8,
    unabhaengig von der Windows-Systemcodepage. Ohne diesen Umweg werden
    Umlaute/Sonderzeichen in Tag-Werten auf Windows haeufig falsch kodiert.
    """
    if not file_paths:
        return
    if not country and not state and not city:
        return

    set_args = ["-P", "-overwrite_original", "-m", "-charset", "iptc=utf8"]
    if country:
        set_args += [f"-Country={country}", f"-XMP-photoshop:Country={country}"]
    if state:
        set_args += [f"-State={state}", f"-XMP-photoshop:State={state}"]
    if city:
        set_args += [f"-City={city}", f"-XMP-photoshop:City={city}"]
    for kw in filter(None, [country, state, city]):
        set_args += [f"-Keywords+={kw}", f"-XMP-dc:Subject+={kw}"]

    # Keywords/Subject sind Listen-Tags: "-Keywords=" (leeren) und "-Keywords+="
    # (befuellen) muessen in getrennten exiftool-Aufrufen erfolgen - in einem
    # gemeinsamen Aufruf wird das Leeren sonst ignoriert und Werte haeufen sich
    # bei wiederholten Laeufen an.
    clear_args = ["-P", "-overwrite_original", "-m", "-Keywords=", "-XMP-dc:Subject="]

    def _run(args: list, chunk: list) -> None:
        argfile_lines = args + [str(p) for p in chunk]
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".args", encoding="utf-8-sig", delete=False
        ) as f:
            f.write("\n".join(argfile_lines))
            argfile_path = f.name
        try:
            proc = subprocess.run(
                [exiftool_path, "-@", argfile_path],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            if proc.returncode not in (0, 1):
                raise RuntimeError(f"exiftool-Fehler beim Schreiben von Tags: {proc.stderr.strip()}")
        finally:
            Path(argfile_path).unlink(missing_ok=True)

    for chunk in _chunks(file_paths, batch_size):
        _run(clear_args, chunk)
        _run(set_args, chunk)
