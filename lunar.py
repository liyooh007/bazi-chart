"""农历（夏历）转换：公历 ⇄ 农历，含闰月。

数据为 1899–2100 年共 202 个农历年的朔望月结构（见 ``data/lunar_table.py``），
可完整重建每年的月序、月长与闰月，并已对 202 个年界全量校验。

注意与命理年的区别
------------------
* **农历年**（此处）以**正月初一**（春节）为界，用于日常日期换算。
* **命理年（八字年柱）**以**立春**为界，由 ``solar_terms`` 与 ``ganzhi`` 处理。
两者相差最大可达一个农历月，切勿混用。
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass
from datetime import date
from functools import lru_cache

from .astro import jdn_from_date
from .constants import DIZHI, TIANGAN, SHENGXIAO
from .data.lunar_table import LUNAR_YEARS, FIRST_YEAR, JDN_OFFSET

__all__ = ["LunarDate", "lunar_year_months", "lunar_year_days",
           "solar_to_lunar", "lunar_to_solar", "LUNAR_MIN", "LUNAR_MAX"]

#: 各农历年正月初一的儒略日数（用于二分查找）
_ANCHORS = tuple(a + JDN_OFFSET for a, _, _, _ in LUNAR_YEARS)


@dataclass(frozen=True)
class LunarDate:
    """一个农历日期。"""

    year: int          # 农历年（干支纪年用 (year - 4) % 60）
    month: int         # 月序 1–12
    day: int           # 日序 1–30
    is_leap: bool      # 是否闰月
    month_days: int    # 本月天数
    year_days: int     # 本农历年天数

    @property
    def ganzhi_year(self) -> str:
        i = (self.year - 4) % 60
        return TIANGAN[i % 10] + DIZHI[i % 12]

    @property
    def shengxiao(self) -> str:
        return SHENGXIAO[(self.year - 4) % 12]

    @property
    def month_name(self) -> str:
        names = ("正", "二", "三", "四", "五", "六", "七", "八", "九", "十", "冬", "腊")
        return ("闰" if self.is_leap else "") + names[self.month - 1] + "月"

    @property
    def day_name(self) -> str:
        if self.day <= 10:
            return ("初一", "初二", "初三", "初四", "初五",
                    "初六", "初七", "初八", "初九", "初十")[self.day - 1]
        if self.day < 20:
            return "十" + ("一", "二", "三", "四", "五", "六", "七", "八", "九")[self.day - 11]
        if self.day == 20:
            return "二十"
        if self.day == 30:
            return "三十"
        return "廿" + ("一", "二", "三", "四", "五", "六", "七", "八", "九")[self.day - 21]

    def __str__(self) -> str:
        return f"{self.ganzhi_year}年{self.month_name}{self.day_name}"


@lru_cache(maxsize=512)
def lunar_year_months(year: int) -> tuple[tuple[int, bool, int, int], ...]:
    """某农历年的月表：``(月序, 是否闰月, 本月天数, 本月初一儒略日数)``。"""
    idx = year - FIRST_YEAR
    if idx < 0 or idx >= len(LUNAR_YEARS):
        raise ValueError(f"农历年表范围 {FIRST_YEAR}–{FIRST_YEAR + len(LUNAR_YEARS) - 1}，"
                         f"不支持 {year} 年")
    anchor, leap, mask, count = LUNAR_YEARS[idx]
    anchor += JDN_OFFSET
    months: list[tuple[int, bool, int, int]] = []
    cursor = anchor
    for i in range(count):
        length = 30 if (mask >> (count - 1 - i)) & 1 else 29
        # 依次给出 正月、二月…；有闰月时在月序 leap 之后再插入一个闰 leap 月
        num = i + 1
        is_leap = False
        if leap and i >= leap:
            num = leap if i == leap else i
            is_leap = i == leap
        months.append((num, is_leap, length, cursor))
        cursor += length
    return tuple(months)


def lunar_year_days(year: int) -> int:
    """某农历年的总天数（353–385）。"""
    ms = lunar_year_months(year)
    return ms[-1][3] + ms[-1][2] - ms[0][3]


def _year_index_from_jdn(jdn: int) -> int:
    if jdn < _ANCHORS[0]:
        raise ValueError("日期早于农历年表下界（1899 年正月初一）")
    i = bisect.bisect_right(_ANCHORS, jdn) - 1
    if i >= len(_ANCHORS):
        i = len(_ANCHORS) - 1
    return i


#: 支持的公历范围
LUNAR_MIN = (FIRST_YEAR, 2, 10)
LUNAR_MAX = (FIRST_YEAR + len(LUNAR_YEARS) - 1, 12, 31)


def solar_to_lunar(y: int, m: int, d: int) -> LunarDate:
    """公历 → 农历。范围 1899-02-10 至 2100-12-31。"""
    jdn = jdn_from_date(y, m, d)
    if jdn < _ANCHORS[0]:
        raise ValueError("日期早于农历年表下界（1899 年正月初一）")
    idx = _year_index_from_jdn(jdn)
    ly = FIRST_YEAR + idx
    months = lunar_year_months(ly)
    # 若落在下一年正月之前，仍属本农历年（含跨公历年）
    cur = None
    for i, (num, is_leap, length, start) in enumerate(months):
        nxt = months[i + 1][3] if i + 1 < len(months) else start + length
        if start <= jdn < nxt:
            cur = (num, is_leap, length, jdn - start + 1)
            break
    if cur is None:                       # 落在年末之后的极少数边界
        num, is_leap, length, start = months[-1]
        cur = (num, is_leap, length, jdn - start + 1)
    num, is_leap, length, day = cur
    return LunarDate(ly, num, day, is_leap, length, lunar_year_days(ly))


def lunar_to_solar(year: int, month: int, day: int, is_leap: bool = False) -> date:
    """农历 → 公历。``is_leap=True`` 表示闰月。"""
    months = lunar_year_months(year)
    target = None
    for num, rl, length, start in months:
        if num == month and rl == is_leap:
            target = (length, start)
            break
    if target is None:
        raise ValueError(f"{year} 年无{'闰' if is_leap else ''}{month}月")
    length, start = target
    if not 1 <= day <= length:
        raise ValueError(f"{year} 年{month}月只有 {length} 天，无第 {day} 日")
    jd = start + day - 1
    # 儒略日数 → 公历日期（Gregorian）
    z = jd
    alpha = (z - 1867216.25) // 36524.25
    a = z + 1 + int(alpha) - int(alpha) // 4
    b = a + 1524
    c = int((b - 122.1) / 365.25)
    dd = int(365.25 * c)
    e = int((b - dd) / 30.6001)
    day_of_month = int(b - dd - int(30.6001 * e))
    mm = e - 1 if e < 14 else e - 13
    yy = c - 4716 if mm > 2 else c - 4715
    return date(yy, mm, day_of_month)


def lunar_months_of_gregorian_year(year: int) -> list[tuple[str, int]]:
    """列出某公历年内的农历月首（用于展示/测试）。"""
    out: list[tuple[str, int]] = []
    for ly in (year - 1, year, year + 1):
        try:
            months = lunar_year_months(ly)
        except ValueError:
            continue
        for num, is_leap, length, start in months:
            xx = start - JDN_OFFSET
            # 还原公历日期
            z = xx
            alpha = (z - 1867216.25) // 36524.25
            a = z + 1 + int(alpha) - int(alpha) // 4
            b = a + 1524
            c = int((b - 122.1) / 365.25)
            dd = int(365.25 * c)
            e = int((b - dd) / 30.6001)
            dom = int(b - dd - int(30.6001 * e))
            mm = e - 1 if e < 14 else e - 13
            yy = c - 4716 if mm > 2 else c - 4715
            if yy == year:
                out.append((f"{'闰' if is_leap else ''}{num}月", dom))
    out.sort(key=lambda t: t[1])
    return out
