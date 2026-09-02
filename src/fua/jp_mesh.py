"""
Японская стандартная региональная сетка JIS X 0410.

Зачем: в зимней версии Япония считалась в EPSG:3857. Web Mercator
растягивает расстояния в 1/cos(широты), поэтому «сетка 1 км» давала
825 м в Хиросиме и 702 м на Хоккайдо — разброс площади в 1.7 раза
внутри одной страны.

JIS X 0410 чинит это и заодно даёт совместимость: e-Stat и people-flow
от MLIT публикуются именно на этой сетке, так что джойн становится
join'ом по коду, а не пространственной операцией.

Уровни:
  1-й (~80 км): 4 знака   p = floor(lat*1.5),  u = floor(lon) - 100
  2-й (~10 км): 6 знаков  деление 1-го на 8x8
  3-й (~1 км) : 8 знаков  деление 2-го на 10x10

Шаг 3-го уровня: 30" по широте, 45" по долготе.
На широте Японии это примерно 0.92 x 1.13 км.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = ["to_mesh", "mesh_to_bbox", "mesh_to_center", "mesh_series", "MESH_LAT_DEG", "MESH_LON_DEG"]

MESH_LAT_DEG = 30.0 / 3600.0   # 0.008333...
MESH_LON_DEG = 45.0 / 3600.0   # 0.0125


def to_mesh(lat: float, lon: float, level: int = 3) -> str:
    """Координаты -> код меша. level: 1 (80 км), 2 (10 км), 3 (1 км)."""
    if not (20.0 <= lat <= 46.0) or not (122.0 <= lon <= 154.0):
        raise ValueError(f"вне охвата японской сетки: lat={lat}, lon={lon}")

    lat_min = lat * 60.0
    p, lat_rem = divmod(lat_min, 40.0)          # 1-й уровень: 40' по широте
    u = int(lon) - 100
    lon_rem = (lon - int(lon)) * 60.0           # минуты долготы
    code = f"{int(p):02d}{u:02d}"
    if level == 1:
        return code

    q, lat_rem = divmod(lat_rem, 5.0)           # 2-й: 5' по широте
    v, lon_rem = divmod(lon_rem, 7.5)           # 2-й: 7.5' по долготе
    code += f"{int(q)}{int(v)}"
    if level == 2:
        return code

    r = int(lat_rem * 60.0 // 30.0)             # 3-й: 30" по широте
    w = int(lon_rem * 60.0 // 45.0)             # 3-й: 45" по долготе
    return code + f"{r}{w}"


def mesh_to_bbox(mesh: str) -> tuple[float, float, float, float]:
    """Код меша -> (lat_min, lon_min, lat_max, lon_max) юго-западного угла и размера."""
    mesh = str(mesh)
    if len(mesh) not in (4, 6, 8):
        raise ValueError(f"длина кода меша должна быть 4, 6 или 8, получено {len(mesh)}")

    lat = int(mesh[0:2]) * 40.0 / 60.0
    lon = int(mesh[2:4]) + 100.0
    dlat, dlon = 40.0 / 60.0, 1.0

    if len(mesh) >= 6:
        lat += int(mesh[4]) * 5.0 / 60.0
        lon += int(mesh[5]) * 7.5 / 60.0
        dlat, dlon = 5.0 / 60.0, 7.5 / 60.0
    if len(mesh) == 8:
        lat += int(mesh[6]) * MESH_LAT_DEG
        lon += int(mesh[7]) * MESH_LON_DEG
        dlat, dlon = MESH_LAT_DEG, MESH_LON_DEG

    return lat, lon, lat + dlat, lon + dlon


def mesh_to_center(mesh: str) -> tuple[float, float]:
    """Код меша -> (lat, lon) центра ячейки."""
    lat0, lon0, lat1, lon1 = mesh_to_bbox(mesh)
    return (lat0 + lat1) / 2.0, (lon0 + lon1) / 2.0


def mesh_series(lat: pd.Series, lon: pd.Series, level: int = 3) -> pd.Series:
    """Векторизованная версия для колонок DataFrame."""
    lat = pd.to_numeric(lat, errors="coerce")
    lon = pd.to_numeric(lon, errors="coerce")
    ok = lat.notna() & lon.notna()
    out = pd.Series(pd.NA, index=lat.index, dtype="object")
    out[ok] = [to_mesh(a, b, level) for a, b in zip(lat[ok], lon[ok])]
    return out


def cell_size_km(lat: float) -> tuple[float, float]:
    """Реальный размер ячейки 3-го уровня на данной широте, км."""
    dy = MESH_LAT_DEG * 110.574
    dx = MESH_LON_DEG * 111.320 * np.cos(np.radians(lat))
    return float(dx), float(dy)


if __name__ == "__main__":
    print("=== round-trip: координаты -> меш -> центр -> меш ===")
    pts = [(34.3853, 132.4553, "Хиросима"), (35.6812, 139.7671, "Токио"),
           (43.0687, 141.3508, "Саппоро"), (26.2124, 127.6809, "Наха")]
    ok = True
    for la, lo, name in pts:
        m = to_mesh(la, lo)
        cla, clo = mesh_to_center(m)
        m2 = to_mesh(cla, clo)
        same = m == m2
        ok &= same
        dx, dy = cell_size_km(la)
        print(f"{name:10s} {m}  центр {cla:.5f},{clo:.5f}  "
              f"ячейка {dx:.3f}x{dy:.3f} км  round-trip {'ok' if same else 'FAIL'}")
    print()
    print("=== для сравнения: та же ячейка в EPSG:3857 при шаге 1000 ===")
    for la, lo, name in pts:
        print(f"{name:10s} {1000*np.cos(np.radians(la)):.0f} м вместо 1000 м")
    print()
    print("все round-trip прошли" if ok else "ЕСТЬ ОШИБКИ")
