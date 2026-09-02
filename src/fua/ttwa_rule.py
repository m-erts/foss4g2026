"""
Правило валидности TTWA и досборка ареалов под него.

Официальный критерий ONS — скользящая шкала между двумя точками:

    рабочая сила >= 3 500   и   самодостаточность >= 75,0 %
    рабочая сила >= 25 000  и   самодостаточность >= 66,7 %

между ними порог по самодостаточности линейно снижается. То есть
крупному ареалу прощается большая утечка, мелкому — нет. Ареал
меньше 3 500 работающих невалиден при любой самодостаточности.

Зачем это здесь. Моя делимитация даёт 197 ареалов на Англию и Уэльс
за 2011 год, а официальных TTWA там 167 (149 в Англии + 18 в Уэльсе;
остальные до 228 — Шотландия, Северная Ирландия и шесть трансграничных).
Разница ровно в том, что у меня нет ограничения снизу: минимальный
ареал — один MSOA. Правило TTWA такие куски поглощает.

Самодостаточность считается двусторонней, как в ONS:
    SC = min(доля работающих жителей, работающих внутри;
             доля рабочих мест, занятых своими жителями)
Слабейшая из двух сторон и определяет годность.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = ["min_self_containment", "area_stats", "is_valid", "enforce_ttwa_rule"]

MIN_SIZE = 3_500
BIG_SIZE = 25_000
SC_SMALL = 0.75
SC_BIG = 2.0 / 3.0


def min_self_containment(size: float | np.ndarray):
    """Порог самодостаточности как функция размера ареала."""
    size = np.asarray(size, dtype=float)
    t = np.clip((size - MIN_SIZE) / (BIG_SIZE - MIN_SIZE), 0.0, 1.0)
    return SC_SMALL + t * (SC_BIG - SC_SMALL)


def area_stats(od: pd.DataFrame, assign: dict) -> pd.DataFrame:
    """
    Для каждого ареала: жители, рабочие места, внутренние потоки
    и двусторонняя самодостаточность.
    """
    d = od.copy()
    d["oa"] = d.origin.map(assign)
    d["da"] = d.dest.map(assign)
    d = d.dropna(subset=["oa", "da"])
    res = d.groupby("oa").flow.sum()                 # работающие жители
    job = d.groupby("da").flow.sum()                 # рабочие места
    ins = d[d.oa == d.da].groupby("oa").flow.sum()   # внутренние
    s = pd.DataFrame({"residents": res, "jobs": job, "internal": ins}).fillna(0.0)
    s["sc_supply"] = (s.internal / s.residents).where(s.residents > 0, 0.0)
    s["sc_demand"] = (s.internal / s.jobs).where(s.jobs > 0, 0.0)
    s["sc"] = s[["sc_supply", "sc_demand"]].min(axis=1)
    s["size"] = s.residents
    return s


def is_valid(stats: pd.DataFrame) -> pd.Series:
    return (stats["size"] >= MIN_SIZE) & (stats.sc >= min_self_containment(stats["size"]))


def enforce_ttwa_rule(od: pd.DataFrame, assign: dict, max_iter: int = 4000,
                      verbose: bool = False) -> dict:
    """
    Пока есть невалидные ареалы — самый слабый вливается в тот,
    с которым у него сильнейшая связь (в обе стороны суммарно).

    Порядок важен: каждый раз берём НАИМЕНЕЕ валидный, иначе результат
    зависит от порядка обхода. «Наименее валидный» = наибольший дефицит
    самодостаточности относительно своего порога.

    Считается на агрегированной матрице ареал×ареал, а не на исходных
    парах. Наивная версия пересчитывала 2,4 млн строк на каждом шаге
    и не укладывалась в разумное время; здесь матрица 200×200
    обновляется сложением строки и столбца.
    """
    names = sorted(set(assign.values()))
    idx = {n: i for i, n in enumerate(names)}
    k = len(names)

    o = od.origin.map(assign).map(idx).to_numpy()
    d = od.dest.map(assign).map(idx).to_numpy()
    w = od.flow.to_numpy(dtype=float)
    ok = ~(np.isnan(o) | np.isnan(d))
    M = np.zeros((k, k))
    np.add.at(M, (o[ok].astype(int), d[ok].astype(int)), w[ok])

    alive = np.ones(k, dtype=bool)
    merged_into = {n: n for n in names}

    for it in range(max_iter):
        res = M.sum(axis=1)
        job = M.sum(axis=0)
        ins = np.diag(M)
        with np.errstate(divide="ignore", invalid="ignore"):
            sc = np.minimum(np.where(res > 0, ins / res, 0.0),
                            np.where(job > 0, ins / job, 0.0))
        thr = min_self_containment(res)
        bad = alive & ((res < MIN_SIZE) | (sc < thr))
        if not bad.any():
            break
        # Мелкие ареалы вливаются первыми: их не спасёт никакая
        # самодостаточность, а их поглощение меняет статистику соседей.
        # Поэтому им прибавляется единица — гарантированно больше
        # любого дефицита самодостаточности, который лежит в [0, 1].
        deficit = np.where(bad, thr - sc, -np.inf)
        deficit = np.where(bad & (res < MIN_SIZE),
                           1.0 + (MIN_SIZE - res) / MIN_SIZE, deficit)
        worst = int(np.argmax(deficit))

        link = M[worst].copy() + M[:, worst]
        link[worst] = -np.inf
        link[~alive] = -np.inf
        if not np.isfinite(link).any() or link.max() <= 0:
            alive[worst] = False          # связей нет, изымаем из проверки
            continue
        tgt = int(np.argmax(link))

        # Сложение строки, затем столбца даёт правильную диагональ само:
        # после первого шага M[t,t] = M[t,t] + M[w,t], после второго
        # добавляется M[t,w] + M[w,w]. Ровно четыре слагаемых, как надо.
        M[tgt, :] += M[worst, :]
        M[:, tgt] += M[:, worst]
        M[worst, :] = 0.0
        M[:, worst] = 0.0
        alive[worst] = False
        for n, cur in merged_into.items():
            if cur == names[worst]:
                merged_into[n] = names[tgt]
        if verbose and it % 25 == 0:
            print(f"  шаг {it}: ареалов {alive.sum()}, невалидных {bad.sum()}")

    return {u: merged_into[a] for u, a in assign.items()}


def enforce_by_dissolution(od: pd.DataFrame, assign: dict, max_iter: int = 500,
                           verbose: bool = False) -> dict:
    """
    Вариант правила: невалидный ареал РАСПУСКАЕТСЯ, а его единицы
    раздаются поштучно тем ареалам, с которыми у каждой сильнейшая связь.

    Зачем отдельно от enforce_ttwa_rule. Слияние целиком запускает
    лавину: как только слабый ареал вливается в Лондон, Лондон
    становится ещё притягательнее, и следующий слабый идёт туда же.
    На данных 2011 года это даёт 67 ареалов вместо официальных 167,
    причём лондонский вбирает 6,1 млн работающих — треть Англии
    и Уэльса. Роспуск с поштучной раздачей этой лавины не создаёт:
    единицы расходятся по разным соседям.

    Так устроен и настоящий алгоритм Кумбса — Бонда, на котором
    построены официальные TTWA.
    """
    assign = dict(assign)
    for it in range(max_iter):
        st = area_stats(od, assign)
        bad = st[~is_valid(st)]
        if bad.empty:
            break
        deficit = min_self_containment(bad["size"]) - bad.sc
        deficit = deficit.where(bad["size"] >= MIN_SIZE,
                                1.0 + (MIN_SIZE - bad["size"]) / MIN_SIZE)
        worst = deficit.sort_values(ascending=False).index[0]
        members = [u for u, a in assign.items() if a == worst]
        valid_areas = set(st.index[is_valid(st)]) - {worst}
        if not valid_areas:
            break

        d = od[(od.origin.isin(members)) | (od.dest.isin(members))].copy()
        d["oa"] = d.origin.map(assign)
        d["da"] = d.dest.map(assign)
        out = (d[d.origin.isin(members)].groupby(["origin", "da"]).flow.sum()
               .rename_axis(["unit", "area"]))
        inn = (d[d.dest.isin(members)].groupby(["dest", "oa"]).flow.sum()
               .rename_axis(["unit", "area"]))
        link = out.add(inn, fill_value=0.0).reset_index()
        link = link[link.area.isin(valid_areas)]
        if link.empty:
            break
        best = link.sort_values("flow", ascending=False).drop_duplicates("unit")
        moved = dict(zip(best.unit, best.area))
        if not moved:
            break
        for u in members:
            if u in moved:
                assign[u] = moved[u]
        if verbose and it % 10 == 0:
            print(f"  шаг {it}: ареалов {len(set(assign.values()))}, невалидных {len(bad)}")
    return assign
