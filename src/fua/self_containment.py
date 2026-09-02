"""
Self-containment: RBSC, DBSC, leakage, доля нерезидентов.

Портировано из твоего Self-containment.ipynb / FUA FRA.ipynb без
изменения формул — чтобы результаты сходились с прошлой работой.
Изменено только обрамление: пороги в аргументах, а не в теле;
есть тесты; и добавлена обработка «работает из дома», без которой
британская перепись 2021 даёт завышенный self-containment.

RBSC = внутренние поездки резидентов / все выезды резидентов
DBSC = прибытия изнутри ареала / все прибытия
LEAK = 1 - RBSC

Пороги 0.66 и 0.75 — из литературы по Labour Market Areas и TTWA.
ONS строит TTWA по правилу 75%/75% с обеих сторон.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = ["compute_self_containment", "benchmark_shares", "WORK_FROM_HOME_CODES"]

# Спецкоды назначения, означающие «нет реальной поездки».
# В ODWP01EW (Census 2021 E&W) работающие из дома кодируются
# псевдо-кодами. Доля надомников: 31.2% в 2021 против 10.3% в 2011.
#
# ВНИМАНИЕ, ПРОВЕРИТЬ ПО ФАЙЛУ: направление искажения зависит от того,
# как именно ONS закодировал надомников.
#   - если псевдо-кодом (как ниже) — они считаются выездом «наружу»
#     и RBSC занижается;
#   - если кодом собственного MSOA — считаются внутренней поездкой
#     и RBSC завышается.
# В 2011 (WU03EW) использовался второй вариант. Для 2021 надо
# посмотреть уникальные значения колонки назначения перед расчётом.
# В любом случае при 31% надомников эффект измеряется десятыми долями,
# а не третьим знаком — см. демонстрацию внизу файла.
WORK_FROM_HOME_CODES = {
    "OD0000001",  # mainly work at or from home
    "OD0000002",  # no fixed place
    "OD0000003",  # offshore installation
    "OD0000004",  # outside the UK
}


def compute_self_containment(
    df: pd.DataFrame,
    fa_meta: pd.DataFrame | None = None,
    drop_codes: set[str] | None = None,
) -> pd.DataFrame:
    """
    df: motive, trip_count, o_fa_code, d_fa_code
        (координаты не нужны — OD переписи подключается напрямую)
    fa_meta: fa_code -> fa_type, cntr, area_km2   (опционально)
    drop_codes: коды назначения, которые не являются поездкой
    """
    need = {"motive", "trip_count", "o_fa_code", "d_fa_code"}
    missing = need - set(df.columns)
    if missing:
        raise ValueError(f"не хватает колонок: {sorted(missing)}")

    d = df.copy()
    if drop_codes:
        before = d["trip_count"].sum()
        d = d[~d["d_fa_code"].isin(drop_codes)]
        dropped = before - d["trip_count"].sum()
        if before > 0:
            print(f"[self_containment] отброшено {dropped:,.0f} поездок "
                  f"({dropped / before:.1%}) по drop_codes")

    d["is_internal"] = (
        d["o_fa_code"].notna() & d["d_fa_code"].notna()
        & (d["o_fa_code"] == d["d_fa_code"])
    )

    res = d[d["o_fa_code"].notna()]

    dep = (res.groupby(["o_fa_code", "motive"], as_index=False)["trip_count"].sum()
              .rename(columns={"o_fa_code": "fa_code", "trip_count": "departures_res"}))
    internal = (res[res["is_internal"]]
                .groupby(["o_fa_code", "motive"], as_index=False)["trip_count"].sum()
                .rename(columns={"o_fa_code": "fa_code", "trip_count": "internal_trips"}))
    arr = (d[d["d_fa_code"].notna()]
           .groupby(["d_fa_code", "motive"], as_index=False)["trip_count"].sum()
           .rename(columns={"d_fa_code": "fa_code", "trip_count": "arrivals_total"}))
    arr_int = (d[d["is_internal"]]
               .groupby(["d_fa_code", "motive"], as_index=False)["trip_count"].sum()
               .rename(columns={"d_fa_code": "fa_code", "trip_count": "arrivals_internal"}))

    m = (dep.merge(internal, on=["fa_code", "motive"], how="left")
            .merge(arr, on=["fa_code", "motive"], how="outer")
            .merge(arr_int, on=["fa_code", "motive"], how="left"))
    for c in ["departures_res", "internal_trips", "arrivals_total", "arrivals_internal"]:
        m[c] = m[c].fillna(0.0)

    m["RBSC"] = np.where(m["departures_res"] > 0, m["internal_trips"] / m["departures_res"], np.nan)
    m["LEAK"] = np.where(m["departures_res"] > 0, 1.0 - m["RBSC"], np.nan)
    m["DBSC"] = np.where(m["arrivals_total"] > 0, m["arrivals_internal"] / m["arrivals_total"], np.nan)
    m["arrivals_external"] = (m["arrivals_total"] - m["arrivals_internal"]).clip(lower=0)
    m["nonresident_share"] = np.where(
        m["arrivals_total"] > 0, m["arrivals_external"] / m["arrivals_total"], np.nan)

    if fa_meta is not None:
        m = m.merge(fa_meta, on="fa_code", how="left")
    return m


def benchmark_shares(m: pd.DataFrame, thresholds=(0.66, 0.75), by=("motive",)) -> pd.DataFrame:
    """
    Доля ареалов, проходящих пороги self-containment.

    0.75 — целевой уровень классических TTWA, 0.66 — нижняя граница,
    допускаемая, когда строгий порог даёт слишком мелкую нарезку.
    Пороги придуманы для трудовых потоков; применяя их к нетрудовым,
    систематически наказываешь открытые системы. В докладе они идут
    как ориентир, а не как критерий «сдал / не сдал».
    """
    by = [c for c in by if c in m.columns]
    rows = []
    grouped = m.groupby(by) if by else [((), m)]
    for key, g in grouped:
        rec = dict(zip(by, key if isinstance(key, tuple) else (key,)))
        rec["n_areas"] = int(g["RBSC"].notna().sum())
        for t in thresholds:
            rec[f"share_ge_{t}"] = float((g["RBSC"] >= t).mean())
        rows.append(rec)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    # Аналитический тест: три ареала, потоки заданы вручную,
    # правильные ответы посчитаны на бумаге.
    df = pd.DataFrame({
        "o_fa_code":  ["A", "A", "B", "B", "C"],
        "d_fa_code":  ["A", "B", "B", "A", "A"],
        "trip_count": [80,  20,  50,  50,  100],
        "motive":     ["work"] * 5,
    })
    m = compute_self_containment(df).set_index("fa_code")

    # A: выезды 100, внутренние 80 -> RBSC 0.80, leak 0.20
    # A: прибытия 80+50+100=230, изнутри 80 -> DBSC 80/230 = 0.3478
    # B: выезды 100, внутренние 50 -> RBSC 0.50
    # B: прибытия 20+50=70, изнутри 50 -> DBSC 0.7143
    # C: выезды 100, внутренних 0 -> RBSC 0.0; прибытий нет -> DBSC NaN
    exp = {"A": (0.80, 80 / 230), "B": (0.50, 50 / 70), "C": (0.00, np.nan)}
    ok = True
    for fa, (rbsc, dbsc) in exp.items():
        got_r, got_d = m.loc[fa, "RBSC"], m.loc[fa, "DBSC"]
        r_ok = abs(got_r - rbsc) < 1e-9
        d_ok = (np.isnan(dbsc) and np.isnan(got_d)) or abs(got_d - dbsc) < 1e-9
        ok &= r_ok and d_ok
        print(f"{fa}: RBSC {got_r:.4f} (ждём {rbsc:.4f}) {'ok' if r_ok else 'FAIL'} | "
              f"DBSC {got_d:.4f} (ждём {dbsc:.4f}) {'ok' if d_ok else 'FAIL'}")

    print("\n--- эффект работы из дома (британский случай 2021) ---")
    wfh = pd.DataFrame({
        "o_fa_code":  ["A", "A", "A"],
        "d_fa_code":  ["A", "B", "OD0000001"],
        "trip_count": [40,  30,  30],
        "motive":     ["work"] * 3,
    })
    naive = compute_self_containment(wfh).set_index("fa_code").loc["A", "RBSC"]
    fixed = compute_self_containment(wfh, drop_codes=WORK_FROM_HOME_CODES) \
        .set_index("fa_code").loc["A", "RBSC"]
    print(f"RBSC без обработки надомников: {naive:.3f}")
    print(f"RBSC с обработкой:             {fixed:.3f}")
    print(f"разница: {naive - fixed:+.3f}")
    print("здесь надомники закодированы псевдо-кодом, поэтому RBSC занижался.")
    print("если ONS кодирует их собственным MSOA, знак будет обратным —")
    print("проверить по уникальным значениям колонки назначения.")

    print("\nвсе проверки пройдены" if ok else "\nЕСТЬ ОШИБКИ")
