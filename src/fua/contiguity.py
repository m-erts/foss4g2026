"""
Смежность ареалов: диагностика телепортов и их починка.

«Телепорт» — кусок ареала, не соприкасающийся с главной компонентой.
Возникает, потому что делимитация идёт только по потокам: MSOA под
Бристолем может отправлять 15 % выезжающих в Лондон и приклеиться
к нему через полстраны.

На данных 2021 года телепортов немного, но они есть: 26 ареалов
из 235 несвязны, лондонский состоит из пяти кусков.

Починка: в каждом ареале оставляем главную компоненту (ту, где ядро;
если ядра нет — крупнейшую по числу единиц), а каждую отрезанную
компоненту отдаём тому СМЕЖНОМУ с ней ареалу, с которым у неё
сильнейший суммарный поток в обе стороны. Если сосед один — выбора
нет; если отрезанный кусок не граничит ни с одним ареалом (остров),
он остаётся как есть и попадает в отчёт.

Смежность — queen (общая точка достаточна), из полигонов BGC.
"""

from __future__ import annotations

from collections import defaultdict

import pandas as pd

__all__ = ["build_adjacency", "components", "fragmentation_report",
           "fix_teleports"]


def build_adjacency(gdf, id_col: str) -> dict[str, set]:
    """Queen-смежность через sjoin полигонов с собой."""
    import geopandas as gpd
    sj = gpd.sjoin(gdf[[id_col, "geometry"]], gdf[[id_col, "geometry"]],
                   predicate="intersects")
    adj: dict[str, set] = defaultdict(set)
    for a, b in zip(sj[f"{id_col}_left"], sj[f"{id_col}_right"]):
        if a != b:
            adj[a].add(b)
            adj[b].add(a)
    return dict(adj)


def components(units: list[str], adj: dict[str, set]) -> list[set]:
    """Компоненты связности внутри списка единиц."""
    us, seen, out = set(units), set(), []
    for u in units:
        if u in seen:
            continue
        comp, stack = set(), [u]
        while stack:
            x = stack.pop()
            if x in comp:
                continue
            comp.add(x)
            stack.extend((adj.get(x, set()) & us) - comp)
        seen |= comp
        out.append(comp)
    return sorted(out, key=len, reverse=True)


def fragmentation_report(assign: dict, adj: dict[str, set]) -> pd.DataFrame:
    rows = []
    groups = defaultdict(list)
    for u, a in assign.items():
        groups[a].append(u)
    for a, units in groups.items():
        comps = components(units, adj)
        rows.append({"fua": a, "n_units": len(units),
                     "n_components": len(comps),
                     "main_size": len(comps[0]),
                     "cut_units": len(units) - len(comps[0])})
    return (pd.DataFrame(rows).sort_values("n_components", ascending=False)
            .reset_index(drop=True))


def fix_teleports(od: pd.DataFrame, assign: dict, adj: dict[str, set],
                  cores: set | None = None, max_rounds: int = 10,
                  verbose: bool = False) -> dict:
    """
    Итеративно: отрезанные компоненты уходят сильнейшему смежному ареалу.

    Итерации нужны, потому что передача куска может разорвать
    или объединить что-то ещё. Обычно сходится за 2–3 круга.
    """
    assign = dict(assign)
    cores = cores or set()

    # быстрые связи единица→суммарный поток с каждой единицей
    flow_uu = defaultdict(float)
    for r in od.itertuples(index=False):
        if r.origin != r.dest:
            flow_uu[(r.origin, r.dest)] += r.flow

    def link_to_area(comp: set, area: str, groups) -> float:
        tgt = groups[area]
        s = 0.0
        for u in comp:
            for v in adj.get(u, set()):
                if v in tgt:
                    s += flow_uu.get((u, v), 0.0) + flow_uu.get((v, u), 0.0)
        return s

    for rnd in range(max_rounds):
        groups = defaultdict(set)
        for u, a in assign.items():
            groups[a].add(u)
        moved = 0
        for a, units in list(groups.items()):
            comps = components(list(units), adj)
            if len(comps) == 1:
                continue
            # главная компонента: с ядром, иначе крупнейшая
            main_i = 0
            for i, c in enumerate(comps):
                if c & cores:
                    main_i = i
                    break
            for i, comp in enumerate(comps):
                if i == main_i:
                    continue
                # смежные ареалы этой компоненты
                nb_areas = set()
                for u in comp:
                    for v in adj.get(u, set()):
                        av = assign.get(v)
                        if av and av != a:
                            nb_areas.add(av)
                if not nb_areas:
                    continue          # остров — оставляем
                best = max(nb_areas, key=lambda x: link_to_area(comp, x, groups))
                for u in comp:
                    assign[u] = best
                moved += len(comp)
        if verbose:
            print(f"  круг {rnd}: переприсвоено {moved}")
        if moved == 0:
            break
    return assign
