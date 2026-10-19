"""节气服务层：为命理排盘提供"交节换月""立春换年"等时刻查询。

对外接口
--------
* :func:`term_time`        某公历年内某个节气的时刻（精确到秒）
* :func:`jie_times`        某公历年内 12 个"节"（月令分野）的时刻
* :func:`lunar_month_info` 某时刻所属的节气月：月支、当令节、距离上下节的时间
* :func:`bazi_year`        命理年（以立春为界）
* :func:`jie_distance`     两时刻之间跨越的节数/天数（大运起运用）

精度：见 :mod:`bazi.astro`，1900–2050 年与权威历表的偏差 ≤1 分钟。
所有时刻默认取中国标准时（UTC+8），可用 ``tz_hours`` 覆盖。
"""

from __future__ import annotations

from datetime import datetime

from .astro import terms_of_year, CST_OFFSET
from .constants import JIE_TERMS, JIE_TO_MONTH_ZHI, SOLAR_TERMS

__all__ = [
    "term_time", "all_terms", "jie_times", "lunar_month_info", "bazi_year",
    "MonthInfo", "jie_distance", "next_jie", "prev_jie",
]

from functools import lru_cache

_CACHE_CAP = 256


@lru_cache(maxsize=_CACHE_CAP)
def all_terms(year: int, tz_hours: float = CST_OFFSET) -> dict[str, datetime]:
    """某公历年内的 24 节气时刻（含 1 月的小寒、大寒）。

    ponytail: LRU 256 年；作为常驻库按年/时区查询时上限可控，需要再大调 _CACHE_CAP。
    """
    return terms_of_year(year, tz_hours)


def term_time(year: int, name: str, tz_hours: float = CST_OFFSET) -> datetime:
    """公历年 ``year`` 内 ``name`` 节气的时刻。"""
    if name not in SOLAR_TERMS:
        raise ValueError(f"未知节气：{name}")
    return all_terms(year, tz_hours)[name]


def jie_times(year: int, tz_hours: float = CST_OFFSET) -> list[tuple[str, datetime]]:
    """公历年内的 12 个"节"，按时间排序。"""
    t = all_terms(year, tz_hours)
    return sorted(((n, t[n]) for n in JIE_TERMS), key=lambda x: x[1])


def _chronological(year: int, tz_hours: float) -> list[tuple[str, datetime]]:
    """``year-1 … year+1`` 三年的 12 节，按时间排序。"""
    out: list[tuple[str, datetime]] = []
    for y in (year - 1, year, year + 1):
        out.extend(jie_times(y, tz_hours))
    out.sort(key=lambda x: x[1])
    return out


class MonthInfo:
    """某时刻的节气月信息。"""

    __slots__ = ("zhi", "jie_name", "jie_time", "next_jie_name", "next_jie_time")

    def __init__(self, zhi: str, jie_name: str, jie_time: datetime,
                 next_jie_name: str, next_jie_time: datetime) -> None:
        self.zhi = zhi
        self.jie_name = jie_name
        self.jie_time = jie_time
        self.next_jie_name = next_jie_name
        self.next_jie_time = next_jie_time

    @property
    def month_length_days(self) -> float:
        """本月节到下一节的天数（≈30.44，冬季节气月略短）。"""
        return (self.next_jie_time - self.jie_time).total_seconds() / 86400.0

    def __repr__(self) -> str:      # pragma: no cover
        return (f"<MonthInfo {self.zhi}月 令{self.jie_name} "
                f"{self.jie_time:%Y-%m-%d %H:%M}>")


def lunar_month_info(dt: datetime, tz_hours: float = CST_OFFSET) -> MonthInfo:
    """给定时刻，返回所属节气月（含当令节与下一节）。"""
    seq = _chronological(dt.year, tz_hours)
    idx = 0
    for i, (_, t) in enumerate(seq):
        if t <= dt:
            idx = i
        else:
            break
    name, t0 = seq[idx]
    nname, t1 = seq[(idx + 1) % len(seq)]
    return MonthInfo(_ZHI_BY_JIE(name), name, t0, nname, t1)


def _ZHI_BY_JIE(name: str) -> str:
    from .constants import DIZHI
    return DIZHI[JIE_TO_MONTH_ZHI[name]]


def prev_jie(dt: datetime, tz_hours: float = CST_OFFSET) -> tuple[str, datetime]:
    """不晚于 ``dt`` 的最近一个节。"""
    seq = _chronological(dt.year, tz_hours)
    last = seq[0]
    for item in seq:
        if item[1] <= dt:
            last = item
        else:
            break
    return last


def next_jie(dt: datetime, tz_hours: float = CST_OFFSET) -> tuple[str, datetime]:
    """晚于 ``dt`` 的最近一个节。"""
    seq = _chronological(dt.year, tz_hours)
    for item in seq:
        if item[1] > dt:
            return item
    return seq[-1]


def bazi_year(dt: datetime, tz_hours: float = CST_OFFSET) -> int:
    """命理年：以立春为界的公历年份编号。"""
    lichun = all_terms(dt.year, tz_hours)["立春"]
    # 立春时刻受 ΔT 与节气归属影响极小；若 dt 在立春之前，命理年 = 上一年
    if dt >= lichun:
        return dt.year
    return dt.year - 1


def jie_distance(dt: datetime, tz_hours: float = CST_OFFSET) -> tuple[float, float]:
    """返回 ``(距上一节的天数, 距下一节的天数)``。

    用于大运起运：阳男阴女顺排取"距下一节"，阴男阳女逆排取"距上一节"。
    """
    _, prev_t = prev_jie(dt, tz_hours)
    _, next_t = next_jie(dt, tz_hours)
    return ((dt - prev_t).total_seconds() / 86400.0,
            (next_t - dt).total_seconds() / 86400.0)
