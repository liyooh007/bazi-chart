"""pytest 兼容入口：``pytest bazi/tests`` 等价于 ``python -m bazi verify``。"""

from __future__ import annotations

# ponytail: 导入必须起别名，否则下方同名 pytest wrapper 会覆盖自检函数，导致 _run 调到自己
from . import (
    Report,
    test_boundaries as _t_boundaries,
    test_cases as _t_cases,
    test_consistency as _t_consistency,
    test_ganzhi as _t_ganzhi,
    test_lunar as _t_lunar,
    test_range_guards as _t_range_guards,
    test_solar_terms as _t_solar_terms,
)


def _run(fn) -> None:
    rep = Report(verbose=False)
    fn(rep)
    assert rep.ok, f"失败项：{rep.failed}"


def test_solar_term_accuracy() -> None:
    _run(_t_solar_terms)


def test_lunar_calendar() -> None:
    _run(_t_lunar)


def test_ganzhi_rules() -> None:
    _run(_t_ganzhi)


def test_published_cases() -> None:
    _run(_t_cases)


def test_boundaries() -> None:
    _run(_t_boundaries)


def test_chart_consistency() -> None:
    _run(_t_consistency)


def test_range_guard() -> None:
    _run(_t_range_guards)


def test_city_longitude_lookup() -> None:
    """城市短名/后缀剥离/未知城市的经度解析。"""
    from ..data.city_longitude import CITY_LONGITUDE, lookup_longitude
    assert len(CITY_LONGITUDE) >= 300
    assert lookup_longitude("济南") == 116.98
    assert lookup_longitude("济南市") == lookup_longitude("济南")
    assert lookup_longitude("北京") == 116.4
    assert lookup_longitude("大理州") == lookup_longitude("大理")
    # 民族自治州全称：单民族 + 多民族连缀都要剥到地名（回归：旧后缀表残留“大理白族”）
    assert lookup_longitude("大理白族自治州") == lookup_longitude("大理")
    assert lookup_longitude("西双版纳傣族自治州") == lookup_longitude("西双版纳")
    assert lookup_longitude("红河哈尼族彝族自治州") == lookup_longitude("红河")
    assert lookup_longitude("香港特别行政区") == CITY_LONGITUDE["香港"]
    assert lookup_longitude("花果山") is None
    assert lookup_longitude("") is None
    assert lookup_longitude(None) is None
