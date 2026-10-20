"""命令行入口：``python -m bazi ...``。

示例
----
排盘（默认排定 10 步大运与近十年流年）::

    python -m bazi chart 1990-05-12 14:30 --gender 男
    python -m bazi chart 1990-05-12 14:30 -g 女 --lon 116.4 --name 张三
    python -m bazi chart 1990-05-12 14:30 --json > pan.json
    python -m bazi chart 1990-05-12 14:30 --years 2024 2035 --sections 事业 财运

工具子命令::

    python -m bazi terms 2025              # 某年 24 节气时刻（含秒）
    python -m bazi lunar 2025-01-29        # 公历转农历
    python -m bazi solar 2025 6 25         # 农历转公历（闰月加 --leap）
    python -m bazi poem 1990-05-12 14:30 -g 男   # 命理诗（前途/命运/好坏）
    python -m bazi verify                  # 内置自检（节气/农历/日柱/命例）
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime

from .astro import CST_OFFSET

__all__ = ["main"]


def _parse_dt(date_str: str, time_str: str | None) -> tuple[int, int, int, int, int]:
    m = re.match(r"^(\d{3,4})[-/.](\d{1,2})[-/.](\d{1,2})$", date_str.strip())
    if not m:
        raise SystemExit(f"日期格式应为 YYYY-MM-DD，收到：{date_str}")
    y, mo, d = (int(x) for x in m.groups())
    hh = mm = 0
    if time_str:
        m2 = re.match(r"^(\d{1,2})[:：](\d{1,2})?$", time_str.strip())
        if not m2:
            raise SystemExit(f"时间格式应为 HH:MM，收到：{time_str}")
        hh = int(m2.group(1))
        mm = int(m2.group(2) or 0)
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        raise SystemExit("时间应在 00:00–23:59 之间")
    from datetime import datetime
    try:
        datetime(y, mo, d, hh, mm)
    except ValueError as e:
        raise SystemExit(f"日期不合法：{e}") from None
    return y, mo, d, hh, mm


def _resolve_lon(args):
    """--lon 优先；否则按 --city 查内置城市经度。查不到报错。"""
    if args.lon is not None:
        return args.lon
    city = getattr(args, "city", None)
    if city:
        from .data.city_longitude import lookup_longitude
        lon = lookup_longitude(city)
        if lon is None:
            raise SystemExit(
                f"未收录城市「{city}」，请改用 --lon 手动给经度（东经为正、西经为负）")
        return lon
    return None


def cmd_poem(args) -> int:
    """生成切合该八字的命理诗（七言八句，含逐句注解与命局评分）。"""
    from .chart import BaziChart
    y, mo, d, hh, mm = _parse_dt(args.date, args.time)
    chart = BaziChart(y, mo, d, hh, mm, gender=args.gender,
                      longitude=_resolve_lon(args), tz_hours=args.tz,
                      name=args.name, day_rollover=args.rollover)
    if args.json:
        import json as _json
        print(_json.dumps(chart.poem(args.variant).to_dict(),
                          ensure_ascii=False, indent=2))
        return 0
    r = chart.poem(args.variant)
    print("═" * 60)
    print(f"  {r.title}")
    print("═" * 60)
    print(r.poem)
    print("─" * 60)
    for ln in r.lines:
        print(f"  {ln.text}")
        print(f"      └ {ln.note}")
    print("─" * 60)
    print(f"  命局综合评分：{r.score:.0f} / 100　{r.grade}（{r.grade_comment}）")
    print(f"  分项：" + "　".join(f"{k}{v:g}" for k, v in r.score_detail.items()))
    print(f"  总断：{r.summary}")
    print("═" * 60)
    return 0


def cmd_chart(args) -> int:
    from .chart import BaziChart
    y, mo, d, hh, mm = _parse_dt(args.date, args.time)
    chart = BaziChart(y, mo, d, hh, mm, gender=args.gender,
                      longitude=_resolve_lon(args), tz_hours=args.tz,
                      name=args.name, day_rollover=args.rollover)
    years = (args.years[0], args.years[1]) if args.years else None
    sections = tuple(args.sections) if args.sections else None
    if args.json:
        data = chart.to_dict(deep=not args.brief)
        if years:
            data["流年"] = chart.liunian_table(*years)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    print(chart.report(sections=sections, years=years))
    return 0


def cmd_terms(args) -> int:
    from .solar_terms import all_terms
    t = all_terms(args.year, args.tz)
    order = ["小寒", "大寒", "立春", "雨水", "惊蛰", "春分", "清明", "谷雨",
             "立夏", "小满", "芒种", "夏至", "小暑", "大暑", "立秋", "处暑",
             "白露", "秋分", "寒露", "霜降", "立冬", "小雪", "大雪", "冬至"]
    print(f"{args.year} 年二十四节气（UTC{args.tz:+g}，精确到秒）")
    for name in order:
        dt = t[name]
        print(f"  {name}  {dt:%Y-%m-%d %H:%M:%S}")
    return 0


def cmd_lunar(args) -> int:
    from .lunar import solar_to_lunar
    y, mo, d, _, _ = _parse_dt(args.date, None)
    ld = solar_to_lunar(y, mo, d)
    print(f"{y}-{mo:02d}-{d:02d} → {ld}（月长 {ld.month_days} 天，"
          f"本农历年 {ld.year_days} 天）")
    return 0


def cmd_solar(args) -> int:
    from .lunar import lunar_to_solar
    d = lunar_to_solar(args.year, args.month, args.day, args.leap)
    print(f"{args.year} 年{'闰' if args.leap else ''}{args.month}月{args.day}日 → "
          f"{d.isoformat()}")
    return 0


def cmd_verify(args) -> int:
    from .tests import run_all
    return run_all(verbose=not args.quiet)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="bazi", description="八字命理排盘与分析")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("chart", help="排盘并输出命书/JSON")
    c.add_argument("date", help="公历生日 YYYY-MM-DD")
    c.add_argument("time", nargs="?", help="出生时间 HH:MM（可省略）")
    c.add_argument("-g", "--gender", choices=("男", "女"), default="男")
    c.add_argument("--lon", type=float, default=None,
                   help="出生地经度（东经为正、西经为负），给出则换算真太阳时")
    c.add_argument("--city", default=None,
                   help="出生地城市短名（如 济南、大理），内置 356 城经度；--lon 优先于 --city")
    c.add_argument("--tz", type=float, default=CST_OFFSET, help="时区偏移（小时），默认 8")
    c.add_argument("--name", default="", help="姓名（仅用于显示）")
    c.add_argument("--rollover", choices=("zi", "midnight"), default="zi",
                   help="日柱换日时刻：zi=23 点（默认），midnight=0 点")
    c.add_argument("--years", nargs=2, type=int, metavar=("START", "END"),
                   help="附加流年表区间")
    c.add_argument("--sections", nargs="+", default=None,
                   help="只输出指定分析段（性格 事业 财运 婚姻 健康 六亲 子女 学业 开运建议）")
    c.add_argument("--json", action="store_true", help="输出 JSON")
    c.add_argument("--brief", action="store_true", help="JSON 不含分析段")
    c.set_defaults(func=cmd_chart)

    t = sub.add_parser("terms", help="查某年 24 节气时刻")
    t.add_argument("year", type=int)
    t.add_argument("--tz", type=float, default=CST_OFFSET)
    t.set_defaults(func=cmd_terms)

    l = sub.add_parser("lunar", help="公历 → 农历")
    l.add_argument("date")
    l.set_defaults(func=cmd_lunar)

    s = sub.add_parser("solar", help="农历 → 公历")
    s.add_argument("year", type=int)
    s.add_argument("month", type=int)
    s.add_argument("day", type=int)
    s.add_argument("--leap", action="store_true", help="闰月")
    s.set_defaults(func=cmd_solar)

    v = sub.add_parser("verify", help="内置自检（节气/农历/日柱/命例/一致性）")
    v.add_argument("--quiet", action="store_true")
    v.set_defaults(func=cmd_verify)

    pm = sub.add_parser("poem", help="生成切合该八字的命理诗（七言八句）")
    pm.add_argument("date", help="公历生日 YYYY-MM-DD")
    pm.add_argument("time", nargs="?", help="出生时间 HH:MM")
    pm.add_argument("-g", "--gender", choices=("男", "女"), default="男")
    pm.add_argument("--lon", type=float, default=None, help="出生地经度（东经为正、西经为负）")
    pm.add_argument("--city", default=None, help="出生地城市短名（如 济南、大理）；--lon 优先")
    pm.add_argument("--tz", type=float, default=CST_OFFSET)
    pm.add_argument("--name", default="")
    pm.add_argument("--rollover", choices=("zi", "midnight"), default="zi")
    pm.add_argument("--variant", type=int, default=0, help="成稿变体（0 为默认）")
    pm.add_argument("--json", action="store_true")
    pm.set_defaults(func=cmd_poem)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, OverflowError) as e:
        print(f"错误：{e}", file=sys.stderr)
        return 2


if __name__ == "__main__":      # pragma: no cover
    sys.exit(main())
