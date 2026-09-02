"""
Контроль сербского парсера.

Главный тест — сходимость: сумма по общинам обязана совпадать
с республиканским итогом из того же файла. Именно он поймал обе
ошибки первой версии (агрегаты «Град Ниш» и коллизию «Палилула»).

Запуск:
    python tests/test_serbia_census.py data/raw/RS/dnevne_migracije_aktivnog...xlsx
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from adapters.serbia_census import (read_daily_migration,  # noqa: E402
                                    add_self_containment, SINGLE_SETTLEMENT)

# известные контрольные значения для файла работающих, перепись 2022
EXPECTED_WORKERS = {"total": 795_779, "same": 400_170, "n_municipalities": 168}


def test_totals_reconcile(path):
    df = read_daily_migration(path, level="all")
    top = df[df.level == "country_or_macroregion"].iloc[0]
    mun = df[df.level == "municipality"]

    assert abs(mun.total.sum() - top.total) < 1, (
        f"сумма общин {mun.total.sum():,.0f} != итог {top.total:,.0f}. "
        "Скорее всего в общины попал агрегат ('Град X') или потерялась строка."
    )
    assert abs(mun.same_municipality.sum() - top.same_municipality) < 1
    print(f"  ✓ суммы сходятся: {mun.total.sum():,.0f}")
    return mun


def test_keys_unique(mun):
    d = add_self_containment(mun)
    dup = d[d.key.duplicated(keep=False)]
    assert dup.empty, f"дубли ключа: {list(dup.key)}"
    # Палилула обязана присутствовать дважды — но с разными областями
    pal = d[d.name == "Палилула"]
    if len(pal) > 1:
        assert pal.area.nunique() == len(pal), "Палилула не разведена по областям"
        print(f"  ✓ Палилула разведена: {list(pal.area)}")
    print(f"  ✓ ключи уникальны ({len(d)} общин)")


def test_no_city_aggregates(mun):
    bad = mun[mun.name.str.startswith("Град ")]
    assert bad.empty, f"агрегаты просочились в общины: {list(bad.name)}"
    print("  ✓ агрегаты 'Град X' отфильтрованы")


def test_rbsc_bounds(mun):
    d = add_self_containment(mun)
    assert d.rbsc.between(0, 1).all(), "RBSC вне [0,1]"
    # сумма четырёх категорий назначения обязана давать укупно
    parts = (d.same_municipality + d.other_municipality_same_area
             + d.other_area + d.abroad)
    err = (parts - d.total).abs().max()
    assert err < 1, f"категории назначения не складываются в укупно, макс. ошибка {err}"
    print(f"  ✓ RBSC в [0,1], категории складываются (макс. ошибка {err:.0f})")

    # Ключевой контроль: {RBSC == 0} и {только Градска} обязаны совпасть
    # РОВНО. Это тождество по определению дневного мигранта, а не
    # эмпирическая закономерность — расхождение означает ошибку чтения.
    zeros = set(d[d.rbsc == 0].name)
    single = set(d[d.single_settlement].name)
    assert zeros == single, (
        f"нули и однопунктовые не совпали.\n"
        f"  ноль, но многопунктовая: {sorted(zeros - single)}\n"
        f"  однопунктовая, но не ноль: {sorted(single - zeros)}"
    )
    assert single == SINGLE_SETTLEMENT, f"состав изменился: {sorted(single)}"
    print(f"  ✓ нули == однопунктовые, ровно {len(zeros)}: {', '.join(sorted(zeros))}")


if __name__ == "__main__":
    p = sys.argv[1]
    print(f"Проверяю {pathlib.Path(p).name}")
    mun = test_totals_reconcile(p)
    test_keys_unique(mun)
    test_no_city_aggregates(mun)
    test_rbsc_bounds(mun)
    if "aktivnog" in p:
        assert len(mun) == EXPECTED_WORKERS["n_municipalities"]
        print(f"  ✓ {EXPECTED_WORKERS['n_municipalities']} общин, как ожидалось")
    print("ВСЁ ПРОШЛО")
