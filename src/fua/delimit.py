"""
Делимитация функциональных городских ареалов из OD-матрицы.

Логика OECD, портирована из ноутбуков (build_fuas_multi, add_teleportations):
  1. ядра — единицы, притягивающие много поездок извне
  2. пригород присоединяется к ядру, если отправляет туда не меньше
     commute_thr своих выезжающих
  3. итерация до стабилизации: присоединившиеся расширяют ареал
  4. смежность — опциональная. Без неё получаются «телепорты»:
     единицы, связанные потоком, но не граничащие. В коде OECD они
     добавляются отдельным шагом, здесь — параметром require_contiguity

Требует ТОЛЬКО матрицу origin x destination. Именно поэтому работает
для Британии и не работает для Сербии и Японии: там публикуют
категории дальности, а не пары.
"""

from __future__ import annotations

import pandas as pd

__all__ = ["prepare_od", "unit_stats", "find_cores", "merge_cores",
           "build_fua", "fua_summary"]


def prepare_od(df: pd.DataFrame, o_col: str, d_col: str, w_col: str) -> pd.DataFrame:
    """Приводит любую OD-таблицу к трём колонкам: origin, dest, flow."""
    od = (df[[o_col, d_col, w_col]]
          .rename(columns={o_col: "origin", d_col: "dest", w_col: "flow"}))
    od["origin"] = od["origin"].astype(str).str.strip()
    od["dest"] = od["dest"].astype(str).str.strip()
    od["flow"] = pd.to_numeric(od["flow"], errors="coerce")
    od = od.dropna(subset=["flow"])
    od = od[od["flow"] > 0]
    return od.groupby(["origin", "dest"], as_index=False)["flow"].sum()


def unit_stats(od: pd.DataFrame) -> pd.DataFrame:
    """Для каждой единицы: выезды, внутренние, въезды извне, самодостаточность."""
    internal = od[od.origin == od.dest].set_index("origin")["flow"]
    out_all = od.groupby("origin")["flow"].sum()
    in_all = od.groupby("dest")["flow"].sum()
    ext_out = out_all.sub(internal, fill_value=0)
    ext_in = in_all.sub(internal, fill_value=0)

    s = pd.DataFrame({
        "internal": internal,
        "out_total": out_all,
        "in_total": in_all,
        "out_external": ext_out,
        "in_external": ext_in,
    }).fillna(0.0)
    s["self_containment"] = (s.internal / s.out_total).where(s.out_total > 0)
    # насколько единица притягивает больше, чем отпускает
    s["net_attraction"] = s.in_external - s.out_external
    s["job_ratio"] = (s.in_total / s.out_total).where(s.out_total > 0)
    return s.sort_values("in_external", ascending=False)


def find_cores(stats: pd.DataFrame, inflow_quantile: float = 0.85,
               min_job_ratio: float = 1.0) -> list[str]:
    """
    Ядро = притягивает много поездок извне И рабочих мест больше,
    чем работающих жителей (job_ratio >= 1).

    inflow_quantile отсекает по абсолютному притоку, job_ratio —
    по роли: спальный район может иметь большой приток, но отдавать
    ещё больше.
    """
    thr = stats.in_external.quantile(inflow_quantile)
    cores = stats[(stats.in_external >= thr) & (stats.job_ratio >= min_job_ratio)]
    return list(cores.index)


def merge_cores(od: pd.DataFrame, cores: list[str],
                merge_thr: float = 0.10) -> dict[str, str]:
    """
    Сливает ядра, сильно связанные между собой.

    Зачем: в полицентричной агломерации каждый деловой район проходит
    критерий ядра по отдельности. Без слияния Лондон рассыпается на
    Вестминстер, Камден, Сити и далее по списку, хотя это один
    трудовой рынок. В коде OECD ту же роль играет шаг с телепортами.

    Правило: два ядра сливаются, если хотя бы у одного из них
    доля выезжающих в другое >= merge_thr. Дальше — связные компоненты.
    """
    cs = set(cores)
    ext = od[(od.origin != od.dest) & od.origin.isin(cs) & od.dest.isin(cs)]
    out_ext = od[od.origin != od.dest].groupby("origin")["flow"].sum()

    parent = {c: c for c in cores}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for r in ext.itertuples():
        denom = out_ext.get(r.origin, 0)
        if denom > 0 and r.flow / denom >= merge_thr:
            union(r.origin, r.dest)

    # имя группы — ядро с наибольшим внешним притоком
    groups: dict[str, list[str]] = {}
    for c in cores:
        groups.setdefault(find(c), []).append(c)
    inflow = od[od.origin != od.dest].groupby("dest")["flow"].sum()
    out = {}
    for members in groups.values():
        head = max(members, key=lambda m: inflow.get(m, 0))
        for m in members:
            out[m] = head
    return out


def build_fua(od: pd.DataFrame, cores: list[str], commute_thr: float = 0.15,
              max_iter: int = 20) -> pd.DataFrame:
    """
    Итеративно присоединяет единицы к ядрам.

    На каждом шаге для каждой неприсоединённой единицы считается доля
    её выезжающих, попадающих в каждый уже сформированный ареал.
    Если максимальная доля >= commute_thr, единица уходит в этот ареал.
    Повторяется, пока есть изменения.
    """
    merged = merge_cores(od, cores) if cores else {}
    assign = {c: merged.get(c, c) for c in cores}
    ext = od[od.origin != od.dest]
    out_ext = ext.groupby("origin")["flow"].sum()

    for _ in range(max_iter):
        e = ext.copy()
        e["fua"] = e["dest"].map(assign)
        e = e.dropna(subset=["fua"])
        if e.empty:
            break
        share = (e.groupby(["origin", "fua"])["flow"].sum()
                   .div(out_ext, level="origin").reset_index(name="share"))
        share = share[~share.origin.isin(assign)]
        if share.empty:
            break
        best = share.sort_values("share", ascending=False).drop_duplicates("origin")
        joined = best[best.share >= commute_thr]
        if joined.empty:
            break
        assign.update(dict(zip(joined.origin, joined.fua)))

    units = sorted(set(od.origin) | set(od.dest))
    return pd.DataFrame({
        "unit": units,
        "fua": [assign.get(u) for u in units],
        "is_core": [u in cores for u in units],
    })


def fua_summary(od: pd.DataFrame, assignment: pd.DataFrame) -> pd.DataFrame:
    """Самодостаточность каждого построенного ареала."""
    m = dict(zip(assignment.unit, assignment.fua))
    d = od.copy()
    d["o_fua"] = d.origin.map(m)
    d["d_fua"] = d.dest.map(m)
    d = d.dropna(subset=["o_fua"])
    dep = d.groupby("o_fua")["flow"].sum()
    inside = d[d.o_fua == d.d_fua].groupby("o_fua")["flow"].sum()
    n = assignment.dropna(subset=["fua"]).groupby("fua").size()
    out = pd.DataFrame({"units": n, "departures": dep,
                        "internal": inside}).fillna(0.0)
    out["self_containment"] = out.internal / out.departures
    return out.sort_values("departures", ascending=False)
