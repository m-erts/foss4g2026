"""
Карта британских функциональных ареалов на границах MSOA 2021.

Левая панель — сырая делимитация по потокам: 235 ареалов, 26 из них
несвязные, отрезанные куски («телепорты») залиты коралловым.
Правая — после починки смежности: телепорты розданы смежным ареалам,
несвязными остались три настоящих острова (Силли, Англси, Хейлинг) —
в обобщённых границах BGC мосты не соприкасаются.

Запуск:
    python talk2/map_uk.py <msoa.geojson> <assign_raw.csv> <assign_fix.csv> <adj.parquet> <out.png>
"""
import sys
import pathlib
from collections import defaultdict

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from fua.contiguity import components  # noqa: E402

BG, CY, VI, CO = "#1A1033", "#4FE3E0", "#B57BFF", "#FF6B6B"


def load(geo, assign_csv):
    import geopandas as gpd
    g = gpd.read_file(geo)[["MSOA21CD", "geometry"]].to_crs(27700)
    a = pd.read_csv(assign_csv)
    if "unit" not in a.columns:
        a.columns = ["unit", "fua"] + list(a.columns[2:])
    return g.merge(a.dropna(subset=["fua"]), left_on="MSOA21CD",
                   right_on="unit", how="left")


def colour_areas(m, seed=7):
    """Категорийные цвета: соседние ареалы не должны сливаться, поэтому
    случайная перестановка палитры, зерно фиксировано."""
    fuas = sorted(m.fua.dropna().unique())
    rng = np.random.default_rng(seed)
    cmap = plt.get_cmap("twilight")
    cols = {f: cmap(x) for f, x in zip(fuas, rng.permutation(np.linspace(0.05, 0.95, len(fuas))))}
    return m.fua.map(cols)


def teleport_mask(m, adj):
    cut = set()
    for fua, gr in m.dropna(subset=["fua"]).groupby("fua"):
        comps = components(list(gr.MSOA21CD), adj)
        for c in comps[1:]:
            cut |= c
    return m.MSOA21CD.isin(cut)


def main(geo, raw_csv, fix_csv, adj_parquet, out):
    edges = pd.read_parquet(adj_parquet)
    adj = defaultdict(set)
    for a, b in edges.itertuples(index=False):
        adj[a].add(b)
        adj[b].add(a)
    adj = dict(adj)

    fig, axes = plt.subplots(1, 2, figsize=(13.6, 9.2), facecolor=BG)
    for ax in axes:
        ax.set_facecolor(BG)
        ax.axis("off")

    for ax, csv, ttl, sub in [
            (axes[0], raw_csv, "По потокам, без географии",
             "235 ареалов · 26 несвязных · отрезанные куски — коралловым"),
            (axes[1], fix_csv, "После починки смежности",
             "куски розданы смежным ареалам · остались 3 настоящих острова")]:
        m = load(geo, csv)
        m.plot(ax=ax, color=colour_areas(m), edgecolor=BG, linewidth=0.12)
        tp = teleport_mask(m, adj)
        if tp.any():
            m[tp].plot(ax=ax, facecolor=CO, edgecolor="#7A1F1F", linewidth=0.3)
        ax.set_title(ttl, color="white", fontsize=14.5, loc="left", pad=24)
        ax.text(0, 1.006, sub, transform=ax.transAxes, color="#9C8FB8",
                fontsize=9.5, va="bottom")
        print(f"{ttl}: телепортных MSOA {int(tp.sum())}")

    fig.suptitle("Функциональные ареалы Англии и Уэльса · перепись 2021, "
                 "потоки дом→работа без надомников",
                 color="white", fontsize=15.5, x=0.02, ha="left", y=0.985)
    fig.text(0.02, 0.045,
             "MSOA под Бристолем может отправлять 15 % выезжающих в Лондон — по потокам он «лондонский», по карте нет.",
             color=CY, fontsize=10.5)
    fig.text(0.02, 0.018,
             "ONS WU/ODWP01EW · границы MSOA 2021 BGC · EPSG:27700 · делимитация: ядра q95, слияние 0,10, порог 0,15",
             color="#6A5D85", fontsize=8.5)
    plt.tight_layout(rect=[0, 0.055, 1, 0.96])
    plt.savefig(out, dpi=150, facecolor=BG, bbox_inches="tight")
    print(f"записано {out}")


if __name__ == "__main__":
    main(*sys.argv[1:6])
