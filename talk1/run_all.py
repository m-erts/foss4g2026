"""Всё, что осталось посчитать для доклада 1.

Четыре города — по одному на каждую юрисдикцию доклада 2 — и три
разрешения H3. Города берутся боксами РОВНО одинаковой площади,
иначе сравнение плотностей и разнообразия нечестное.
Каждый город скачивается с S3 один раз, разрешения считаются локально.

Запуск:  python talk1/run_all.py
Вывод:   <city>_dna_res<N>.parquet + сводная таблица в консоль
"""
import math
import duckdb
import pandas as pd

RELEASE = "2026-07-22.0"
AREA_KM2 = 366.0          # площадь бокса, одинаковая для всех городов
DLON = 0.20               # ширина в градусах; высота подбирается под площадь
RESOLUTIONS = [7, 8, 9]
MIN_POI = 10
LEVEL = 1                 # ветка верхнего уровня таксономии

CENTRES = {               # город: (широта, долгота) центра
    "hiroshima": (34.390, 132.450),
    "belgrade":  (44.805, 20.450),
    "amsterdam": (52.370, 4.900),
    "london":    (51.510, -0.120),
}


def bbox_equal_area(lat, lon, area=AREA_KM2, dlon=DLON):
    """Бокс заданной площади вокруг точки. Высота компенсирует сжатие по широте."""
    width_km = dlon * 111.320 * math.cos(math.radians(lat))
    dlat = (area / width_km) / 110.574
    return lat - dlat / 2, lon - dlon / 2, lat + dlat / 2, lon + dlon / 2


con = duckdb.connect()
con.sql("INSTALL httpfs; LOAD httpfs; INSTALL h3 FROM community; LOAD h3;")
con.sql("SET s3_region='us-west-2';")

rows = []
for city, (clat, clon) in CENTRES.items():
    ymin, xmin, ymax, xmax = bbox_equal_area(clat, clon)
    print(f"\n=== {city}  bbox {ymin:.3f},{xmin:.3f} .. {ymax:.3f},{xmax:.3f} ===")

    # один скан S3 на город
    con.sql(f"""
        CREATE OR REPLACE TABLE raw_{city} AS
        SELECT bbox.ymin AS lat, bbox.xmin AS lon,
               taxonomy.hierarchy[least({LEVEL}, len(taxonomy.hierarchy))] AS category
        FROM read_parquet(
            's3://overturemaps-us-west-2/release/{RELEASE}/theme=places/type=place/*',
            hive_partitioning = 1)
        WHERE bbox.xmin BETWEEN {xmin} AND {xmax}
          AND bbox.ymin BETWEEN {ymin} AND {ymax}
          AND taxonomy IS NOT NULL AND len(taxonomy.hierarchy) > 0
    """)
    n = con.sql(f"SELECT count(*) FROM raw_{city}").fetchone()[0]
    print(f"    объектов с категорией: {n:,}")

    for res in RESOLUTIONS:
        con.sql(f"""
            CREATE OR REPLACE TABLE cells AS
            WITH shares AS (
                SELECT cell, category, n, n / sum(n) OVER (PARTITION BY cell) AS p
                FROM (SELECT h3_latlng_to_cell(lat, lon, {res}) AS cell,
                             category, count(*)::DOUBLE AS n
                      FROM raw_{city} GROUP BY 1, 2)
            )
            SELECT cell, h3_cell_to_boundary_wkt(cell) AS geometry,
                   sum(n)                                    AS poi_count,
                   count(*)                                  AS cat_richness,
                   -sum(p * ln(p))                           AS cat_shannon,
                   -sum(p * ln(p)) / nullif(ln(count(*)), 0) AS cat_evenness,
                   1 - sum(p * p)                            AS cat_gini_simpson,
                   exp(-sum(p * ln(p)))                      AS cat_hill_q1,
                   1 / sum(p * p)                            AS cat_hill_q2,
                   max(p)                                    AS top_cat_share,
                   arg_max(category, p)                      AS dominant_category
            FROM shares GROUP BY cell HAVING sum(n) >= {MIN_POI}
        """)
        con.sql(f"COPY cells TO '{city}_dna_res{res}.parquet' (FORMAT parquet)")
        r = con.sql("""SELECT count(*) cells, sum(poi_count) poi,
                              median(poi_count) med_poi, median(cat_richness) richness,
                              median(cat_hill_q1) hill_q1, median(cat_hill_q2) hill_q2,
                              median(top_cat_share) top_share,
                              mode(dominant_category) dominant FROM cells""").fetchone()
        rows.append(dict(city=city, res=res, cells=r[0], poi=int(r[1]), med_poi=r[2],
                         richness=r[3], hill_q1=round(r[4], 2), hill_q2=round(r[5], 2),
                         top_share=round(r[6], 3), dominant=r[7]))
        print(f"    res {res}: {r[0]:4d} ячеек, hill_q2 = {r[5]:.2f}")

df = pd.DataFrame(rows)
print("\n\n" + "=" * 100)
print("СВОДКА — если знак разрыва между городами одинаков на всех res, MAUP закрыт")
print("=" * 100)
print(df.to_string(index=False))
df.to_csv("dna_summary.csv", index=False)
print("\nсохранено: dna_summary.csv")
