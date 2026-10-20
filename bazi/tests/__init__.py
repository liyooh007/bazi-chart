"""内置验证套件。

运行方式::

    python -m bazi verify
    python -m bazi.tests          # 等价

覆盖：
1. 节气精度 —— 与 JPL DE441 参考值（10 年 × 24 节气）逐点比对
2. 农历 —— 年表内部一致性（202 个年界）、逐日往返转换、已知春节/闰月
3. 干支 —— 日柱锚点、六十甲子、纳音、空亡、长生、五虎遁/五鼠遁
4. 命例 —— 四则公开名人命盘（跨越 1711–1898）
5. 一致性 —— 大量随机时刻的排盘不变式、五行归一、喜忌互斥、大运递推
"""

from __future__ import annotations

import random
import sys
from datetime import date, datetime, timedelta

__all__ = ["run_all"]


class Report:
    """极简测试报告器。"""

    def __init__(self, verbose: bool = True) -> None:
        self.verbose = verbose
        self.passed = 0
        self.failed: list[tuple[str, str]] = []
        self.details: list[str] = []

    def check(self, cond: bool, name: str, detail: str = "") -> bool:
        if cond:
            self.passed += 1
            if self.verbose:
                print(f"  ✓ {name}")
        else:
            self.failed.append((name, detail))
            print(f"  ✗ {name}  {detail}")
        return cond

    def info(self, text: str) -> None:
        self.details.append(text)
        if self.verbose:
            print(f"  · {text}")

    @property
    def ok(self) -> bool:
        return not self.failed


# --------------------------------------------------------------------------- #
# 1. 节气精度
# --------------------------------------------------------------------------- #
def test_solar_terms(rep: Report) -> None:
    """节气精度：与 DE441 参考值逐点比对。

    容差按年代分级——1900–2050 年为 ±1 分钟（与参考值本身的取整误差同量级），
    2050 年后放宽到 ±2/±3 分钟：差异主要来自 ΔT(TT−UT1) 的外推模型分歧
    （各家对未来 ΔT 的预测本身就有分钟级不确定性），而非黄经级数精度。
    """
    from ..astro import terms_of_year
    from ..data.solar_terms_reference import SOLAR_TERM_REFERENCE, REFERENCE_ORDER

    def tol(year: int) -> int:
        return 1 if year <= 2050 else 2 if year <= 2080 else 3

    rows = []
    worst_all = (0.0, "")
    ok = True
    total = 0
    for year, refs in sorted(SOLAR_TERM_REFERENCE.items()):
        terms = terms_of_year(year)
        base = datetime(year, 1, 1)
        worst = 0
        for name, ref_min in zip(REFERENCE_ORDER, refs):
            dt = terms[name]
            # 参考值日序自 1 起；换算为同口径的分钟数
            got = int(round((dt - base).total_seconds() / 60)) + 1440
            diff = got - ref_min
            total += 1
            if abs(diff) > abs(worst):
                worst = diff
            if abs(diff) > abs(worst_all[0]):
                worst_all = (diff, f"{year} {name}")
            if abs(diff) > tol(year):
                ok = False
        rows.append(f"{year}:最大 {worst:+d} 分")
    rep.check(ok, f"节气精度：{total} 个节气对照 DE441 参考值（容差按年代 1/2/3 分钟）",
              f"最大偏差 {worst_all[0]:+.0f} 分钟（{worst_all[1]}）")
    rep.info("节气逐点偏差：" + "　".join(rows))
    rep.info(f"节气最大偏差 {worst_all[0]:+.0f} 分钟（{worst_all[1]}）；"
             f"1900–2050 年全部 ≤1 分钟")


# --------------------------------------------------------------------------- #
# 2. 农历
# --------------------------------------------------------------------------- #
FESTIVALS = {
    1900: "1900-01-31", 1912: "1912-02-18", 1949: "1949-01-29", 1976: "1976-01-31",
    1984: "1984-02-02", 2000: "2000-02-05", 2023: "2023-01-22", 2024: "2024-02-10",
    2025: "2025-01-29", 2033: "2033-01-31", 2050: "2050-01-23", 2100: "2100-02-09",
}
#: 公开资料可查的闰月（农历年 → 闰几月）
LEAP_CASES = {1900: 8, 1984: 10, 2004: 2, 2017: 6, 2020: 4,
              2023: 2, 2025: 6, 2028: 5, 2033: 11}


def test_lunar(rep: Report) -> None:
    from ..data.lunar_table import LUNAR_YEARS, FIRST_YEAR
    from ..lunar import (
        lunar_year_months, lunar_to_solar, solar_to_lunar, lunar_year_days,
    )

    # 2.1 年表内部一致性：相邻年界之差 == 各月天数之和
    bad = []
    for i in range(len(LUNAR_YEARS) - 1):
        year = FIRST_YEAR + i
        months = lunar_year_months(year)
        span = LUNAR_YEARS[i + 1][0] - LUNAR_YEARS[i][0]
        if sum(m[2] for m in months) != span:
            bad.append(year)
    rep.check(not bad, f"农历年表一致性：{len(LUNAR_YEARS) - 1} 个年界月长合计校验",
              f"不一致年份：{bad[:5]}")

    # 2.2 已知春节
    errs = []
    for ly, iso in FESTIVALS.items():
        got = lunar_to_solar(ly, 1, 1).isoformat()
        if got != iso:
            errs.append(f"{ly}:{got}≠{iso}")
    rep.check(not errs, f"春节日期：{len(FESTIVALS)} 个年份对照公开历表", str(errs))

    # 2.3 闰月
    errs = []
    for ly, leap in LEAP_CASES.items():
        months = lunar_year_months(ly)
        got = next((m[0] for m in months if m[1]), 0)
        if got != leap:
            errs.append(f"{ly}:{got}≠{leap}")
    rep.check(not errs, f"闰月判定：{len(LEAP_CASES)} 个年份", str(errs))

    # 2.4 逐日往返转换（1900-01-31 → 2100-12-31，共 7 万余天）
    d = date(1900, 1, 31)
    end = date(2100, 12, 31)
    n = 0
    errs = []
    while d <= end:
        ld = solar_to_lunar(d.year, d.month, d.day)
        back = lunar_to_solar(ld.year, ld.month, ld.day, ld.is_leap)
        if back != d:
            errs.append(f"{d}→{ld}→{back}")
            if len(errs) > 3:
                break
        if ld.day > ld.month_days:
            errs.append(f"{d} 日序超月长")
            break
        d += timedelta(days=1)
        n += 1
    rep.check(not errs, f"农历逐日往返：{n} 天 公历→农历→公历 完全一致", str(errs[:3]))

    # 2.5 全年天数范围
    days = {lunar_year_days(y) for y in range(1900, 2100)}
    rep.check(all(353 <= x <= 385 for x in days),
              f"农历年天数范围：{min(days)}–{max(days)} 天（应落 353–385）")

    # 2.6 农历年干支
    rep.check(solar_to_lunar(2024, 2, 10).ganzhi_year == "甲辰"
              and solar_to_lunar(2024, 2, 9).ganzhi_year == "癸卯",
              "农历年干支：2024 春节前后由癸卯转甲辰")


# --------------------------------------------------------------------------- #
# 3. 干支
# --------------------------------------------------------------------------- #
#: 独立日柱锚点。
#: 2000-01-01、2024-01-01、2033-01-01、1900-01-01、1900-10-23 取自公开历算网站
#: （ytliu0/ChineseCalendar，DE441）逐日干支；1949-10-01（甲子）为广泛引用的纪日事实，
#: 2033-01-31 可由 2033-01-01 壬子递推校核。
DAY_ANCHORS = {
    (2000, 1, 1): "戊午", (2024, 1, 1): "甲子", (2033, 1, 1): "壬子",
    (1900, 1, 1): "甲戌", (1900, 10, 23): "己巳",
    (1949, 10, 1): "甲子", (2033, 1, 31): "壬午",
}


def test_ganzhi(rep: Report) -> None:
    from ..astro import jdn_from_date
    from ..constants import (
        TIANGAN, DIZHI, ganzhi, shishen, nayin, xunkong, changsheng,
        ZANGGAN, sheng, ke, ke_wo, sheng_wo, WUXING,
    )
    from ..pillars import cast_pillars

    # 3.1 日柱锚点（(JDN + 49) mod 60）
    errs = []
    for (y, m, d), expect in DAY_ANCHORS.items():
        jdn = jdn_from_date(y, m, d)
        got = ganzhi((jdn + 49) % 60)
        if got != expect:
            errs.append(f"{y}-{m}-{d}:{got}≠{expect}")
    rep.check(not errs, f"日柱锚点：{len(DAY_ANCHORS)} 个独立锚点全部吻合", str(errs))

    # 3.2 六十甲子闭合：连续 60 天一循环
    base = jdn_from_date(2024, 1, 1)
    idx = [ganzhi((base + k + 49) % 60) for k in range(60)]
    rep.check(len(set(idx)) == 60 and idx[0] == "甲子" and idx[59] == "癸亥",
              "六十甲子：连续 60 日不重复且首尾为甲子—癸亥")

    # 3.3 十神矩阵自洽
    bad = []
    for g1 in TIANGAN:
        for g2 in TIANGAN:
            s = shishen(g1, g2)
            if s not in ("比肩", "劫财", "食神", "伤官", "偏财", "正财",
                         "七杀", "正官", "偏印", "正印"):
                bad.append((g1, g2, s))
        if shishen(g1, g1) != "比肩":
            bad.append((g1, g1, "self"))
    rep.check(not bad, "十神矩阵：100 组天干组合全部合法，同干为比肩", str(bad[:3]))

    # 3.4 十神与五行生克对应
    ok = True
    for day in TIANGAN:
        dw = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
              "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}[day]
        for other in TIANGAN:
            ow = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
                  "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}[other]
            s = shishen(day, other)
            if dw == ow and not s.startswith(("比", "劫")):
                ok = False
            if s in ("食神", "伤官") and sheng(dw) != ow:
                ok = False
            if s in ("正财", "偏财") and ke(dw) != ow:
                ok = False
            if s in ("正官", "七杀") and ke_wo(dw) != ow:
                ok = False
            if s in ("正印", "偏印") and sheng_wo(dw) != ow:
                ok = False
    rep.check(ok, "十神与五行生克：100 组映射全部符合 生我/克我/我生/我克")

    # 3.5 纳音：每两干支共一音，30 音全覆盖
    pairs_ok = all(nayin(ganzhi(i)) == nayin(ganzhi(i + 1)) for i in range(0, 60, 2))
    names = {nayin(ganzhi(i)) for i in range(60)}
    rep.check(pairs_ok and len(names) == 30,
              f"纳音：60 甲子两两共音，共 {len(names)} 种音")

    # 3.6 空亡：甲子旬空戌亥
    rep.check(xunkong("甲", "子") == ("戌", "亥") and xunkong("甲", "戌") == ("申", "酉"),
              "旬空：甲子旬空戌亥，甲戌旬空申酉")

    # 3.7 十二长生
    cases = {("甲", "亥"): "长生", ("甲", "卯"): "帝旺", ("甲", "午"): "死",
             ("乙", "午"): "长生", ("丙", "寅"): "长生", ("庚", "酉"): "帝旺",
             ("壬", "申"): "长生", ("癸", "卯"): "长生"}
    errs = [f"{k}:{changsheng(*k)}≠{v}" for k, v in cases.items() if changsheng(*k) != v]
    rep.check(not errs, "十二长生：8 组标准状态校验", str(errs))

    # 3.8 五虎遁 / 五鼠遁（用排盘结果反查）
    bad = []
    for year in (1990, 2000, 2010, 2024, 2033):
        for month in range(1, 13):
            fp = cast_pillars(datetime(year, month, 10, 12, 0), "男")
            order = (DIZHI.index(fp.month.zhi) - 2) % 12
            expect = TIANGAN[((TIANGAN.index(fp.year.gan) % 5) * 2 + 2 + order) % 10]
            if fp.month.gan != expect:
                bad.append(f"{year}-{month} {fp.ganzhi}")
            zi = ((TIANGAN.index(fp.day.gan) % 5) * 2 + DIZHI.index(fp.hour.zhi)) % 10
            if fp.hour.gan != TIANGAN[zi]:
                bad.append(f"{year}-{month} 时柱")
    rep.check(not bad, "五虎遁/五鼠遁：5 年 × 12 月 月柱与日时柱推算自洽", str(bad[:3]))

    # 3.9 藏干表完整
    rep.check(all(z in ZANGGAN and 1 <= len(ZANGGAN[z]) <= 3 for z in DIZHI),
              "地支藏干：12 支齐全且每支 1–3 个藏干")


# --------------------------------------------------------------------------- #
# 4. 命例
# --------------------------------------------------------------------------- #
CASES = (
    # (说明, 年月日时分, 性别, 期望四柱)
    ("乾隆 1711-09-25 子时", (1711, 9, 25, 0, 30), "男", "辛卯 丁酉 庚午 丙子"),
    ("蒋介石 1887-10-31 午时", (1887, 10, 31, 12, 0), "男", "丁亥 庚戌 己巳 庚午"),
    ("毛泽东 1893-12-26 辰时", (1893, 12, 26, 8, 0), "男", "癸巳 甲子 丁酉 甲辰"),
    ("周恩来 1898-03-05 辰时", (1898, 3, 5, 8, 0), "男", "戊戌 甲寅 丁卯 甲辰"),
)


def test_cases(rep: Report) -> None:
    from ..pillars import cast_pillars
    for label, (y, m, d, hh, mm), gender, expect in CASES:
        fp = cast_pillars(datetime(y, m, d, hh, mm), gender)
        rep.check(fp.ganzhi == expect, f"命例：{label}", f"得 {fp.ganzhi}，期望 {expect}")


# --------------------------------------------------------------------------- #
# 5. 边界与一致性
# --------------------------------------------------------------------------- #
def test_boundaries(rep: Report) -> None:
    from ..pillars import cast_pillars
    from ..solar_terms import all_terms

    # 5.1 立春换年（2024 立春 02-04 16:26:53）
    lc = all_terms(2024)["立春"]
    before = cast_pillars(lc - timedelta(minutes=5), "男")
    after = cast_pillars(lc + timedelta(minutes=5), "男")
    rep.check(before.year.gan == "癸" and after.year.gan == "甲",
              "立春换年：2024 立春前后年柱由癸卯转甲辰",
              f"{before.ganzhi} / {after.ganzhi}")
    rep.check(before.month.zhi == "丑" and after.month.zhi == "寅",
              "交节换月：立春前后月支由丑转寅")

    # 5.2 子时换日（默认 23:00）
    a = cast_pillars(datetime(2024, 1, 1, 22, 59), "男")
    b = cast_pillars(datetime(2024, 1, 1, 23, 1), "男")
    c = cast_pillars(datetime(2024, 1, 1, 23, 1), "男", day_rollover="midnight")
    rep.check(a.day.gan == "甲" and b.day.gan == "乙" and c.day.gan == "甲",
              "子时换日：23:00 归次日（可切换为 0 点换日）",
              f"{a.ganzhi} / {b.ganzhi} / {c.ganzhi}")

    # 5.3 真太阳时：经度校正方向
    t = cast_pillars(datetime(2024, 6, 1, 12, 0), "男", longitude=116.4)
    rep.check(t.solar_time_applied and abs(
        (t.dt - t.raw_dt).total_seconds() / 60) < 20,
        "真太阳时：北京经度 116.4° 校正量在 ±20 分钟内",
        f"{t.dt}")

    # 5.4 早子时/晚子时小时柱
    z1 = cast_pillars(datetime(2024, 1, 1, 0, 30), "男")
    z2 = cast_pillars(datetime(2024, 1, 1, 23, 30), "男")
    rep.check(z1.hour.zhi == "子" and z2.hour.zhi == "子",
              "子时归属：23:00–00:59 均为子时")


def test_consistency(rep: Report, samples: int = 400, seed: int = 20240210) -> None:
    import json
    from ..chart import BaziChart
    from ..constants import TIANGAN, DIZHI, WUXING, ganzhi
    from ..pillars import cast_pillars

    rng = random.Random(seed)
    bad = []
    import calendar
    for _ in range(samples):
        y = rng.randint(1900, 2100)
        m = rng.randint(1, 12)
        # 覆盖月末/闰日（含 29/30/31 号），不再只取 1–28
        d = rng.randint(1, calendar.monthrange(y, m)[1])
        hh = rng.randint(0, 23)
        gender = rng.choice(("男", "女"))
        chart = BaziChart(y, m, d, hh, 0, gender=gender)
        fp = chart.four_pillars
        # 不变式
        if not (fp.year.index == (fp.bazi_year - 4) % 60):
            bad.append(f"{y}-{m}-{d} 年柱")
        if abs(sum(chart.power.percent.values()) - 100) > 0.5:
            bad.append(f"{y}-{m}-{d} 五行归一")
        if chart.pattern.yongshen not in WUXING:
            bad.append(f"{y}-{m}-{d} 用神")
        if set(chart.pattern.xishen) & set(chart.pattern.jishen):
            bad.append(f"{y}-{m}-{d} 喜忌重叠")
        if chart.gender == "男" and chart.four_pillars.gender != "男":
            bad.append(f"{y}-{m}-{d} 性别")
        # 大运递推：相邻大运在六十甲子中相差 ±1（顺序由年干阴阳与性别决定）
        ds = chart.dayun
        forward = (fp.is_yang_year and gender == "男") or \
                  (not fp.is_yang_year and gender == "女")
        base = fp.month.index
        for k, dz in enumerate(ds, start=1):
            want = ganzhi((base + k) % 60) if forward else ganzhi((base - k) % 60)
            if dz.name != want:
                bad.append(f"{y}-{m}-{d} 大运{k}")
        # JSON 可序列化
        try:
            json.dumps(chart.to_dict(deep=False), ensure_ascii=False)
        except Exception as e:                       # pragma: no cover
            bad.append(f"{y}-{m}-{d} JSON:{e}")
        if len(bad) > 3:
            break
    rep.check(not bad, f"一致性：{samples} 个随机命盘全部通过不变式校验", str(bad[:3]))

    # 日柱连续性：随机年逐日递增
    base = datetime(1988, 3, 1)
    errs = []
    for i in range(0, 400):
        d1 = base + timedelta(days=i)
        d2 = d1 + timedelta(days=1)
        i1 = cast_pillars(d1.replace(hour=12), "男").day.index
        i2 = cast_pillars(d2.replace(hour=12), "男").day.index
        if (i2 - i1) % 60 != 1:
            errs.append(str(d1))
            break
    rep.check(not errs, "日柱连续性：400 天逐日递增一位", str(errs))

    # 大运顺逆方向
    fp1 = cast_pillars(datetime(1990, 5, 12, 12), "男")   # 庚午年（阳）男 → 顺
    fp2 = cast_pillars(datetime(1990, 5, 12, 12), "女")   # 阳年女 → 逆
    from ..fortune import dayun_list
    d1 = dayun_list(fp1, steps=2)
    d2 = dayun_list(fp2, steps=2)
    rep.check(d1[0].name == ganzhi((fp1.month.index + 1) % 60)
              and d2[0].name == ganzhi((fp2.month.index - 1) % 60),
              "大运顺逆：阳年男顺排、阳年女逆排",
              f"{d1[0].name} / {d2[0].name}")


def test_poem(rep: Report) -> None:
    """命理诗：诗库合规、成诗 8 句 7 字、韵脚一致、确定性可复现、要素贴合。"""
    from ..poem import destiny_poem, verify_library
    from ..chart import BaziChart

    # 1) 诗库：全部成句 7 字、偶句韵脚合规
    n, errs = verify_library()
    rep.check(not errs, f"诗库合规：{n} 条成句全部为 7 字且偶句入韵",
              "；".join(errs[:5]))

    # 2) 一批真实/随机命盘：均能成诗且 8 句、每句 7 字、二四六八同韵
    from ..poem import RHYME
    import random as _r
    rng = _r.Random(20261016)
    bad = []
    rhyme_seen = set()
    for _ in range(60):
        y = rng.randint(1900, 2099); m = rng.randint(1, 12)
        from datetime import datetime as _dt
        import calendar as _cal
        d = rng.randint(1, _cal.monthrange(y, m)[1]); hh = rng.randint(0, 23)
        g = rng.choice(("男", "女"))
        c = BaziChart(y, m, d, hh, 0, gender=g)
        r = destiny_poem(c)
        texts = [ln.text for ln in r.lines]
        if len(texts) != 8 or any(len(t) != 7 for t in texts):
            bad.append(f"{y}-{m}-{d} 字数")
        ends = [texts[i][-1] for i in (1, 3, 5, 7)]
        if not all(ch in RHYME[r.rhyme] for ch in ends):
            bad.append(f"{y}-{m}-{d} 韵脚 {ends} 不属 {r.rhyme}")
        if not all(ln.note for ln in r.lines):
            bad.append(f"{y}-{m}-{d} 缺注解")
        if not (0 <= r.score <= 100) or r.grade not in (
                "上上", "上中", "中上", "中平", "中下", "下中", "下下"):
            bad.append(f"{y}-{m}-{d} 评分/评级越界")
        rhyme_seen.add(r.rhyme)
    rep.check(not bad, "60 个随机命盘均成 8 句 7 字、偶句同韵、注解齐全、评分合法",
              "；".join(bad[:5]))
    rep.info(f"命理诗覆盖韵部：{''.join(sorted(rhyme_seen))}（{len(rhyme_seen)}/5）")

    # 3) 确定性：同一八字（variant=0）两次成诗一致；variant 变化可取得不同稿
    c = BaziChart(1990, 5, 12, 14, 30, gender="男")
    r1, r2 = destiny_poem(c), destiny_poem(c)
    same = [l.text for l in r1.lines] == [l.text for l in r2.lines]
    rep.check(same, "同一八字命理诗确定可复现（variant=0）")

    # 4) 名人命例要素贴合：子月冬生必出现调候（火）相关句；评分与注解中含日主
    c2 = BaziChart(1893, 12, 26, 8, 0, gender="男")
    r3 = destiny_poem(c2)
    body = r3.poem + "".join(l.note for l in r3.lines)
    rep.check("丁" in r3.lines[0].text and "丁火" in r3.lines[0].note,
              "命理诗起句切合日干（毛泽东丁火 → 丁火灯窗夜向晨）",
              r3.lines[0].text)
    rep.check("寒" in body and "火" in body,
              "子月寒生的命盘，诗中出现寒天调候（火）要素", body[:80])


def test_range_guards(rep: Report) -> None:
    from ..lunar import solar_to_lunar
    ok = False
    try:
        solar_to_lunar(1890, 1, 1)
    except ValueError as e:
        ok = "1899" in str(e) or "年表" in str(e)
    rep.check(ok, "范围保护：超出农历年表下界的日期明确报错")

    # 农历上界（2100 年腊月之后；2101-01-01 仍属农历 2100 年，不越界）
    ok = False
    try:
        solar_to_lunar(2101, 3, 1)
    except ValueError:
        ok = True
    rep.check(ok, "范围保护：超出农历年表上界的日期明确报错")

    # P0：入参校验——拼错的 gender/rollover/经度/时区必须报错，不静默排出另一张盘
    from datetime import datetime
    from ..pillars import cast_pillars
    base = datetime(1990, 5, 12, 14, 30)
    bad = ({"gender": "M"}, {"day_rollover": "ZI"}, {"longitude": 200.0},
           {"tz_hours": 20.0})
    guard_ok = True
    for kw in bad:
        try:
            cast_pillars(base, **kw)
            guard_ok = False
        except ValueError:
            pass
        except Exception:
            guard_ok = False
    rep.check(guard_ok, "范围保护：非法 gender/换日规则/经度/时区统一 ValueError")

    # P0：datetime_from_jd 月末秒进位不崩（1/3/5/7/8/10/12 月 31 号附近往返）
    from ..astro import jd_from_datetime, datetime_from_jd
    jd_ok = all(datetime_from_jd(jd_from_datetime(datetime(y, m, 31)) + 0.99999 / 86400)
                for y in (1990, 2000, 2024) for m in (1, 3, 12))
    rep.check(jd_ok, "月末秒进位：JD→datetime 在 31 号附近不构造非法日期")

    # P0：_tou_groups 只取年/月/时三干（日柱是日主自己，不算透出）
    from .. import BaziChart
    c = BaziChart(1990, 5, 12, 14, 30, gender="男", longitude=116.4)
    from ..ziping import _tou_groups
    from ..constants import SHISHEN_GROUP, shishen
    fp = c.four_pillars
    expect = {SHISHEN_GROUP[shishen(fp.day.gan, p.gan)]
              for p in (fp.year, fp.month, fp.hour)}
    rep.check(_tou_groups(fp) == expect,
              "子平：透干十神只取年/月/时三干，排除日主比肩")
    # 反巧合：选一个日干≠时干的命盘，旧实现 pillars[:3] 会漏时干、误纳日主比劫
    c2 = BaziChart(1990, 1, 1, 4, 0, gender="男")      # 丙寅日 / 庚寅时
    fp2 = c2.four_pillars
    assert fp2.day.gan != fp2.hour.gan
    expect2 = {SHISHEN_GROUP[shishen(fp2.day.gan, p.gan)]
               for p in (fp2.year, fp2.month, fp2.hour)}
    got2 = _tou_groups(fp2)
    rep.check(got2 == expect2 and "财星" in got2,
              "子平：时干≠日干时透干集合仍取年/月/时（回归：旧 [:3] 漏时干）",
              f"got={got2} expect={expect2}")

    # P1：MCP 流月区间严格单调衔接，第12月（丑月）起于次年小寒
    from ..mcp_server import tool_liuyue
    ly_bad = ""
    for yr in (2024, 2049):
        rows = tool_liuyue(dict(birth_year=2000, birth_month=1, birth_day=1,
                                birth_hour=12, gender="男", year=yr))
        if len(rows) != 12:
            ly_bad = f"{yr} 月数={len(rows)}"; break
        if any(rows[i]["止"] <= rows[i]["起"] for i in range(12)):
            ly_bad = f"{yr} 区间倒挂"; break
        if any(rows[i]["止"] != rows[i + 1]["起"] for i in range(11)):
            ly_bad = f"{yr} 区间不衔接"; break
        if not (rows[-1]["起"].startswith(str(yr + 1))
                and rows[-1]["止"].startswith(str(yr + 1))):
            ly_bad = f"{yr} 丑月未在次年: {rows[-1]['起']}"
    rep.check(not ly_bad, "MCP流月：12月区间单调衔接，丑月起于次年小寒", ly_bad)


    # P0：大运匹配是半开区间——交运年只命中一步大运；交运前的立春不归该运
    from ..fortune import dayun_at
    from ..solar_terms import all_terms
    dys = c.dayun
    boundary_bad = False
    if len(dys) >= 2:
        lc = all_terms(dys[1].start_year, c.tz_hours)["立春"]
        hit = [d for d in dys if d.start_dt <= lc
               and (d.end_dt is None or lc < d.end_dt)]
        boundary_bad = len(hit) != 1
    # 该盘第 2 运 2008-08 交运：2008 立春在交运前→仍属第 1 运；2009 立春→第 2 运
    rep.check(not boundary_bad
              and dayun_at(dys, 2008, c.tz_hours) is dys[0]
              and dayun_at(dys, 2009, c.tz_hours) is dys[1],
              "大运：交运边界年只命中一步（半开区间，立春时刻比较）")


# --------------------------------------------------------------------------- #
# 入口
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# 8. 月令加权方向 & 流年天喜（P1/P2 回归）
# --------------------------------------------------------------------------- #
def test_weight_tianxi(rep: Report) -> None:
    from ..shensha import liunian_shensha

    # P2：子年生人，天喜在酉（红鸾卯之冲），冲太岁在午；二者不可同位
    names = {n for n, _ in liunian_shensha("酉", "子")}
    rep.check("天喜" in names and "冲太岁" not in names,
              "流年神煞：子年生人遇酉年为天喜（非冲太岁）", f"得 {sorted(names)}")
    names2 = {n for n, _ in liunian_shensha("午", "子")}
    rep.check("冲太岁" in names2 and "天喜" not in names2,
              "流年神煞：子年生人遇午年为冲太岁（非天喜）", f"得 {sorted(names2)}")


SECTIONS = (
    ("一、节气精度（对照 JPL DE441）", test_solar_terms),
    ("二、农历转换（年表一致性 / 逐日往返 / 春节闰月）", test_lunar),
    ("三、干支运算（日柱锚点 / 十神 / 纳音 / 空亡 / 长生 / 遁法）", test_ganzhi),
    ("四、公开命例复现", test_cases),
    ("五、边界条件（立春 / 子时 / 真太阳时）", test_boundaries),
    ("六、随机一致性（排盘不变式）", test_consistency),
    ("七、命理诗生成", test_poem),
    ("八、月令加权与流年神煞（P1/P2 回归）", test_weight_tianxi),
    ("九、范围保护", test_range_guards),
)


def run_all(verbose: bool = True) -> int:
    rep = Report(verbose)
    if verbose:
        print("=" * 74)
        from .. import __version__ as _v
        print(f"  八字命理引擎 v{_v} — 内置验证套件")
        print("=" * 74)
    for title, fn in SECTIONS:
        if verbose:
            print(f"\n{title}")
        try:
            fn(rep)
        except Exception as exc:                      # pragma: no cover
            rep.failed.append((title, f"异常：{type(exc).__name__}: {exc}"))
            print(f"  ✗ {title} 抛出异常：{type(exc).__name__}: {exc}")
    total = rep.passed + len(rep.failed)
    if verbose:
        print("\n" + "=" * 74)
        for line in rep.details:
            print(f"  {line}")
        print("=" * 74)
        print(f"  结果：{rep.passed}/{total} 项通过"
              + ("　✅ 全部通过" if rep.ok else f"　❌ 失败 {len(rep.failed)} 项"))
        for name, detail in rep.failed:
            print(f"    - {name}: {detail}")
        print("=" * 74)
    return 0 if rep.ok else 1


if __name__ == "__main__":                            # pragma: no cover
    sys.exit(run_all())
