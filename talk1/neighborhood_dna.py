"""Neighborhood DNA from Overture Maps Places — FOSS4G Hiroshima 2026.

Функциональная ДНК района из Overture Places. Без скачивания: DuckDB
читает parquet прямо с S3 и фильтрует по bbox на стороне хранилища.

Запуск:  python neighborhood_dna.py 34.30 132.35 34.48 132.55 hiroshima
"""
import sys
import duckdb

RELEASE = "2026-07-22.0"  # categories удаляются в сентябре — здесь taxonomy
H3_RES = 8                # равноплощадные ячейки: градусный грид даёт разброс 1.5x по широте
LEVEL = 1                 # уровень таксономии: 1 = 13 веток, 3 = ~200 листьев
MIN_POI = 10              # ниже порога метрики разнообразия — шум, а не сигнал

ymin, xmin, ymax, xmax, name = (*map(float, sys.argv[1:5]), sys.argv[5])

con = duckdb.connect()
con.sql("INSTALL httpfs; LOAD httpfs; INSTALL h3 FROM community; LOAD h3;")
con.sql("SET s3_region='us-west-2';")

con.sql(f"""
CREATE TABLE cells AS
WITH places AS (
    SELECT h3_latlng_to_cell(bbox.ymin, bbox.xmin, {H3_RES}) AS cell,
           taxonomy.hierarchy[least({LEVEL}, len(taxonomy.hierarchy))] AS category
    FROM read_parquet(
        's3://overturemaps-us-west-2/release/{RELEASE}/theme=places/type=place/*',
        hive_partitioning = 1)
    WHERE bbox.xmin BETWEEN {xmin} AND {xmax}
      AND bbox.ymin BETWEEN {ymin} AND {ymax}
      AND taxonomy IS NOT NULL AND len(taxonomy.hierarchy) > 0
),
shares AS (
    SELECT cell, category, n, n / sum(n) OVER (PARTITION BY cell) AS p
    FROM (SELECT cell, category, count(*)::DOUBLE AS n
          FROM places GROUP BY 1, 2)
)
SELECT cell,
       h3_cell_to_boundary_wkt(cell)              AS geometry,
       sum(n)                                     AS poi_count,
       count(*)                                   AS cat_richness,
       -sum(p * ln(p))                            AS cat_shannon,
       -sum(p * ln(p)) / nullif(ln(count(*)), 0)  AS cat_evenness,
       1 - sum(p * p)                             AS cat_gini_simpson,
       exp(-sum(p * ln(p)))                       AS cat_hill_q1,
       1 / sum(p * p)                             AS cat_hill_q2,
       max(p)                                     AS top_cat_share,
       arg_max(category, p)                       AS dominant_category
FROM shares GROUP BY cell HAVING sum(n) >= {MIN_POI};
""")

con.sql(f"COPY cells TO '{name}_dna.parquet' (FORMAT parquet)")
print(con.sql(f"""SELECT count(*) AS cells, round(sum(poi_count)) AS poi,
    round(median(cat_richness), 1) AS med_richness, round(median(cat_hill_q1), 2) AS med_hill_q1,
    round(median(cat_hill_q2), 2) AS med_hill_q2, round(median(top_cat_share), 2) AS med_top_share,
    mode(dominant_category) AS most_common_dominant FROM cells""").df().to_string(index=False))
