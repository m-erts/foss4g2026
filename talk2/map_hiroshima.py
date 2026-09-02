"""
Карта присутствия по мешу 1 км: Хиросима, день против ночи.

Что показывает: единственное измерение, которое открытые японские
данные дают, а переписи — нет. День и ночь в одном и том же месте.

Соотношение день/ночь — это, по сути, дневной прирост населения
на ячейку. Больше 1 — место, куда приезжают; меньше 1 — откуда уезжают.

Запуск:
    python talk2/map_hiroshima.py <папка mdp> <attribute.csv.zip> <out.png>
"""
import io
import sys
import zipfile
import glob
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, LogNorm, TwoSlopeNorm

# Noto CJK JP содержит и кириллицу, и кандзи — ставим его основным.
# Список с DejaVu впереди НЕ работает: matplotlib не всегда падает
# на второй шрифт поглифно, и японские подписи выходят квадратами.
matplotlib.rcParams["font.family"] = ["Noto Serif CJK JP", "DejaVu Sans"]

BG, CY, VI, CO, GR = "#1A1033", "#4FE3E0", "#B57BFF", "#FF6B6B", "#3DD68C"
SEQ = LinearSegmentedColormap.from_list("seq", ["#150D2A", "#4A3080", VI, CY, "#EAFBFF"])
# Нейтральный цвет ОБЯЗАН стоять ровно посередине списка, иначе
# TwoSlopeNorm поставит центр (отношение ×1) не туда, и ячейки без
# дневного прироста покрасятся как «прирост». На первой версии карты
# из-за этого вся агломерация вышла красной.
DIV = LinearSegmentedColormap.from_list(
    "div", ["#2A6FE0", "#3D5A9E", "#241A44", CO, "#FFD166"])

YEAR, MONTH = 2019, 10          # до ковида
DAY_WEEKDAY = 1                 # 平日
TZ_DAY, TZ_NIGHT = 0, 1         # 昼 / 深夜


def read_mdp(root: str) -> pd.DataFrame:
    files = sorted(glob.glob(os.path.join(root, "**", "monthly_mdp_mesh1km.csv.zip"),
                             recursive=True))
    frames = []
    for z in files:
        with zipfile.ZipFile(z) as zf:
            n = next(x for x in zf.namelist() if x.endswith(".csv"))
            frames.append(pd.read_csv(io.BytesIO(zf.read(n))))
    return pd.concat(frames, ignore_index=True)


def read_attribute(path: str) -> pd.DataFrame:
    with zipfile.ZipFile(path) as zf:
        n = next(x for x in zf.namelist() if x.endswith(".csv"))
        return pd.read_csv(io.BytesIO(zf.read(n)))


def main(mdp_root, attr_zip, out):
    d = read_mdp(mdp_root)
    a = read_attribute(attr_zip)
    d = d[(d.year == YEAR) & (d.month == MONTH) & (d.dayflag == DAY_WEEKDAY)]
    p = (d[d.timezone.isin([TZ_DAY, TZ_NIGHT])]
         .pivot_table(index="mesh1kmid", columns="timezone",
                      values="population", aggfunc="sum"))
    p.columns = ["day", "night"]
    p = p.dropna()
    m = p.join(a.set_index("mesh1kmid")[["lon_center", "lat_center"]], how="inner")
    # порог: ниже 10 человек данные не публикуются, отношения там шумные
    m = m[(m.day >= 10) & (m.night >= 10)]
    m["ratio"] = m.day / m.night
    print(f"ячеек {len(m):,}  дневное присутствие {m.day.sum():,.0f}  "
          f"ночное {m.night.sum():,.0f}")

    # окно на агломерацию Хиросимы
    W = (132.15, 132.85, 34.20, 34.62)
    v = m[(m.lon_center.between(W[0], W[1])) & (m.lat_center.between(W[2], W[3]))]
    print(f"в окне {len(v):,} ячеек")

    fig = plt.figure(figsize=(17.0, 8.6), facecolor=BG)
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.45], wspace=0.10,
                          left=0.015, right=0.955, top=0.90, bottom=0.115)
    ax0, ax1 = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
    for ax in (ax0, ax1):
        ax.set_facecolor(BG)
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_color("#3A2D5A")
        ax.set_aspect(1 / np.cos(np.radians(34.4)))

    sz0, sz1 = 26, 40
    sc = ax0.scatter(v.lon_center, v.lat_center, c=v.night, cmap=SEQ,
                     norm=LogNorm(vmin=10, vmax=float(v.night.max())),
                     s=sz0, marker="s", linewidths=0)
    ax0.set_title("Где спят  深夜", color="white", fontsize=15, loc="left", pad=9)
    cb = fig.colorbar(sc, ax=ax0, fraction=0.035, pad=0.012)
    cb.set_label("человек на ячейку 1 км²", color="#BBB", fontsize=9)
    cb.ax.tick_params(colors="#CCC", labelsize=9); cb.outline.set_edgecolor("#444")

    lim = float(np.nanpercentile(np.abs(np.log2(v.ratio)), 97))
    sc2 = ax1.scatter(v.lon_center, v.lat_center, c=np.log2(v.ratio), cmap=DIV,
                      norm=TwoSlopeNorm(vmin=-lim, vcenter=0, vmax=lim),
                      s=sz1, marker="s", linewidths=0)
    ax1.set_title("Куда едут днём  昼 / 深夜", color="white", fontsize=15,
                  loc="left", pad=9)
    cb2 = fig.colorbar(sc2, ax=ax1, fraction=0.035, pad=0.012,
                       ticks=[-lim, -1, 0, 1, lim])
    cb2.ax.set_yticklabels([f"×{2**-lim:.2f}", "×0,5", "×1", "×2", f"×{2**lim:.1f}"])
    cb2.ax.tick_params(colors="#CCC", labelsize=9); cb2.outline.set_edgecolor("#444")

    fig.suptitle("Присутствие населения, агломерация Хиросимы · будний день, октябрь 2019",
                 color="white", fontsize=16.5, x=0.015, ha="left", y=0.972)
    fig.text(0.015, 0.070,
             "Жёлтым — ячейки, где днём людей вдвое с лишним больше, чем ночью: рабочие места. Синим — спальные районы.",
             color="#BBB", fontsize=10)
    fig.text(0.015, 0.040,
             "Этого измерения нет ни в британской, ни в сербской переписи. Зато здесь нет пар «откуда → куда», которые есть у британцев.",
             color=CY, fontsize=10)
    fig.text(0.015, 0.010,
             "MLIT 全国の人流オープンデータ · меш 1 км JIS X 0410 · значения ниже 10 человек не публикуются",
             color="#6A5D85", fontsize=8.5)
    plt.savefig(out, dpi=150, facecolor=BG)
    print(f"записано {out}")
    top = v.nlargest(5, "ratio")[["lon_center", "lat_center", "day", "night", "ratio"]]
    print("\nсамый сильный дневной прирост:")
    print(top.to_string(index=False))


if __name__ == "__main__":
    main(*sys.argv[1:4])
