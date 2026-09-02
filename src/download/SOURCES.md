# Источники — что откуда качать

Проверено 17 августа 2026. Лицензии перечитать в момент скачивания.
Всё складывается в `data/raw/<CC>/`.

## OD переписи — ядро доклада 2

| CC | Источник | Где взять | Формат | Примечание |
|----|----------|-----------|--------|------------|
| RS | Перепись 2022, «Дневне миграције» | [Excel-таблицы Пописа 2022](https://popis2022.stat.gov.rs/popisni-podaci-eksel-tabele/) · [база распространения, «Табела 1: Дневне миграције»](https://data.stat.gov.rs/Home/Result/31040211?languageCode=sr-Latn) | Excel / веб-БД | 1 048 825 мигрантов; 75.9% работа, 24.1% учёба. Таблица 2 — работающие, таблица 3 — учащиеся |
| GB | Census 2021 OD, **ODWP01EW** — location of usual residence and place of work | [прямая ссылка, 77 МБ](https://www.nomisweb.co.uk/output/census/2021/odwp01ew.zip) · [страница релиза](https://www.nomisweb.co.uk/sources/census_2021_od) | zip с CSV по типам геометрии + метаданные XLS | Лучшее разрешение из четырёх — до MSOA. **Читать про COVID ниже** |
| JP | Перепись 2020, 従業地・通学地集計 | [e-Stat](https://www.e-stat.go.jp/en) | CSV/JSON через API | Нужен бесплатный appId. Есть учёба И вид транспорта |
| NL | Потоки между муниципалитетами | [CBS StatLine](https://opendata.cbs.nl/statline/) | CSV/OData | Коды вида GM0363 |

**appId для e-Stat не коммитить.** Сессии на FOSS4G записываются и выкладываются
на YouTube — учётные данные на экране недопустимы. Класть в `.env`.

## Официальные функциональные регионы — для валидации

| Что | Где | Зачем |
|-----|-----|-------|
| TTWA **2011** (UK) | [data.gov.uk](https://www.data.gov.uk/dataset/1b3604bc-8fd3-4b01-a0fd-0f3bf7fcd160/travel-to-work-areas-ttwa-boundaries) · [ONS Open Geography](https://geoportal.statistics.gov.uk/) | **Эталон метода.** 228 зон, построены ONS по правилу self-containment 75%/75% |

### ВАЖНО: TTWA на данных 2021 не существует

Действующие TTWA построены на переписи **2011**, и ONS их пока не обновил —
именно потому, что не разобрался с влиянием ковида. Доля работающих из дома
выросла с **10.3% в 2011 до 31.2% в 2021**.

Последствия для плана валидации:

1. Валидировать метод надо на **переписи 2011** против TTWA 2011 —
   это чистое сравнение «то же на том же».
   Данные 2011: [Nomis, WU03EW](https://www.nomisweb.co.uk/sources/census_2011_od).
2. Прогон на **2021** — это уже не валидация, а отдельный результат:
   насколько сдвинулась функциональная география, когда треть страны
   ушла на удалёнку. На этот вопрос официальной статистики пока нет.
3. Надомников в ODWP01EW обязательно обработать явно — см.
   `src/fua/self_containment.py`, `WORK_FROM_HOME_CODES`. Направление
   искажения зависит от кодировки, проверить по уникальным значениям.

Это делает британский кейс сильнее, а не слабее: метод валидируется
на 2011, а потом валидированным методом отвечает на вопрос, который
статслужба ещё не закрыла.
| GHS-FUA | [GHSL](https://human-settlement.emergency.copernicus.eu/ghs_fua.php) | Глобально, покрывает RS и JP. Внешняя сверка |
| JRC FUA/FRA | [JRC Data Catalogue](https://data.jrc.ec.europa.eu/) | Только ЕС — отсюда и сербский пробел |

## Границы LAU

| CC | Источник |
|----|----------|
| RS | ГИС РЗС / OSM admin_level=7 (општине) |
| GB | ONS Open Geography Portal (MSOA / LAD 2021) |
| JP | 国土数値情報 (MLIT NLNI), административные границы |
| NL | PDOK / CBS wijk- en buurtkaart |

## POI и землепользование — доклад 1

| Что | Где | Лицензия |
|-----|-----|----------|
| Overture Places | `s3://overturemaps-us-west-2/release/2026-07-22.0/theme=places/type=place/*` | смешанная, атрибуция по источнику |
| OSM (сверка полноты) | Geofabrik / Overpass — **код у тебя уже есть** в `download POI.ipynb` | ODbL |
| Urban Atlas 2021 | [Copernicus Land](https://land.copernicus.eu/en/products/urban-atlas) | бесплатно, регистрация. Покрывает Сербию (EEA38) |

## Население и урбанизация

| Что | Где | Лицензия |
|-----|-----|----------|
| GHS-POP / GHS-SMOD R2023A | [GHSL](https://human-settlement.emergency.copernicus.eu/download.php) | CC BY 4.0. Единственный слой, согласованный между RS, GB, JP, NL |
| Eurostat census grid 2021 | [Eurostat GISCO](https://ec.europa.eu/eurostat/web/gisco/geodata/population-distribution/population-grids) | CC BY 4.0. **Сербии и Великобритании нет** |
| WorldPop 1 км | [worldpop.org](https://www.worldpop.org/) | CC BY 4.0. Уже используется в твоём FRA-пайплайне |

## Мобильность сверх переписи

| Что | Где | Примечание |
|-----|-----|------------|
| MLIT 人流オープンデータ | [G-Spatial Information Center](https://www.geospatial.jp/) | **Только Япония.** Меш 1 км, OD, все цели поездок. Единственный источник, на котором FRA строятся бесплатно. Период 2019–2021 — захватывает ковид |
| GTFS | [Mobility Database](https://mobilitydatabase.org/) / [Transitland](https://www.transit.land/) | JP: GTFS-JP, во многом CC0. RS: ГСП Белград + 5 городов. Нужен для r5py |
| ODiN (NL) | [CBS микроданные](https://www.cbs.nl/nl-nl/onze-diensten/maatwerk-en-microdata) | Обследование с целями поездок. Выборка, география грубая |
| National Travel Survey (GB) | UK Data Service | То же самое |

> Про ODiN и NTS: цели поездок там есть, но без нужной географии.
> Перепись даёт географию без цели. Совместить бесплатно можно только в Японии —
> это формулировка для слайда, а не «нетрудовых данных не существует».

## Что качать в первую очередь

1. OD Сербии (Excel) — от него зависит формат адаптера
2. TTWA + Census OD Великобритании — валидация метода
3. Границы LAU всех четырёх
4. Overture по четырём городам — для доклада 1, ближайший дедлайн
