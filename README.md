# Urban function maps on open data — FOSS4G Hiroshima 2026

> **This repository is the snapshot uploaded on the day of the first talk. It is kept for the record and is no longer updated.**
>
> | Talk | Where it lives now |
> | --- | --- |
> | *50 Lines of Python: Neighborhood DNA from Overture Maps Places*, lightning talk, 2 September 2026 | [m-erts/neighborhood-dna](https://github.com/m-erts/neighborhood-dna): [slides](https://m-erts.github.io/neighborhood-dna/), [interactive map](https://m-erts.github.io/neighborhood-dna/demo.html), [slides as delivered on stage (PDF)](https://github.com/m-erts/neighborhood-dna/blob/main/docs/slides-as-delivered.pdf), [caveats](https://github.com/m-erts/neighborhood-dna/blob/main/CAVEATS.md) |
> | *Eurostat vs OSM vs Census: Choosing Open Mobility Data for Urban Function Maps* | Accepted; the session was cancelled. |
>
> `talk1/neighborhood_dna.py` pins Overture release `2026-07-22.0`. Overture keeps a release for 60 days and has deleted it, so the quick start below no longer runs as written. Use `dna.py` in [neighborhood-dna](https://github.com/m-erts/neighborhood-dna), which takes the newest release.

Code prepared for two talks:

- **Sep 2, 13:45, Ran1** — *50 Lines of Python: Neighborhood DNA from Overture Maps Places* (lightning)
- *Eurostat vs OSM vs Census: Choosing Open Mobility Data for Urban Function Maps* (accepted; the session was cancelled)

**The question behind both:** which parts of an urban-function-mapping methodology,
built on paid mobile-operator GPS, survive on fully open data — and where exactly
the boundary runs.

## Quick start (talk 1 — no download, no ETL)

```bash
pip install -r requirements.txt
python talk1/neighborhood_dna.py 34.30 132.35 34.48 132.55 hiroshima
# or open talk1/neighborhood_dna.ipynb — replace the city name, run, done
```

DuckDB reads Overture Places straight off S3; the bbox filter runs on the
storage side. Output: `<name>_dna.parquet` with H3 cell geometry and
diversity metrics (Hill numbers, evenness, top-category share).

**Before trusting any number, read [`CAVEATS.md`](CAVEATS.md) — the full
list promised from the stage.** Two of them are the talk: control for cell
size, check the sources column.

## Layout

```
talk1/   Overture DNA: 50-line script, notebook, robustness checks
talk2/   UK/RS/NL/JP mobility: maps, null model, TTWA rule
src/     adapters (Serbia census, Japan MLIT, geo joins), FUA delimitation, metrics
tests/   reconciliation tests that caught real bugs (sums, bijections, zeros)
```

Code MIT · slides & figures CC BY 4.0.

---

# Urban function maps on open data — FOSS4G Hiroshima 2026

Код, подготовленный к двум докладам:

- **2 сентября, 13:45, Ran1** — *50 Lines of Python: Neighborhood DNA from Overture Maps Places* (lightning, 4 мин)
- *Eurostat vs OSM vs Census: Choosing Open Mobility Data for Urban Function Maps* (доклад принят; сессия была отменена)

**Вопрос обоих докладов:** какие части методологии картирования городских функций,
отработанной на платных GPS мобильных операторов, выживают на полностью открытых
данных — и где именно проходит граница.

Юрисдикции: **Сербия** (мало данных, вне ЕС), **Великобритания** (много данных, вне ЕС),
**Япония** (единственные бесплатные GPS-OD), **Нидерланды** (полный стек ЕС).

## Быстрый старт

```bash
pip install -r requirements.txt

# доклад 1: ДНК района из Overture, без скачивания данных
python talk1/neighborhood_dna.py 34.30 132.35 34.48 132.55 hiroshima
```

Аргументы: `ymin xmin ymax xmax имя`. На выходе `<имя>_dna.parquet` с геометрией
ячеек H3 и метриками разнообразия.

## Структура

```
config.yml              версии данных, CRS, пороги — всё в одном месте
talk1/
  neighborhood_dna.py   те самые ~50 строк: DuckDB -> Overture S3 -> H3 -> метрики
src/
  metrics/diversity.py  Hill-числа, энтропия, выровненность, sample coverage
  adapters/od_schema.py приведение OD переписи к схеме RS/GB/JP/NL
  download/SOURCES.md   что откуда качать, с лицензиями
  fua/                  делимитация (портируется из существующих ноутбуков)
data/raw|interim|processed
```

## Методологические решения и почему именно так

**H3 вместо градусного грида.** Ячейка 0.01° в Стокгольме — 0.63 км², в Афинах — 0.97 км².
Полтора раза разницы по площади. Счётчики POI на такой сетке между странами
несопоставимы: северные страны механически проигрывают.

**Япония не в EPSG:3857.** Web Mercator растягивает расстояния в 1/cos(широты).
Сетка «1 км» на самом деле даёт 825 м в Хиросиме и 702 м на Хоккайдо — внутри
одной страны разброс площади в 1.7 раза. Для сеточных операций используется
японская стандартная сетка JIS X 0410, та же, на которой публикуются e-Stat и MLIT.

**Hill-числа вместо richness.** Число присутствующих категорий механически растёт
с числом объектов в ячейке. Сравнивая по нему места с разной полнотой данных,
меряешь полноту, а не функцию. Hill q1 и q2 к этому устойчивее
(Chao & Jost 2012). `sample_coverage` даётся как диагностика.

**Порог 10 POI на ячейку.** В ячейке с одним объектом `top_cat_share = 1.0` —
формально «идеальная монофункциональность», содержательно шум.

**`basic_category`, не `categories`.** Свойство `categories` в Overture Places
удаляется в сентябрьском релизе 2026.

**Версия релиза зафиксирована** в `config.yml`. Overture обновляется ежемесячно;
без фиксации числа невоспроизводимы.

## Что этот код НЕ делает

FRA (Functional Rural Areas) для Сербии не строятся, и это не недоработка.
Алгоритм требует нетрудовых поездок на сетке 1 км. Перепись даёт потоки
община → община и только работу с учёбой. Подать в него трудовые поездки
технически можно — получится уверенный неправильный ответ, потому что FRA
существуют именно там, где маятниковая миграция перестаёт описывать жизнь.

Бесплатно оба требования выполняются в одной стране мира — в Японии,
данными MLIT. Поэтому FRA показываются на японском кейсе.

## Источники

См. `src/download/SOURCES.md`.

## Лицензия

Код — MIT. Данные — по лицензиям источников, см. SOURCES.md.
Overture Places требует атрибуции по каждому источнику-донору.
