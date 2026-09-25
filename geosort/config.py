from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

PHOTO_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic", ".heif",
    ".bmp", ".gif", ".webp", ".cr2", ".nef", ".arw", ".dng", ".raf", ".orf",
}
VIDEO_EXTENSIONS = {
    ".mp4", ".mov", ".m4v", ".avi", ".mkv", ".3gp", ".mts", ".m2ts",
}


@dataclass
class Config:
    source_dir: Path
    output_dir: Optional[Path] = None
    bubble_distance_km: float = 20.0
    mode: str = "copy"  # "copy" oder "move"
    dry_run: bool = False
    language: str = "de"
    user_agent: str = "Geo-Photosort/1.0 (privates Sortier-Tool)"
    exiftool_path: Optional[str] = None  # wird zur Laufzeit ueber geosort.settings aufgeloest
    cache_file: Optional[Path] = None
    no_gps_dirname: str = "Ohne_GPS"
    extensions: set = field(default_factory=lambda: PHOTO_EXTENSIONS | VIDEO_EXTENSIONS)
    batch_size: int = 200
    request_interval_sec: float = 1.1
    write_location_tags: bool = False
    tag_existing: bool = False

    def __post_init__(self):
        self.source_dir = Path(self.source_dir).resolve()
        if self.output_dir is None:
            self.output_dir = self.source_dir / "GeoSort"
        else:
            self.output_dir = Path(self.output_dir).resolve()
        if self.cache_file is None:
            self.cache_file = self.output_dir / ".geosort_cache.json"
        else:
            self.cache_file = Path(self.cache_file)
        if self.mode not in ("copy", "move"):
            raise ValueError(f"Ungueltiger mode: {self.mode!r} (erlaubt: 'copy', 'move')")


def load_config(config_path: Optional[Path], overrides: dict) -> Config:
    data: dict = {}
    if config_path is not None:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    for key, value in overrides.items():
        if value is not None:
            data[key] = value
    if "source_dir" not in data:
        raise ValueError("source_dir muss angegeben werden (--source oder in der Config-Datei)")
    return Config(**data)
