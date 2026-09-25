from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"


class NominatimGeocoder:
    def __init__(
        self,
        user_agent: str,
        language: str = "de",
        cache_file: Optional[Path] = None,
        request_interval_sec: float = 1.1,
    ):
        self.user_agent = user_agent
        self.language = language
        self.cache_file = cache_file
        self.request_interval_sec = request_interval_sec
        self._last_request = 0.0
        self._cache: dict = {}
        if cache_file is not None and cache_file.exists():
            try:
                self._cache = json.loads(cache_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._cache = {}

    def _save_cache(self) -> None:
        if self.cache_file is None:
            return
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache_file.write_text(
            json.dumps(self._cache, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request
        wait = self.request_interval_sec - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()

    def reverse(self, lat: float, lon: float, zoom: int) -> dict:
        key = f"{round(lat, 3)},{round(lon, 3)},{zoom}"
        if key in self._cache:
            return self._cache[key]

        self._throttle()
        resp = requests.get(
            NOMINATIM_URL,
            params={
                "format": "jsonv2",
                "lat": lat,
                "lon": lon,
                "zoom": zoom,
                "accept-language": self.language,
            },
            headers={"User-Agent": self.user_agent},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        address = data.get("address", {})
        self._cache[key] = address
        self._save_cache()
        return address

    def location_fields(self, lat: float, lon: float) -> dict:
        """Rohe Adressfelder (fuer IPTC/XMP-Tags), unabhaengig von den
        sanitized/deduplizierten Ordnernamen."""
        address = self.reverse(lat, lon, zoom=12)
        city = None
        for key in ("city", "town", "village", "municipality", "suburb", "county"):
            if address.get(key):
                city = address[key]
                break
        return {
            "country": address.get("country"),
            "state": address.get("state") or address.get("region"),
            "city": city,
        }
