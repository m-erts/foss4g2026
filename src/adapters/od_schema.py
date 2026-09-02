"""
Приведение OD-таблиц к единой схеме.

ЕДИНСТВЕННАЯ точка интеграции доклада 2. Твой существующий
compute_self_containment_tables() требует ровно четыре колонки:

    motive, trip_count, o_fa_code, d_fa_code

Никаких координат — значит OD из переписи подключается обычным
join'ом (муниципалитет -> код ареала), без point-in-polygon.
Это проще, чем текущий путь через GPS-точки.

Целевая схема на выходе adapters:
    ORIG_CODE : str   код LAU происхождения (нормализованный)
    DEST_CODE : str   код LAU назначения
    trip_count: float величина потока
    motive    : str   "work" | "study" | "other"
"""

from __future__ import annotations

import pandas as pd

TARGET_COLS = ["ORIG_CODE", "DEST_CODE", "trip_count", "motive"]


def _finalize(df: pd.DataFrame, country: str) -> pd.DataFrame:
    missing = [c for c in TARGET_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"[{country}] после адаптера не хватает колонок: {missing}")
    out = df[TARGET_COLS].copy()
    out["ORIG_CODE"] = out["ORIG_CODE"].astype(str).str.strip()
    out["DEST_CODE"] = out["DEST_CODE"].astype(str).str.strip()
    out["trip_count"] = pd.to_numeric(out["trip_count"], errors="coerce")
    out = out.dropna(subset=["trip_count"])
    out = out[out["trip_count"] > 0]
    return out.reset_index(drop=True)


# ---------------------------------------------------------------- Сербия
def adapt_rs(df: pd.DataFrame) -> pd.DataFrame:
    """
    Перепись 2022, «Дневне миграције» (РЗС), Excel.
    1 048 825 дневных мигрантов: 75.9% работающие, 24.1% учащиеся.

    TODO после получения файла: подставить реальные имена колонок.
    Коды общин РЗС — не то же самое, что LAU Евростата; понадобится
    таблица соответствия, если будем сшивать с европейскими слоями.
    """
    ren = {
        "opstina_stanovanja": "ORIG_CODE",
        "opstina_rada": "DEST_CODE",
        "broj": "trip_count",
    }
    df = df.rename(columns={k: v for k, v in ren.items() if k in df.columns})
    if "motive" not in df.columns:
        df["motive"] = "work"
    return _finalize(df, "RS")


# ------------------------------------------------------- Великобритания
def adapt_gb(df: pd.DataFrame) -> pd.DataFrame:
    """
    Census 2021 origin-destination, ONS/Nomis. Уровень MSOA или LA.
    Валидация метода идёт против официальных TTWA (порог 75%/75%).
    """
    ren = {
        "Middle layer Super Output Areas code": "ORIG_CODE",
        "MSOA of workplace code": "DEST_CODE",
        "Count": "trip_count",
        "usual_residence": "ORIG_CODE",
        "place_of_work": "DEST_CODE",
        "obs_value": "trip_count",
    }
    df = df.rename(columns={k: v for k, v in ren.items() if k in df.columns})
    if "motive" not in df.columns:
        df["motive"] = "work"
    return _finalize(df, "GB")


# ---------------------------------------------------------------- Япония
def adapt_jp(df: pd.DataFrame) -> pd.DataFrame:
    """
    Перепись 2020, 従業地・通学地集計 (e-Stat).
    Единственная из четырёх, где учёба отделена от работы —
    сохраняем это, motive не схлопываем.
    """
    ren = {
        "residence_code": "ORIG_CODE",
        "work_school_code": "DEST_CODE",
        "value": "trip_count",
    }
    df = df.rename(columns={k: v for k, v in ren.items() if k in df.columns})
    if "motive" not in df.columns:
        df["motive"] = "work"
    # коды муниципалитетов Японии — 5 знаков с ведущими нулями
    for c in ("ORIG_CODE", "DEST_CODE"):
        df[c] = df[c].astype(str).str.zfill(5)
    return _finalize(df, "JP")


# ----------------------------------------------------------- Нидерланды
def adapt_nl(df: pd.DataFrame) -> pd.DataFrame:
    """CBS, потоки между муниципалитетами (gemeenten). Коды вида GM0363."""
    ren = {
        "woongemeente": "ORIG_CODE",
        "werkgemeente": "DEST_CODE",
        "aantal": "trip_count",
    }
    df = df.rename(columns={k: v for k, v in ren.items() if k in df.columns})
    if "motive" not in df.columns:
        df["motive"] = "work"
    return _finalize(df, "NL")


ADAPTERS = {"RS": adapt_rs, "GB": adapt_gb, "JP": adapt_jp, "NL": adapt_nl}


def standardize_od_schema(df: pd.DataFrame, country_code: str) -> pd.DataFrame:
    """Замена одноимённой заглушки из FUA FRA.ipynb."""
    cc = country_code.upper()
    if cc not in ADAPTERS:
        raise KeyError(f"нет адаптера для {cc}; есть: {sorted(ADAPTERS)}")
    return ADAPTERS[cc](df)
