"""
Привязка сербской переписи к границам общин ГеоСрбије.

Проблема, ради которой существует этот модуль: в шейпфайле Op_tina.shp
атрибутивная таблица записана с потерей кодировки. Кириллическое поле
opstina_im целиком превратилось в «?????», а в латинском opstina__1
каждый символ вне ASCII заменён на «?»:

    ARAN?ELOVAC   <- ARANĐELOVAC
    VRA?AR        <- VRAČAR
    ?AKOVICA      <- ĐAKOVICA

Поэтому джойн идёт по имени с «?» как шаблоном на один символ. И вот
чем это опасно: шаблон .AKOVICA подходит и к ĐAKOVICA, и к RAKOVICA.
На первой версии карты косовская Ђаковица получила данные белградской
Раковицы и вылезла отдельным пятном в 587 км² на юге. Ошибка была видна
глазами только потому, что полигон не примыкал к остальной Сербии.

Отсюда правила, зашитые ниже:

 1. точные совпадения разбираются ПЕРВЫМИ, шаблон применяется только
    к остатку;
 2. шаблонное совпадение принимается, только если оно единственное;
 3. Косово (коды 9xxxx) исключается: перепись 2022 его не охватывает,
    и оставлять эти полигоны — значит либо красить их мусором, либо
    оставлять дыру, которую примут за данные;
 4. на выходе проверяется биекция: одна община — один полигон.
"""

from __future__ import annotations

import re

import pandas as pd

__all__ = ["cyr_to_ascii", "load_municipalities", "join_census",
           "KOSOVO_PREFIX"]

#: коды общин Косова в матичном регистре РЗС
KOSOVO_PREFIX = "9"

# сербская кириллица -> ASCII. Диграфы Љ/Њ/Џ дают ДВЕ буквы —
# на этом я уже один раз ошиблась: Ариље превращалось в ARILE
# и не находило ARILJE.
_CYR = {
    "А": "A", "Б": "B", "В": "V", "Г": "G", "Д": "D", "Ђ": "D", "Е": "E",
    "Ж": "Z", "З": "Z", "И": "I", "Ј": "J", "К": "K", "Л": "L", "Љ": "LJ",
    "М": "M", "Н": "N", "Њ": "NJ", "О": "O", "П": "P", "Р": "R", "С": "S",
    "Т": "T", "Ћ": "C", "У": "U", "Ф": "F", "Х": "H", "Ц": "C", "Ч": "C",
    "Џ": "DZ", "Ш": "S",
}


def cyr_to_ascii(s: str) -> str:
    """Кириллица -> голый ASCII в верхнем регистре, без пробелов."""
    up = "".join(_CYR.get(c, c) for c in str(s).upper())
    return re.sub(r"[^A-Z]", "", up)


def _split_qualifier(s: str) -> tuple[str, str]:
    """PALILULA (BEOGRAD) -> ('PALILULA', 'BEOGRAD')."""
    s = str(s).upper()
    q = re.search(r"\(([^)]*)\)", s)
    base = re.sub(r"\([^)]*\)", "", s)
    return (re.sub(r"[^A-Z?]", "", base),
            re.sub(r"[^A-Z?]", "", q.group(1)) if q else "")


def load_municipalities(shp_path: str, drop_kosovo: bool = True):
    """Читает Op_tina.shp, добавляет key_lat и qual."""
    import geopandas as gpd
    g = gpd.read_file(shp_path)
    g[["key_lat", "qual"]] = g.opstina__1.apply(
        lambda s: pd.Series(_split_qualifier(s)))
    if drop_kosovo:
        g = g[~g.opstina_ma.astype(str).str.startswith(KOSOVO_PREFIX)]
    return g.reset_index(drop=True)


def join_census(g, census: pd.DataFrame, name_col: str = "name",
                area_col: str = "area", strict: bool = True):
    """
    Привязывает таблицу переписи к полигонам.

    census должен содержать колонку с кириллическим именем общины и
    (для разведения тёзок) колонку области.

    strict=True — падать, если биекция не получилась.
    """
    c = census.copy()
    c["base"] = c[name_col].map(cyr_to_ascii)
    c["area_ascii"] = c[area_col].map(cyr_to_ascii) if area_col in c else ""
    # уникальный ключ: имя, а для тёзок — имя + область
    dup = c.base.duplicated(keep=False)
    c["key_lat"] = c.base.where(~dup, c.base + "@" + c.area_ascii)

    def qual_fits(qual: str, area_ascii: str) -> bool:
        """Уточнение из скобок как префикс названия области.

        «PALILULA (NI?)» -> qual 'NI?' -> шаблон 'NI.' против
        'NISAVSKAOBLAST'[:3] = 'NIS'. «(BEOGRAD)» против
        'BEOGRADSKAOBLAST...'[:7]. Сравнение по длине уточнения.
        """
        if not qual:
            return False
        return re.match("^" + qual.replace("?", ".") + "$",
                        area_ascii[:len(qual)]) is not None

    taken: dict[int, str] = {}
    used: set[str] = set()

    def claim(i, key):
        taken[i] = key
        used.add(key)

    # шаг 1: точные совпадения по имени, без тёзок и без «?»
    unique_exact = {r.key_lat: r.key_lat for _, r in c[~dup].iterrows()}
    for i, row in g.iterrows():
        if "?" in row.key_lat:
            continue
        if row.key_lat in unique_exact and row.key_lat not in used:
            claim(i, row.key_lat)

    # шаг 2: тёзки — разводим по уточнению в скобках
    for i, row in g.iterrows():
        if i in taken:
            continue
        hits = [r for _, r in c[dup].iterrows()
                if r.base == row.key_lat.replace("?", ".")[:len(r.base)]
                or re.match("^" + row.key_lat.replace("?", ".") + "$", r.base)]
        hits = [r for r in hits if qual_fits(row.qual, r.area_ascii)
                and r.key_lat not in used]
        if len(hits) == 1:
            claim(i, hits[0].key_lat)
        elif len(hits) > 1 and strict:
            raise ValueError(f"{row.opstina__1!r}: уточнение не развело тёзок")

    # шаг 3: остаток — шаблон, только если совпадение единственное
    free = [k for k in c.key_lat if k not in used]
    for i, row in g.iterrows():
        if i in taken or "?" not in row.key_lat:
            continue
        rx = re.compile("^" + row.key_lat.replace("?", ".") + "$")
        hits = [k for k in free if rx.match(k.split("@")[0])]
        if len(hits) == 1:
            claim(i, hits[0])
            free.remove(hits[0])
        elif len(hits) > 1 and strict:
            raise ValueError(
                f"шаблон {row.opstina__1!r} подходит к нескольким общинам: "
                f"{hits}. Именно так Ђаковица однажды получила данные Раковицы."
            )

    g = g.copy()
    g["matched"] = pd.Series(taken)
    out = g.dropna(subset=["matched"]).merge(
        c, left_on="matched", right_on="key_lat", how="left",
        suffixes=("", "_census"))

    if strict:
        n_dup = out.matched.duplicated().sum()
        if n_dup:
            raise ValueError(f"{n_dup} общин получили больше одного полигона")
        missing = set(c.key_lat) - set(out.matched)
        if missing:
            raise ValueError(f"без полигона остались: {sorted(missing)}")
    return out
