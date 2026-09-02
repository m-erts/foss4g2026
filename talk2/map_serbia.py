"""
Карта самодостаточности общин Сербии: труд против учёбы.

Запуск:
    python talk2/map_serbia.py <Op_tina.shp> <xlsx_работа> <xlsx_учёба> <out.png>
"""
import sys
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from adapters.serbia_census import read_daily_migration, add_self_containment  # noqa: E402
from adapters.serbia_geo import load_municipalities, join_census  # noqa: E402

BG, CY, VI, CO, GR = "#1A1033", "#4FE3E0", "#B57BFF", "#FF6B6B", "#3DD68C"
SEQ = LinearSegmentedColormap.from_list("seq", ["#2A1B4A", "#6B4E9E", VI, CY])
DIV = LinearSegmentedColormap.from_list("div", [CO, "#4A3A6A", GR])


def panel(ax, gdf, col, cmap, norm, title, sub):
    ax.set_facecolor(BG)
    ax.axis("off")
    gdf.plot(ax=ax, column=col, cmap=cmap, norm=norm,
             edgecolor=BG, linewidth=0.3)
    ax.set_title(title, color="white", fontsize=14, pad=4, loc="left")
    ax.text(0, 1.005, sub, transform=ax.transAxes, color="#9C8FB8",
            fontsize=10, va="bottom")
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    cb = ax.get_figure().colorbar(sm, ax=ax, fraction=0.030, pad=0.01)
    cb.ax.tick_params(colors="#CCC", labelsize=9)
    cb.outline.set_edgecolor("#444")
    return cb


def main(shp, xlsx_w, xlsx_s, out):
    w = add_self_containment(read_daily_migration(xlsx_w))
    s = add_self_containment(read_daily_migration(xlsx_s))
    g = load_municipalities(shp)
    jw = join_census(g, w).to_crs(32634)
    js = join_census(g, s).to_crs(32634)
    jw["rbsc_s"] = js.set_index("matched").rbsc.reindex(jw.matched).values
    jw["gap"] = jw.rbsc_s - jw.rbsc
    single = jw.single_settlement.astype(bool)

    fig, axes = plt.subplots(1, 2, figsize=(15.5, 7.6), facecolor=BG)

    panel(axes[0], jw[~single], "rbsc", SEQ, plt.Normalize(0, 1),
          "Самодостаточность по труду",
          "доля дневных мигрантов, остающихся в своей общине · перепись 2022")
    jw[single].plot(ax=axes[0], facecolor="#2A1B4A", edgecolor=CO,
                    linewidth=1.4, hatch="///")

    lim = float(jw.loc[~single, "gap"].abs().quantile(0.97))
    panel(axes[1], jw[~single], "gap", DIV,
          TwoSlopeNorm(vmin=-lim, vcenter=0, vmax=lim),
          "Учёба минус труд",
          "насколько учебная мобильность локальнее трудовой")
    jw[single].plot(ax=axes[1], facecolor="#2A1B4A", edgecolor=CO,
                    linewidth=1.4, hatch="///")

    fig.text(0.012, 0.062,
             "Штриховкой — 8 общин из одного населённого пункта: у них показатель структурно равен нулю.",
             color=CO, fontsize=10.5)
    fig.text(0.012, 0.034,
             "Дневни мигрант в Сербии — тот, кто покидает своё ПОСЕЛЕНИЕ. Для однопунктовой общины это всегда выезд за её пределы.",
             color="#AAA", fontsize=9.5)
    fig.text(0.012, 0.008,
             "Справа зелёное — учёба замкнутее труда. Оговорка: школьники и студенты в переписи сложены и не разделяются.",
             color="#AAA", fontsize=9.5)
    fig.text(0.988, 0.008,
             "РЗС, Попис 2022 · границе ГеоСрбија, без Косова и Метохије · EPSG:32634",
             color="#6A5D85", fontsize=8.5, ha="right")

    plt.tight_layout(rect=[0, 0.085, 1, 0.985])
    plt.savefig(out, dpi=155, facecolor=BG, bbox_inches="tight")
    print(f"записано {out}")
    print(f"  общин {len(jw)}, медиана труд {jw.loc[~single,'rbsc'].median():.3f} "
          f"учёба {jw.loc[~single,'rbsc_s'].median():.3f} "
          f"разрыв {jw.loc[~single,'gap'].mean():+.3f}")


if __name__ == "__main__":
    main(*sys.argv[1:5])
