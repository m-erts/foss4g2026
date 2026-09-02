"""Диагностика: как устроены категории в Overture Places и какова их полнота.

Запуск:  python talk1/inspect_taxonomy.py 34.30 132.35 34.48 132.55 hiroshima
         python talk1/inspect_taxonomy.py 44.75 20.35 44.85 20.55 belgrade
"""
import sys
import duckdb

RELEASE = "2026-07-22.0"
ymin, xmin, ymax, xmax, name = (*map(float, sys.argv[1:5]), sys.argv[5])

con = duckdb.connect()
con.sql("INSTALL httpfs; LOAD httpfs; SET s3_region='us-west-2';")

SRC = f"""read_parquet(
    's3://overturemaps-us-west-2/release/{RELEASE}/theme=places/type=place/*',
    hive_partitioning = 1)"""
WHERE = f"""bbox.xmin BETWEEN {xmin} AND {xmax}
        AND bbox.ymin BETWEEN {ymin} AND {ymax}"""

con.sql(f"CREATE TABLE p AS SELECT * FROM {SRC} WHERE {WHERE}")

print(f"\n########## {name} ##########\n")

print("--- 1. КОЛОНКИ ТАБЛИЦЫ ---")
print(con.sql("DESCRIBE p").df().to_string(index=False))

print("\n--- 2. ПОЛНОТА КАТЕГОРИЙ (это идёт прямо на слайд) ---")
print(con.sql("""
SELECT count(*) AS total,
       count(basic_category) AS with_basic_category,
       round(100.0 * count(basic_category) / count(*), 1) AS pct_covered
FROM p""").df().to_string(index=False))

print("\n--- 3. КАК ВЫГЛЯДЯТ ЗНАЧЕНИЯ basic_category (топ-20) ---")
print(con.sql("""
SELECT basic_category, count(*) AS n
FROM p WHERE basic_category IS NOT NULL
GROUP BY 1 ORDER BY n DESC LIMIT 20""").df().to_string(index=False))

print("\n--- 4. СКОЛЬКО ВСЕГО РАЗНЫХ ЗНАЧЕНИЙ ---")
print(con.sql("""
SELECT count(DISTINCT basic_category) AS distinct_basic_category,
       count(DISTINCT split_part(basic_category, '.', 1)) AS distinct_first_part
FROM p WHERE basic_category IS NOT NULL""").df().to_string(index=False))

print("\n--- 5. ЧТО ЛЕЖИТ В taxonomy (первые 5 записей) ---")
try:
    print(con.sql("""
    SELECT basic_category, taxonomy
    FROM p WHERE taxonomy IS NOT NULL LIMIT 5""").df().to_string(index=False))
except Exception as e:
    print("колонки taxonomy нет или другой тип:", e)

print("\n--- 6. ЕСТЬ ЛИ ЕЩЁ СТАРОЕ ПОЛЕ categories ---")
try:
    print(con.sql("SELECT categories FROM p WHERE categories IS NOT NULL LIMIT 3").df().to_string(index=False))
except Exception as e:
    print("колонки categories уже нет:", e)
