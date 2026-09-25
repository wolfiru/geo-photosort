from __future__ import annotations

import csv
import re
import shutil
from pathlib import Path
from typing import Optional

_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_name(name: str, max_length: int = 80) -> str:
    name = _INVALID_CHARS.sub("_", name).strip(" .")
    if not name:
        name = "Unbekannt"
    return name[:max_length]


def unique_destination(dest: Path) -> Path:
    if not dest.exists():
        return dest
    stem, suffix, parent = dest.stem, dest.suffix, dest.parent
    counter = 2
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def copy_or_move_file(src: Path, dest_dir: Path, mode: str, dry_run: bool) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = unique_destination(dest_dir / src.name)
    if not dry_run:
        if mode == "copy":
            shutil.copy2(src, dest)
        else:
            shutil.move(str(src), str(dest))
    return dest


def write_report(rows: list, report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Quelle", "Ziel", "Grossraum", "Bubble", "Latitude", "Longitude"])
        writer.writerows(rows)
