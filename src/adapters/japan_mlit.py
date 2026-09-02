"""
Парсер MLIT «全国の人流オープンデータ» — monthly_fromto_city.

Структура архива:
    monthly_fromto_city_<PREF>.zip
      └ <PREF>/<год>/<месяц>/monthly_fromto_city.csv.zip
                              └ monthly_fromto_city.csv

Колонки (из официального «データ定義書 –滞在人口From-Toデータ-», стр. 6):

    year, month
    dayflag    0 = 休日 выходной, 1 = 平日 будни, 2 = 全日 все дни
    timezone   0 = 昼 день,      1 = 深夜 ночь,   2 = 終日 сутки
    prefcode   код префектуры (2 знака)
    citycode   код муниципалитета (5 знаков)
    from_area  居住地区分 — КАТЕГОРИЯ места жительства, НЕ код:
                 0 同一市区町村              тот же муниципалитет
                 1 同一都道府県かつ異なる市区町村  та же префектура, другой муниципалитет
                 2 同一の地方ブロックかつ異なる都道府県  тот же регион, другая префектура
                 3 異なる地方ブロック         другой регион
    population 滞在人口（平均） — среднее присутствие, 10人未満は出力しない

--------------------------------------------------------------------------
ГЛАВНОЕ, ЧТО НАДО ПОНИМАТЬ ПРО ЭТОТ ФАЙЛ

1. Это НЕ OD-матрица. Название «From-To» вводит в заблуждение: «From» —
   это одна из четырёх вложенных полос дальности, а не муниципалитет
   происхождения. Структура ровно та же, что в сербской переписи:

       Сербия:  та же община / другая община той же области /
                другая область / за границей
       Япония:  тот же муниципалитет / та же префектура /
                тот же регион / другой регион

   Делимитацию функциональных ареалов из этого построить нельзя —
   нет пар «откуда → куда».

2. Это присутствие (滞在人口), а не поездки. Человек, простоявший
   в муниципалитете весь день, и человек, заехавший на час, попадают
   в разные доли одного и того же среднего.

3. Объём НОРМИРОВАН. Суммарное присутствие по префектуре Хиросима
   за 2019, 2020 и 2021 совпадает с точностью до 0,3 % — при том, что
   реальная мобильность в 2020 рухнула. Значит, межгодовые сравнения
   ОБЪЁМА бессмысленны; сравнивать можно только СОСТАВ (доли).
   Сдвиг состава при этом виден: доля «свои» на будний день выросла
   с 0,632 (2019) до 0,677 (2020).

4. Ловушка кодов: у города Накагава (преф. Фукуока) в данных 2019 года
   стоит старый код 40305 вместо 40231. При джойне с мастером за 2020-й
   строка потеряется.
"""

from __future__ import annotations

import glob
import io
import os
import zipfile

import pandas as pd

__all__ = ["read_fromto", "read_city_master", "presence_self_containment",
           "FROM_AREA", "DAYFLAG", "TIMEZONE"]

FROM_AREA = {0: "same_city", 1: "same_pref", 2: "same_region", 3: "other_region"}
DAYFLAG = {0: "holiday", 1: "weekday", 2: "all_days"}
TIMEZONE = {0: "daytime", 1: "night", 2: "all_day"}

#: код Накагавы до слияния — в данных 2019 года
CITYCODE_FIXES = {40305: 40231}


def read_fromto(root: str) -> pd.DataFrame:
    """
    Читает все month/year из распакованного monthly_fromto_city_<PREF>.

    root — папка, внутри которой лежит <PREF>/<год>/<месяц>/*.csv.zip.
    Внутренние .csv.zip распаковываются на лету, на диск ничего не пишется.
    """
    pat = os.path.join(root, "**", "monthly_fromto_city.csv.zip")
    files = sorted(glob.glob(pat, recursive=True))
    if not files:
        raise FileNotFoundError(f"не найдено ни одного monthly_fromto_city.csv.zip в {root}")

    frames = []
    for z in files:
        with zipfile.ZipFile(z) as zf:
            name = next(n for n in zf.namelist() if n.endswith(".csv"))
            frames.append(pd.read_csv(io.BytesIO(zf.read(name))))
    df = pd.concat(frames, ignore_index=True)
    df["citycode"] = df["citycode"].replace(CITYCODE_FIXES)
    return df


def read_city_master(path: str) -> pd.DataFrame:
    """Мастер префектур и муниципалитетов. Берите UTF-8 версию."""
    with zipfile.ZipFile(path) as zf:
        name = next(n for n in zf.namelist() if n.endswith(".csv"))
        m = pd.read_csv(io.BytesIO(zf.read(name)), dtype={"prefcode": str,
                                                          "citycode": str})
    m["citycode"] = m["citycode"].astype(int)
    return m


def presence_self_containment(df: pd.DataFrame) -> pd.DataFrame:
    """
    Доля присутствия, приходящаяся на местных жителей.

    Аналог RBSC, но по присутствию, а не по поездкам, и знаменатель —
    всё присутствие в муниципалитете. С британским RBSC несопоставимо
    напрямую; с сербским — сопоставимо по структуре категорий,
    но не по единице наблюдения.

    Возвращает по строке на (year, month, dayflag, timezone, citycode).
    """
    p = df.pivot_table(index=["year", "month", "dayflag", "timezone", "citycode"],
                       columns="from_area", values="population",
                       aggfunc="sum").fillna(0.0)
    p = p.rename(columns=FROM_AREA)
    for c in FROM_AREA.values():
        if c not in p.columns:
            p[c] = 0.0
    p["total"] = p[list(FROM_AREA.values())].sum(axis=1)
    p["sc"] = (p.same_city / p.total).where(p.total > 0)
    # доля приезжих из-за пределов префектуры — мера «дальнего» притяжения
    p["far_share"] = ((p.same_region + p.other_region) / p.total).where(p.total > 0)
    return p.reset_index()


if __name__ == "__main__":
    import sys
    d = read_fromto(sys.argv[1])
    p = presence_self_containment(d)
    print(f"строк {len(d):,}  муниципалитетов {d.citycode.nunique()}  "
          f"годы {sorted(d.year.unique())}")
    for tz, tzn in [(0, "день"), (1, "ночь")]:
        s = p[(p.timezone == tz) & (p.dayflag == 1)]
        print(f"  будни, {tzn}: медиана SC {s.sc.median():.3f}")
