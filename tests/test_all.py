"""pytest 兼容入口：``pytest bazi/tests`` 等价于 ``python -m bazi verify``。"""

from __future__ import annotations

from . import (
    Report, test_boundaries, test_cases, test_consistency, test_ganzhi,
    test_lunar, test_range_guards, test_solar_terms,
)


def _run(fn) -> None:
    rep = Report(verbose=False)
    fn(rep)
    assert rep.ok, f"失败项：{rep.failed}"


def test_solar_term_accuracy() -> None:
    _run(test_solar_terms)


def test_lunar_calendar() -> None:
    _run(test_lunar)


def test_ganzhi_rules() -> None:
    _run(test_ganzhi)


def test_published_cases() -> None:
    _run(test_cases)


def test_boundaries() -> None:
    _run(test_boundaries)


def test_chart_consistency() -> None:
    _run(test_consistency)


def test_range_guard() -> None:
    _run(test_range_guards)
