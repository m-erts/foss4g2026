"""
Скачивание публичных GPS-треков OSM для трёх городских боксов.

ЗАПУСКАТЬ НА ТВОЕЙ МАШИНЕ — мой fetcher до api.openstreetmap.org
не достаёт. Скрипту не нужны ключи: API треков публичный.

    pip install requests
    python fetch_osm_traces.py

Результат: osm_traces_<city>.csv (lat, lon, time если есть)
и сводка в консоль. Каждая страница = до 5 000 точек; страниц
берём до 40 на бокс, этого хватает для оценки плотности и
participation bias. Между запросами пауза — API это просит.

Зачем это докладу: аннотация обещает OSM traces как третий источник.
Тезис, который проверяем: треки отражают поведение КОНТРИБЬЮТОРОВ,
а не населения. Признаки в данных: доля точек с пустым временем,
концентрация вдоль веломаршрутов и хайвеев, кратные проезды одного
и того же пути.
"""
import csv
import time
import xml.etree.ElementTree as ET

import requests

BOXES = {
    # lon_min, lat_min, lon_max, lat_max — небольшие, иначе API режет
    "hiroshima_centre": (132.440, 34.380, 132.475, 34.405),
    "belgrade_centre": (20.440, 44.800, 20.480, 44.825),
    "london_soho": (-0.150, 51.505, -0.115, 51.525),
}
MAX_PAGES = 40
URL = "https://api.openstreetmap.org/api/0.6/trackpoints"
NS = {"gpx": "http://www.topografix.com/GPX/1/0"}


def fetch_box(name, bbox):
    rows, page = [], 0
    while page < MAX_PAGES:
        r = requests.get(URL, params={"bbox": ",".join(map(str, bbox)),
                                      "page": page},
                         headers={"User-Agent": "foss4g2026-talk-research"},
                         timeout=60)
        if r.status_code != 200:
            print(f"  {name}: страница {page} -> HTTP {r.status_code}, стоп")
            break
        root = ET.fromstring(r.content)
        pts = root.findall(".//gpx:trkpt", NS)
        if not pts:
            break
        for p in pts:
            t = p.find("gpx:time", NS)
            rows.append((p.get("lat"), p.get("lon"),
                         t.text if t is not None else ""))
        page += 1
        time.sleep(1.0)
    with open(f"osm_traces_{name}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["lat", "lon", "time"])
        w.writerows(rows)
    with_time = sum(1 for r in rows if r[2])
    print(f"{name}: {len(rows):,} точек за {page} страниц, "
          f"с меткой времени {with_time / max(len(rows), 1):.0%}")
    return rows


if __name__ == "__main__":
    for name, bbox in BOXES.items():
        fetch_box(name, bbox)
    print("\nГотово. Пришли мне три osm_traces_*.csv")
