from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from tqdm import tqdm


class ExifToolNotFoundError(RuntimeError):
    pass


@dataclass
class FileMetadata:
    path: Path
    lat: Optional[float]
    lon: Optional[float]
    date_taken: Optional[str]

    @property
    def has_gps(self) -> bool:
        if self.lat is None or self.lon is None:
            return False
        # "Nullinsel" (0,0) ist praktisch immer ein fehlgeschlagener GPS-Fix,
        # kein echter Aufnahmeort.
        if abs(self.lat) < 1e-6 and abs(self.lon) < 1e-6:
            return False
        return True


def check_exiftool(exiftool_path: str) -> None:
    if shutil.which(exiftool_path) is None:
        raise ExifToolNotFoundError(
            f"exiftool wurde nicht gefunden ('{exiftool_path}').\n"
            "Installation unter Windows:\n"
            "  winget install -e --id OliverBetz.ExifTool\n"
            "oder Download von https://exiftool.org und den Pfad per --exiftool-path angeben."
        )


def find_media_files(source_dir: Path, extensions: set) -> List[Path]:
    files = []
    for p in source_dir.rglob("*"):
        if p.is_file() and p.suffix.lower() in extensions:
            files.append(p)
    return files


def _chunks(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def read_metadata_batch(
    files: List[Path], exiftool_path: str = "exiftool", batch_size: int = 200
) -> List[FileMetadata]:
    check_exiftool(exiftool_path)
    results: List[FileMetadata] = []
    chunks = list(_chunks(files, batch_size))
    for chunk in tqdm(chunks, desc="Lese Metadaten (exiftool)", unit="Batch"):
        cmd = [
            exiftool_path,
            "-j",
            "-n",
            "-GPSLatitude",
            "-GPSLongitude",
            "-DateTimeOriginal",
            "-CreateDate",
            *[str(p) for p in chunk],
        ]
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        if proc.returncode not in (0, 1):
            raise RuntimeError(f"exiftool-Fehler: {proc.stderr.strip()}")
        try:
            entries = json.loads(proc.stdout) if proc.stdout.strip() else []
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Konnte exiftool-Ausgabe nicht parsen: {e}")

        by_file = {Path(e["SourceFile"]).resolve(): e for e in entries}
        for original_path in chunk:
            entry = by_file.get(original_path.resolve())
            if entry is None:
                results.append(FileMetadata(original_path, None, None, None))
                continue
            lat = entry.get("GPSLatitude")
            lon = entry.get("GPSLongitude")
            date_taken = entry.get("DateTimeOriginal") or entry.get("CreateDate")
            results.append(
                FileMetadata(
                    original_path,
                    float(lat) if lat is not None else None,
                    float(lon) if lon is not None else None,
                    date_taken,
                )
            )
    return results
