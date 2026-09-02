"""Четыре проверки из критического разбора.

1. Состав источников по городам      -> раздел 8.3
2. Сравнение по корзинам равной плотности -> раздел 8.1
3. Сдвиг центров боксов               -> раздел 8.5
4. Чувствительность к порогу          -> раздел 8.6

Каждый город тянется с S3 ОДИН раз увеличенным боксом, дальше всё
считается локально. Иначе двадцать сканов.

Запуск:  python talk1/checks.py
"""
import math
import duckdb
import pandas as pd

RELEASE = "2026-07-22.0"
AREA_KM2 = 366.0
DLON = 0.20
BIG = 2.0          # во сколько раз больше тянем, чтобы хватило на сдвиги
RES = 8
LEVEL = 1
OFFSETS_KM = 4.0   # на сколько сдвигаем центр

CENTRES = {
    "hiroshima": (34.390, 132.450),
    "belgrade":  (44.805, 20.450),
    "amsterdam": (52.370, 4.900),
    "london":    (51.510, -0.120),
}

pd.set_option("display.width", 200)


def half_extents(lat, area=AREA_KM2, dlon=DLON):
    """Полуразмеры бокса в градусах для заданной площади."""
    width_km = dlon * 111.320 * math.cos(math.radians(lat))
    dlat = (area / width_km) / 110.574
    return dlat / 2, dlon / 2


con = duckdb.connect()
con.sql("INSTALL httpfs; LOAD httpfs; INSTALL h3 FROM community; LOAD h3;")
con.sql("SET s3_region='us-west-2';")

# ---------------------------------------------------------------- загрузка
for city, (clat, clon) in CENTRES.items():
    hlat, hlon = half_extents(clat)
    y0, y1 = clat - hlat * BIG, clat + hlat * BIG
    x0, x1 = clon - hlon * BIG, clon + hlon * BIG
    con.sql(f"""
        CREATE OR REPLACE TABLE raw_{city} AS
        SELECT bbox.ymin AS lat, bbox.xmin AS lon,
               taxonomy.hierarchy[least({LEVEL}, len(taxonomy.hierarchy))] AS category,
               sources[1].dataset AS src
        FROM read_parquet(
            's3://overturemaps-us-west-2/release/{RELEASE}/theme=places/type=place/*',
            hive_partitioning = 1)
        WHERE bbox.xmin BETWEEN {x0} AND {x1}
          AND bbox.ymin BETWEEN {y0} AND {y1}
          AND taxonomy IS NOT NULL AND len(taxonomy.hierarchy) > 0
    """)
    n = con.sql(f"SELECT count(*) FROM raw_{city}").fetchone()[0]
    print(f"загружен {city}: {n:,} объектов (бокс x{BIG})")


def cells_for(city, clat, clon, dy_km=0.0, dx_km=0.0, min_poi=10):
    """Метрики по ячейкам для сдвинутого бокса заданной площади."""
    hlat, hlon = half_extents(clat)
    dlat = dy_km / 110.574
    dlon_ = dx_km / (111.320 * math.cos(math.radians(clat)))
    y0, y1 = clat + dlat - hlat, clat + dlat + hlat
    x0, x1 = clon + dlon_ - hlon, clon + dlon_ + hlon
    return con.sql(f"""
        WITH box AS (
            SELECT * FROM raw_{city}
            WHERE lat BETWEEN {y0} AND {y1} AND lon BETWEEN {x0} AND {x1}
        ),
        shares AS (
            SELECT cell, n, n / sum(n) OVER (PARTITION BY cell) AS p
            FROM (SELECT h3_latlng_to_cell(lat, lon, {RES}) AS cell,
                         category, count(*)::DOUBLE AS n
                  FROM box GROUP BY 1, 2)
        )
        SELECT cell, sum(n) AS poi_count, count(*) AS richness,
               exp(-sum(p * ln(p))) AS hill_q1, 1 / sum(p * p) AS hill_q2
        FROM shares GROUP BY cell HAVING sum(n) >= {min_poi}
    """).df()


# ================================================== 1. СОСТАВ ИСТОЧНИКОВ
print("\n" + "=" * 96)
print("1. СОСТАВ ИСТОЧНИКОВ — сравниваем ли мы города или конвейеры сбора данных?")
print("=" * 96)
parts = []
for city in CENTRES:
    df = con.sql(f"""
        SELECT '{city}' AS city, coalesce(src,'(нет)') AS src, count(*) AS n
        FROM raw_{city} GROUP BY 1,2""").df()
    df["share"] = (100 * df.n / df.n.sum()).round(1)
    parts.append(df)
src = pd.concat(parts)
piv = src.pivot_table(index="src", columns="city", values="share", fill_value=0.0)
print(piv.round(1).to_string())
print("\nЕсли доли сильно разные — межгородское сравнение частично сравнивает источники.")

# ================================================== 2. КОРЗИНЫ
print("\n" + "=" * 96)
print("2. КОРЗИНЫ РАВНОЙ ПЛОТНОСТИ — держится ли разрыв при одинаковом числе POI?")
print("=" * 96)
frames = []
for city, (clat, clon) in CENTRES.items():
    df = cells_for(city, clat, clon)
    df["city"] = city
    frames.append(df)
allc = pd.concat(frames, ignore_index=True)
bins = [10, 20, 40, 80, 160, 320, 10**9]
lab = ["10-19", "20-39", "40-79", "80-159", "160-319", "320+"]
allc["bin"] = pd.cut(allc.poi_count, bins=bins, labels=lab, right=False)
for metric in ["hill_q2", "richness"]:
    t = allc.pivot_table(index="bin", columns="city", values=metric,
                         aggfunc="median", observed=True)
    n = allc.pivot_table(index="bin", columns="city", values=metric,
                         aggfunc="size", observed=True)
    print(f"\n--- медиана {metric} по корзинам ---")
    print(t.round(2).to_string())
    print(f"--- число ячеек ---")
    print(n.to_string())
print("\nЕсли Белград впереди ВНУТРИ каждой корзины — возражение 8.1 снято.")

# ================================================== 3. СДВИГ ЦЕНТРОВ
print("\n" + "=" * 96)
print(f"3. СДВИГ ЦЕНТРОВ на {OFFSETS_KM:.0f} км — устойчиво ли ранжирование к выбору бокса?")
print("=" * 96)
shifts = {"центр": (0, 0), "север": (OFFSETS_KM, 0), "юг": (-OFFSETS_KM, 0),
          "восток": (0, OFFSETS_KM), "запад": (0, -OFFSETS_KM)}
rows = []
for name, (dy, dx) in shifts.items():
    rec = {"сдвиг": name}
    for city, (clat, clon) in CENTRES.items():
        df = cells_for(city, clat, clon, dy, dx)
        rec[city] = round(df.hill_q2.median(), 2) if len(df) else float("nan")
    rows.append(rec)
sh = pd.DataFrame(rows).set_index("сдвиг")
print(sh.to_string())
print("\nранг Белграда в каждом сдвиге:")
for name, r in sh.iterrows():
    order = r.sort_values(ascending=False)
    print(f"  {name:8s}: " + " > ".join(f"{c} {v:.2f}" for c, v in order.items()))

# ================================================== 4. ПОРОГ
print("\n" + "=" * 96)
print("4. ЧУВСТВИТЕЛЬНОСТЬ К ПОРОГУ min_poi")
print("=" * 96)
rows = []
for mp in (5, 10, 20):
    rec = {"порог": mp}
    for city, (clat, clon) in CENTRES.items():
        df = cells_for(city, clat, clon, min_poi=mp)
        rec[city] = round(df.hill_q2.median(), 2)
        rec[city + "_n"] = len(df)
    rows.append(rec)
th = pd.DataFrame(rows).set_index("порог")
print(th.to_string())
print("\nЕсли ранжирование одинаково при 5, 10 и 20 — порог результат не определяет.")

print("\n" + "=" * 96)
print("ГОТОВО. Пришли весь вывод целиком.")
