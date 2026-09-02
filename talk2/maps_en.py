"""
All talk-2 map assets, English labels, 16:9-friendly, dark theme.

Generates into <outdir>:
    uk_areas.png        UK functional areas, raw vs contiguity-fixed
    rs_selfcont.png     Serbia municipal self-containment, work vs education gap
    jp_daynight.png     Hiroshima presence, night + day/night ratio
    jp_signatures.png   Hiroshima temporal signatures (rule-based)

Run:
    python talk2/maps_en.py <outdir>
Paths to inputs are set below (sandbox /tmp layout).
"""
import io
import sys
import glob
import zipfile
import pathlib
from collections import defaultdict

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, LogNorm, TwoSlopeNorm
from matplotlib.patches import Patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from adapters.serbia_census import read_daily_migration, add_self_containment  # noqa: E402
from adapters.serbia_geo import load_municipalities, join_census  # noqa: E402
from fua.contiguity import components  # noqa: E402

matplotlib.rcParams["font.family"] = ["Noto Serif CJK JP", "DejaVu Sans"]

BG, CY, VI, CO, GR, YE = "#1A1033", "#4FE3E0", "#B57BFF", "#FF6B6B", "#3DD68C", "#FFD166"
SEQ = LinearSegmentedColormap.from_list("seq", ["#150D2A", "#4A3080", VI, CY, "#EAFBFF"])
SEQ2 = LinearSegmentedColormap.from_list("seq2", ["#2A1B4A", "#6B4E9E", VI, CY])
DIV = LinearSegmentedColormap.from_list("div", ["#2A6FE0", "#3D5A9E", "#241A44", CO, YE])
DIVG = LinearSegmentedColormap.from_list("divg", ["#2A6FE0", "#3D4A7E", "#241A44", "#B8743D", YE])

U = "/sessions/practical-upbeat-brown/mnt/uploads/"
RS_SHP = "/tmp/rs/Op_tina.shp"
RS_W = U + "dnevne_migracije_aktivnog_stanovnistva_koje_obavlja_zanimanje_po_polu_i_tipu_naselja.xlsx"
RS_S = U + "dnevne_migracije_učenika_i_studenata_po_polu_i_tipu_naselja.xlsx"
UK_GEO = U + "Middle_layer_Super_Output_Areas_December_2021_Boundaries_EW_BGC_V3_-4477917303172606123.geojson"
UK_RAW, UK_FIX = "/tmp/uk21_assign_fixed.csv", "/tmp/uk21_contig.csv"
UK_ADJ = "/tmp/msoa_adj.parquet"
JP_MDP = "/tmp/jp/mdp"
JP_ATTR = "/tmp/jp/attribute/attribute/attribute_mesh1km_2019.csv.zip"
JP_SIG = "/tmp/jp_signatures.parquet"


def style(ax):
    ax.set_facecolor(BG)
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_color("#3A2D5A")


def cbar(fig, ax, sm, label):
    cb = fig.colorbar(sm, ax=ax, fraction=0.033, pad=0.012)
    cb.set_label(label, color="#BBB", fontsize=9)
    cb.ax.tick_params(colors="#CCC", labelsize=9)
    cb.outline.set_edgecolor("#444")
    return cb


def footer(fig, main, src):
    fig.text(0.015, 0.040, main, color=CY, fontsize=10.5)
    fig.text(0.015, 0.012, src, color="#6A5D85", fontsize=8.5)


# ---------------------------------------------------------------- UK
def uk_map(outdir):
    import geopandas as gpd
    edges = pd.read_parquet(UK_ADJ)
    adj = defaultdict(set)
    for a, b in edges.itertuples(index=False):
        adj[a].add(b); adj[b].add(a)
    adj = dict(adj)
    g = gpd.read_file(UK_GEO)[["MSOA21CD", "geometry"]].to_crs(27700)

    fig, axes = plt.subplots(1, 2, figsize=(12.8, 7.2), facecolor=BG)
    for ax, csv, ttl, sub in [
            (axes[0], UK_RAW, "Flows only, no geography",
             "235 areas · 26 non-contiguous · cut-off fragments in coral"),
            (axes[1], UK_FIX, "After contiguity repair",
             "fragments handed to adjacent areas · 3 true islands remain")]:
        a = pd.read_csv(csv)
        if "unit" not in a.columns:
            a.columns = ["unit", "fua"] + list(a.columns[2:])
        m = g.merge(a.dropna(subset=["fua"]), left_on="MSOA21CD",
                    right_on="unit", how="left")
        fuas = sorted(m.fua.dropna().unique())
        rng = np.random.default_rng(7)
        cmap = plt.get_cmap("twilight")
        cols = {f: cmap(x) for f, x in
                zip(fuas, rng.permutation(np.linspace(0.05, 0.95, len(fuas))))}
        style(ax); ax.axis("off")
        m.plot(ax=ax, color=m.fua.map(cols), edgecolor=BG, linewidth=0.1)
        cut = set()
        for fua, gr in m.dropna(subset=["fua"]).groupby("fua"):
            for c in components(list(gr.MSOA21CD), adj)[1:]:
                cut |= c
        tp = m.MSOA21CD.isin(cut)
        if tp.any():
            m[tp].plot(ax=ax, facecolor=CO, edgecolor="#7A1F1F", linewidth=0.3)
        ax.set_title(ttl, color="white", fontsize=14.5, loc="left", pad=22)
        ax.text(0, 1.005, sub, transform=ax.transAxes, color="#9C8FB8",
                fontsize=9.5, va="bottom")
    fig.suptitle("Functional areas of England & Wales · Census 2021 "
                 "home→work flows, home-workers excluded",
                 color="white", fontsize=15, x=0.02, ha="left", y=0.985)
    footer(fig,
           "An MSOA near Bristol can send 15 % of its commuters to London — "
           "\"London\" by flows, not on the map.",
           "ONS ODWP01EW · MSOA 2021 BGC boundaries · EPSG:27700 · "
           "cores q95, core merge 0.10, attach 0.15")
    plt.tight_layout(rect=[0, 0.05, 1, 0.955])
    plt.savefig(f"{outdir}/uk_areas.png", dpi=150, facecolor=BG,
                bbox_inches="tight")
    plt.close(fig)
    print("uk_areas.png")


# ------------------------------------------------------------ Serbia
def rs_map(outdir):
    w = add_self_containment(read_daily_migration(RS_W))
    s = add_self_containment(read_daily_migration(RS_S))
    g = load_municipalities(RS_SHP)
    jw = join_census(g, w).to_crs(32634)
    js = join_census(g, s).to_crs(32634)
    jw["rbsc_s"] = js.set_index("matched").rbsc.reindex(jw.matched).values
    jw["gap"] = jw.rbsc_s - jw.rbsc
    single = jw.single_settlement.astype(bool)

    fig, axes = plt.subplots(1, 2, figsize=(12.8, 7.2), facecolor=BG)
    for ax in axes:
        style(ax); ax.axis("off")
    jw[~single].plot(ax=axes[0], column="rbsc", cmap=SEQ2,
                     vmin=0, vmax=1, edgecolor=BG, linewidth=0.3)
    jw[single].plot(ax=axes[0], facecolor="#2A1B4A", edgecolor=CO,
                    linewidth=1.6, hatch="///")
    axes[0].set_title("Work self-containment", color="white",
                      fontsize=14.5, loc="left", pad=22)
    axes[0].text(0, 1.005, "share of daily migrants staying in their "
                 "municipality · Census 2022", transform=axes[0].transAxes,
                 color="#9C8FB8", fontsize=9.5, va="bottom")
    cbar(fig, axes[0], plt.cm.ScalarMappable(cmap=SEQ2,
         norm=plt.Normalize(0, 1)), "share staying in own municipality")

    lim = float(jw.loc[~single, "gap"].abs().quantile(0.97))
    nrm = TwoSlopeNorm(vmin=-lim, vcenter=0, vmax=lim)
    jw[~single].plot(ax=axes[1], column="gap", cmap=DIVG, norm=nrm,
                     edgecolor=BG, linewidth=0.3)
    jw[single].plot(ax=axes[1], facecolor="#2A1B4A", edgecolor=CO,
                    linewidth=1.6, hatch="///")
    axes[1].set_title("Education minus work", color="white",
                      fontsize=14.5, loc="left", pad=22)
    axes[1].text(0, 1.005, "yellow = education commuting is MORE local than work; "
                 "blue = work more local", transform=axes[1].transAxes,
                 color="#9C8FB8", fontsize=9.5, va="bottom")
    cbar(fig, axes[1], plt.cm.ScalarMappable(cmap=DIVG, norm=nrm), "education − work, per municipality")

    footer(fig,
           "Hatched: 8 single-settlement municipalities where the metric is "
           "structurally zero — a definition artefact, not a finding.",
           "SORS Popis 2022 · boundaries GeoSrbija · Census 2022 does not cover Kosovo* (*UNSCR 1244) · "
           "EPSG:32634 · pupils and students are published as one number")
    plt.tight_layout(rect=[0, 0.05, 1, 0.97])
    plt.savefig(f"{outdir}/rs_selfcont.png", dpi=150, facecolor=BG,
                bbox_inches="tight")
    plt.close(fig)
    print("rs_selfcont.png")


# ------------------------------------------------------------- Japan
def _jp_base():
    frames = []
    for z in sorted(glob.glob(f"{JP_MDP}/**/monthly_mdp_mesh1km.csv.zip",
                              recursive=True)):
        with zipfile.ZipFile(z) as zf:
            n = next(x for x in zf.namelist() if x.endswith(".csv"))
            frames.append(pd.read_csv(io.BytesIO(zf.read(n))))
    d = pd.concat(frames, ignore_index=True)
    with zipfile.ZipFile(JP_ATTR) as zf:
        n = next(x for x in zf.namelist() if x.endswith(".csv"))
        a = pd.read_csv(io.BytesIO(zf.read(n)))
    return d, a.set_index("mesh1kmid")[["lon_center", "lat_center"]]


def jp_daynight(outdir):
    d, coords = _jp_base()
    d = d[(d.year == 2019) & (d.month == 10) & (d.dayflag == 1)]
    p = (d[d.timezone.isin([0, 1])]
         .pivot_table(index="mesh1kmid", columns="timezone",
                      values="population", aggfunc="sum"))
    p.columns = ["day", "night"]
    m = p.dropna().join(coords, how="inner")
    m = m[(m.day >= 10) & (m.night >= 10)]
    m["ratio"] = m.day / m.night
    W = (132.15, 132.85, 34.20, 34.62)
    v = m[m.lon_center.between(W[0], W[1]) & m.lat_center.between(W[2], W[3])]

    fig = plt.figure(figsize=(12.8, 7.2), facecolor=BG)
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.45], wspace=0.10,
                          left=0.015, right=0.95, top=0.87, bottom=0.11)
    ax0, ax1 = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
    for ax in (ax0, ax1):
        style(ax)
        ax.set_aspect(1 / np.cos(np.radians(34.4)))
    sc = ax0.scatter(v.lon_center, v.lat_center, c=v.night, cmap=SEQ,
                     norm=LogNorm(10, float(v.night.max())), s=20,
                     marker="s", linewidths=0)
    ax0.set_title("Where people sleep  深夜", color="white", fontsize=14,
                  loc="left", pad=8)
    cbar(fig, ax0, sc, "people per 1 km² cell")
    lim = float(np.nanpercentile(np.abs(np.log2(v.ratio)), 97))
    sc2 = ax1.scatter(v.lon_center, v.lat_center, c=np.log2(v.ratio),
                      cmap=DIV,
                      norm=TwoSlopeNorm(vmin=-lim, vcenter=0.0, vmax=lim), s=30,
                      marker="s", linewidths=0)
    ax1.set_title("Where they go by day  昼 / 深夜", color="white",
                  fontsize=14, loc="left", pad=8)
    cb = fig.colorbar(sc2, ax=ax1, fraction=0.04, pad=0.012,
                      ticks=[-lim, -1, 0, 1, lim])
    cb.ax.set_yticklabels([f"×{2**-lim:.2f}", "×0.5", "×1", "×2",
                           f"×{2**lim:.1f}"])
    cb.ax.tick_params(colors="#CCC", labelsize=9)
    cb.outline.set_edgecolor("#444")
    fig.suptitle("Population presence, Hiroshima agglomeration · weekday, "
                 "October 2019", color="white", fontsize=15, x=0.015,
                 ha="left", y=0.96)
    ax1.annotate("Naka-ku 中区", xy=(132.455, 34.390), color="white",
                 fontsize=11, ha="center",
                 xytext=(132.55, 34.435),
                 arrowprops=dict(arrowstyle="-", color="#AAA", lw=0.8))
    footer(fig,
           "Yellow: 2×+ more people by day than by night — job clusters. "
           "Blue: dormitory areas. Censuses cannot see this axis at all.",
           "MLIT 全国の人流オープンデータ · source: Agoop app-GPS panel, 換算人口 expansion · 1 km mesh JIS X 0410 "
           "· values under 10 suppressed · volumes normalised, compare "
           "composition only")
    plt.savefig(f"{outdir}/jp_daynight.png", dpi=150, facecolor=BG)
    plt.close(fig)
    print("jp_daynight.png")


def jp_signatures(outdir):
    """Двухпанельный: слева континуум в осях порогов, справа карта."""
    sig = pd.read_parquet(JP_SIG)
    _, coords = _jp_base()
    m = sig.join(coords, how="inner")
    m = m[m.volume >= 100]
    W = (132.28, 132.62, 34.30, 34.48)
    v = m[m.lon_center.between(W[0], W[1]) & m.lat_center.between(W[2], W[3])]
    COLS = {"mixed": "#463868", "residential": VI, "leisure": CY, "office": YE}
    T = 0.585

    fig = plt.figure(figsize=(12.8, 6.4), facecolor=BG)
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.15], wspace=0.14,
                          left=0.055, right=0.985, top=0.90, bottom=0.14)
    ax0, ax1 = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])

    # --- скаттер: континуум и произвол порогов видны глазами
    ax0.set_facecolor(BG)
    for spn in ax0.spines.values():
        spn.set_color("#3A2D5A")
    for k, c in COLS.items():
        sub = m[m.sig == k]
        ax0.scatter(sub.work, sub.leis, s=7, c=c, alpha=0.6, linewidths=0)
    for x in (-T, T):
        ax0.axvline(x, color="#888", lw=0.9, ls="--")
    ax0.axhline(T, color="#888", lw=0.9, ls="--")
    ax0.set_xlim(-3.2, 3.2); ax0.set_ylim(-2.4, 2.9)
    ax0.tick_params(colors="#9C8FB8", labelsize=9)
    ax0.set_xlabel("log2 (weekday day / night)", color="#BBB", fontsize=10)
    ax0.set_ylabel("log2 (holiday day / weekday day)", color="#BBB", fontsize=10)
    ax0.text(2.0, -1.9, "office-like", color=YE, fontsize=11, ha="center")
    ax0.text(-2.2, -1.9, "dormitory", color=VI, fontsize=11, ha="center")
    ax0.text(0, 2.55, "weekend-leisure", color=CY, fontsize=11, ha="center")
    ax0.text(0, -0.15, "one dense mode", color="#CCC", fontsize=10,
             ha="center", style="italic")
    ax0.set_title("The continuum — cuts are declared, not discovered",
                  color="white", fontsize=13, loc="left", pad=8)

    # --- карта
    ax1.set_facecolor(BG); ax1.set_xticks([]); ax1.set_yticks([])
    for spn in ax1.spines.values():
        spn.set_color("#3A2D5A")
    ax1.set_aspect(1 / np.cos(np.radians(34.4)))
    for k, c in COLS.items():
        sub = v[v.sig == k]
        ax1.scatter(sub.lon_center, sub.lat_center, c=c, s=72, marker="s",
                    linewidths=0, alpha=0.55 if k == "mixed" else 1.0)
    ax1.set_title("Hiroshima city, cells >= 100 people", color="white",
                  fontsize=13, loc="left", pad=8)
    handles = [Patch(facecolor=c, label={"office": "Office / industrial",
               "residential": "Residential", "leisure": "Leisure / retail",
               "mixed": "Mixed"}[k]) for k, c in COLS.items()]
    ax1.legend(handles=handles, loc="lower right", fontsize=9,
               framealpha=0.9, facecolor="#241A44", edgecolor="#3A2D5A",
               labelcolor="white")

    fig.suptitle("Temporal signatures from the open app-GPS panel · 2019 mean",
                 color="white", fontsize=15, x=0.015, ha="left", y=0.975)
    fig.text(0.015, 0.055,
             "HDBSCAN at honest settings: 100 % noise — no second mode. "
             "Hopkins 0.93: density is concentrated, but not separated.",
             color=CY, fontsize=10.5)
    fig.text(0.015, 0.022,
             "MLIT people-flow (Agoop app-GPS panel) · 1.5x thresholds "
             "(dashed) · k-means would happily cut 4 classes anyway",
             color="#6A5D85", fontsize=8.5)
    plt.savefig(f"{outdir}/jp_signatures.png", dpi=150, facecolor=BG)
    plt.close(fig)
    print("jp_signatures.png")


if __name__ == "__main__":
    out = sys.argv[1]
    uk_map(out)
    rs_map(out)
    jp_daynight(out)
    jp_signatures(out)
