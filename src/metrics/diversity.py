"""
Метрики функционального разнообразия ("ДНК района").

Взяты из экологии сообществ. Ключевой момент, которого не хватало
в зимней версии: richness механически растёт с числом объектов
в ячейке, поэтому сравнивать по нему места с разной полнотой данных
нельзя. Числа Хилла устойчивее; плюс порог min_count отсекает
ячейки, где любая метрика — шум.

Chao, A. & Jost, L. (2012) Coverage-based rarefaction and extrapolation.
Ecology 93(12): 2533-2547.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = [
    "richness", "shannon", "evenness", "gini_simpson",
    "hill_q1", "hill_q2", "top_cat_share", "sample_coverage",
    "compute_all",
]


def _proportions(counts: np.ndarray) -> np.ndarray:
    """Доли ненулевых категорий. Пустой вход -> пустой массив."""
    counts = np.asarray(counts, dtype=float)
    counts = counts[counts > 0]
    total = counts.sum()
    if total <= 0:
        return np.empty(0)
    return counts / total


def richness(counts) -> float:
    """Число представленных категорий. ОСТОРОЖНО: зависит от размера выборки."""
    c = np.asarray(counts, dtype=float)
    return float((c > 0).sum())


def shannon(counts) -> float:
    """Энтропия Шеннона. 0 при монофункциональности."""
    p = _proportions(counts)
    if p.size == 0:
        return np.nan
    return float(-(p * np.log(p)).sum())


def evenness(counts) -> float:
    """Выровненность Пиелу: H / ln(S). Отделяет сбалансированность от богатства."""
    p = _proportions(counts)
    if p.size <= 1:
        return np.nan  # для одной категории выровненность не определена
    return float(shannon(counts) / np.log(p.size))


def gini_simpson(counts) -> float:
    """Вероятность, что два случайных объекта — из разных категорий."""
    p = _proportions(counts)
    if p.size == 0:
        return np.nan
    return float(1.0 - (p ** 2).sum())


def hill_q1(counts) -> float:
    """Эффективное число категорий, exp(H). Устойчивее richness."""
    p = _proportions(counts)
    if p.size == 0:
        return np.nan
    return float(np.exp(shannon(counts)))


def hill_q2(counts) -> float:
    """Эффективное число ДОМИНИРУЮЩИХ категорий, 1/sum(p^2)."""
    p = _proportions(counts)
    if p.size == 0:
        return np.nan
    return float(1.0 / (p ** 2).sum())


def top_cat_share(counts) -> float:
    """Доля самой массовой категории. Прямая мера монофункциональности."""
    c = np.asarray(counts, dtype=float)
    total = c.sum()
    if total <= 0:
        return np.nan
    return float(c.max() / total)


def sample_coverage(counts) -> float:
    """
    Оценка полноты выборки по Chao (Turing-Good).
    C_hat = 1 - (f1/n) * ((n-1)*f1 / ((n-1)*f1 + 2*f2))

    Диагностика, а не итоговая метрика: показывает, насколько
    наблюдённое разнообразие близко к истинному. Низкое значение =
    данных в ячейке мало, метрикам верить нельзя.
    """
    c = np.asarray(counts, dtype=float)
    c = c[c > 0]
    n = c.sum()
    if n <= 1:
        return np.nan
    f1 = float((c == 1).sum())
    f2 = float((c == 2).sum())
    if f1 == 0:
        return 1.0
    denom = (n - 1) * f1 + 2 * f2
    if denom <= 0:
        return np.nan
    return float(1.0 - (f1 / n) * ((n - 1) * f1 / denom))


def compute_all(
    df: pd.DataFrame,
    cat_cols: list[str] | None = None,
    prefix: str = "cat_",
    min_count: int = 10,
) -> pd.DataFrame:
    """
    Считает весь набор метрик по таблице «ячейка x категория».

    df        : индекс — ячейка, колонки — счётчики по категориям
    cat_cols  : какие колонки считать категориями (по умолчанию — по префиксу)
    min_count : ниже порога метрики -> NaN, а не мусорные экстремумы.
                Ячейка с одним POI формально даёт top_cat_share=1.0
                («идеальная монофункциональность»), что бессмысленно.
    """
    if cat_cols is None:
        cat_cols = [c for c in df.columns if c.startswith(prefix)]
    if not cat_cols:
        raise ValueError(f"не найдено колонок с префиксом {prefix!r}")

    mat = df[cat_cols].to_numpy(dtype=float)
    out = pd.DataFrame(index=df.index)
    out["poi_count"] = mat.sum(axis=1)

    funcs = {
        "cat_richness": richness,
        "cat_shannon": shannon,
        "cat_evenness": evenness,
        "cat_gini_simpson": gini_simpson,
        "cat_hill_q1": hill_q1,
        "cat_hill_q2": hill_q2,
        "top_cat_share": top_cat_share,
        "sample_coverage": sample_coverage,
    }
    for name, fn in funcs.items():
        out[name] = [fn(row) for row in mat]

    below = out["poi_count"] < min_count
    out.loc[below, [c for c in out.columns if c != "poi_count"]] = np.nan
    out["below_threshold"] = below

    return out


if __name__ == "__main__":
    # Пример из статьи: 90 ритейла, 1 сервис, 1 досуг.
    # richness говорит "три функции", Hill q1 говорит "фактически одна".
    demo = np.array([90, 1, 1])
    print("richness      =", richness(demo))
    print("hill_q1       =", round(hill_q1(demo), 3))
    print("hill_q2       =", round(hill_q2(demo), 3))
    print("top_cat_share =", round(top_cat_share(demo), 3))
