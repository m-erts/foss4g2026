"""
Парсер сербской переписи 2022: дневные миграции.

Файлы РЗС (popis2022, раздел Opštine):
  dnevne_migracije_aktivnog_stanovnistva_koje_obavlja_zanimanje_...xlsx  (TABELA1)
  dnevne_migracije_ucenika_i_studenata_...xlsx                           (TABELA2)

--------------------------------------------------------------------------
ЧЕГО В ЭТИХ ФАЙЛАХ НЕТ: матрицы «откуда → куда».

Назначение задано четырьмя категориями дальности:

    укупно
      у истој области
        у оквиру исте општине     <- числитель самодостаточности
        у другој општини
      у другој области
      у страној држави

Отсюда можно посчитать self-containment, но нельзя делимитировать
функциональные регионы. То же самое в японской переписи.

--------------------------------------------------------------------------
ТОНКОСТЬ ОПРЕДЕЛЕНИЯ, которую надо оговаривать в выводах.

«Дневни мигрант» в Сербии — тот, кто выезжает за пределы своего
НАСЕЛЁННОГО ПУНКТА, а не общины. Отсюда парадокс: у сельских общин
самодостаточность выше, чем у городских. Переезд из села в райцентр
остаётся внутри общины и попадает в числитель, а житель городского
центра, став мигрантом, по определению общину уже покинул.

Крайний случай — общины из одного населённого пункта (Врачар, Савски
венац, Стари град, Раковица, Сремски Карловци, Севојно). У них
self-containment ровно 0: любой их мигрант по определению выехал.
Это артефакт определения, а не экономический результат.

--------------------------------------------------------------------------
СТРУКТУРА ЛИСТА — иерархия с отступами в первом столбце:

    РЕПУБЛИКА СРБИЈА                     (заглавные)
      СРБИЈА – СЕВЕР                     (заглавные)
        Београдски регион                ('регион')
          Београдска област (Град Београд)   ('област')
            Барајево                     <- община
            Вождовац                     <- община
        Нишавска област
          Град Ниш                       <- АГРЕГАТ над городскими общинами
            Медијана                     <- община
            Палилула                     <- община

Две ловушки, обе проверены на файле:

 1. «Град Ниш», «Град Ужице», «Град Пожаревац», «Град Врање» — это
    агрегаты над своими городскими общинами, а не общины. Их сумма
    56 877 ровно объясняет расхождение с республиканским итогом.
 2. «Палилула» встречается дважды — в Белграде и в Нише. Ключ по имени
    даёт коллизию, поэтому ключ = (область, имя).

Каждая территория дополнительно разбита строками «Градска» / «Остала»
(тип поселения) и «с» / «м» / «ж» (пол). Берём только «с» = укупно.
"""

from __future__ import annotations

import pandas as pd

__all__ = ["read_daily_migration", "add_self_containment",
           "SEX_TOTAL", "SINGLE_SETTLEMENT"]

SEX_TOTAL = "с"                             # с / м / ж
_SETTLEMENT_ROWS = {"Градска", "Остала"}    # разрез по типу поселения

COLS = {
    2: "total",                             # укупно
    3: "same_municipality",                 # у оквиру исте општине
    4: "other_municipality_same_area",      # у другој општини
    5: "other_area",                        # у другој области
    6: "abroad",                            # у страној држави
}

#: Общины из одного населённого пункта. У них self-containment
#: структурно равен нулю: любой их дневной мигрант по определению
#: выехал за пределы своего населённого пункта, а значит и общины.
#:
#: НЕ задаётся списком вручную — выводится из самого файла: у такой
#: общины есть строка «Градска» и нет строки «Остала». Проверено:
#: множество {только Градска} и множество {RBSC == 0} совпадают
#: ровно, 8 общин из 168. Это не совпадение, а тождество по
#: определению — поэтому и годится как контроль.
SINGLE_SETTLEMENT = {"Врачар", "Звездара", "Нови Београд", "Раковица",
                     "Савски венац", "Севојно", "Сремски Карловци",
                     "Стари град"}   # ожидаемый результат, см. тест


def _classify(name: str) -> str:
    low = name.lower()
    if name.isupper():
        return "country_or_macroregion"
    if "регион" in low:
        return "region"
    if "област" in low:
        return "area"
    if name.startswith("Град "):
        return "city_aggregate"
    return "municipality"


def read_daily_migration(path: str, sheet: str | None = None,
                         level: str = "municipality") -> pd.DataFrame:
    """
    Читает xlsx РЗС.

    level='municipality' — только общины (168 штук, сумма сходится
    с республиканским итогом 795 779 для работающих).
    level='all' — все уровни иерархии, с колонкой level.

    Имя листа не фиксировано: TABELA1 у работающих, TABELA2 у учащихся.
    По умолчанию берётся первый лист.
    """
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[sheet] if sheet else wb[wb.sheetnames[0]]

    recs, cur_area, cur_city, cur_rec = [], None, None, None
    for row in ws.iter_rows(min_row=5, values_only=True):
        raw, sex = row[0], row[1]
        if raw is None:
            continue
        name = str(raw).strip()
        if not name:
            continue

        # строка разреза по типу поселения — относится к предыдущей территории
        if name in _SETTLEMENT_ROWS:
            if cur_rec is not None and str(sex).strip() == SEX_TOTAL:
                cur_rec["settlement_types"].add(name)
            continue

        kind = _classify(name)
        if kind == "area":
            cur_area, cur_city = name, None
        elif kind == "city_aggregate":
            cur_city = name

        if str(sex).strip() != SEX_TOTAL:
            continue

        rec = {"name": name, "level": kind, "area": cur_area,
               "city": cur_city if kind == "municipality" else None,
               "settlement_types": set()}
        ok = True
        for idx, col in COLS.items():
            try:
                rec[col] = float(row[idx]) if row[idx] is not None else 0.0
            except (TypeError, ValueError):
                ok = False
                break
        if ok:
            recs.append(rec)
            cur_rec = rec
        else:
            cur_rec = None

    df = pd.DataFrame(recs)
    # однопунктовая община = есть «Градска», нет «Остала»
    df["single_settlement"] = df.settlement_types.apply(
        lambda t: t == {"Градска"})
    df = df.drop(columns="settlement_types")
    if level == "municipality":
        df = df[df.level == "municipality"].drop(columns="level")
    return df.reset_index(drop=True)


def add_self_containment(df: pd.DataFrame) -> pd.DataFrame:
    """
    RBSC = доля дневных мигрантов, остающихся в своей общине.

    Знаменатель — все дневные мигранты общины, а НЕ все занятые.
    Это не то же самое, что британский RBSC, где знаменатель — все
    работающие с фиксированным рабочим местом. Величины похожи,
    но напрямую несопоставимы: разные знаменатели.

    single_settlement (проставлен при чтении) помечает общины,
    у которых ноль структурный. Их надо исключать из сводных
    показателей, иначе медиана уезжает вниз.
    """
    out = df.copy()
    out["rbsc"] = (out.same_municipality / out.total).where(out.total > 0)
    out["leakage"] = 1.0 - out.rbsc
    out["share_other_area"] = (out.other_area / out.total).where(out.total > 0)
    out["share_abroad"] = (out.abroad / out.total).where(out.total > 0)
    if "single_settlement" not in out.columns:
        out["single_settlement"] = out.name.isin(SINGLE_SETTLEMENT)
    if "area" in out.columns:
        out["key"] = out.area.fillna("") + " / " + out.name
    return out


if __name__ == "__main__":
    import sys
    p = sys.argv[1]
    d = add_self_containment(read_daily_migration(p))
    real = d[~d.single_settlement]
    print(f"общин: {len(d)}   мигрантов: {d.total.sum():,.0f}")
    print(f"RBSC по всем:        медиана {d.rbsc.median():.3f}")
    print(f"RBSC без однопунктовых: медиана {real.rbsc.median():.3f}")
    print(f"  >= 0.66: {(real.rbsc >= 0.66).mean():.0%}   "
          f">= 0.75: {(real.rbsc >= 0.75).mean():.0%}")
