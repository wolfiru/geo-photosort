from __future__ import annotations

import math
from typing import List, Tuple

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import pdist

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r1, r2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(r1) * math.cos(r2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def _to_cartesian(points: np.ndarray) -> np.ndarray:
    lat = np.radians(points[:, 0])
    lon = np.radians(points[:, 1])
    x = np.cos(lat) * np.cos(lon)
    y = np.cos(lat) * np.sin(lon)
    z = np.sin(lat)
    return np.column_stack([x, y, z]) * EARTH_RADIUS_KM


def cluster_points(points: List[Tuple[float, float]], threshold_km: float) -> List[int]:
    """Complete-linkage Clustering: garantiert, dass innerhalb eines Clusters
    kein Punktepaar weiter als threshold_km auseinanderliegt (begrenzter
    Durchmesser). Im Unterschied zu Single-Linkage verhindert das eine
    Ketten-/Verkettungsbildung, bei der weit entfernte Punkte ueber eine Kette
    von Zwischenpunkten verbunden werden, obwohl ihr direkter Abstand den
    Schwellwert deutlich ueberschreitet.
    Gibt fuer jeden Punkt ein Cluster-Label (0..k-1) zurueck."""
    n = len(points)
    if n == 0:
        return []
    if n == 1:
        return [0]

    arr = np.array(points, dtype=float)
    cart = _to_cartesian(arr)

    # Sehnenlaenge (Cartesian-Distanz), die einem Grosskreisabstand von
    # threshold_km auf der Einheitskugel mit Radius EARTH_RADIUS_KM entspricht.
    central_angle = threshold_km / EARTH_RADIUS_KM
    chord_threshold = 2 * EARTH_RADIUS_KM * math.sin(min(central_angle, math.pi) / 2)

    condensed = pdist(cart)
    z = linkage(condensed, method="complete")
    labels = fcluster(z, t=chord_threshold, criterion="distance")
    return (labels - 1).tolist()


def centroid(points: List[Tuple[float, float]]) -> Tuple[float, float]:
    arr = np.array(points, dtype=float)
    return float(arr[:, 0].mean()), float(arr[:, 1].mean())
