"""BaziChart：一张命盘的统一入口。

用法::

    from bazi import BaziChart
    c = BaziChart(1990, 5, 12, 14, 30, gender="男", longitude=116.4)
    print(c.report())          # 文本命书
    c.to_dict()                # 结构化数据
    c.liunian_table(2024, 2030)  # 流年表
    c.good_years(2024, 2034)     # 用神得力的年份
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .astro import CST_OFFSET
from .constants import (
    TIANGAN, DIZHI, WUXING, GAN_WUXING, ZHI_WUXING,
    shishen, constellation,
)
from .fortune import (DaYun, LiuNian, dayun_at, dayun_list, start_age,
                      liunian_of, liuyue_of)
from .pillars import (
    FourPillars, WuXingPower, cast_pillars, day_master_strength,
    wuxing_balance, shishen_distribution as _ss_dist,
)
from .pattern import Pattern, useful_god
from .qiongtong import qiongtong
from .shensha import ShenShaResult, find_shensha
from .ziping import (geju_cheng_bai, guan_sha_hun_za, cong_quality,
                     alternative_patterns)

__all__ = ["BaziChart"]


@dataclass
class BaziChart:
    """完整命盘。"""

    year: int
    month: int
    day: int
    hour: int = 0
    minute: int = 0
    gender: str = "男"
    longitude: float | None = None      # 东经为正；给出则启用真太阳时
    tz_hours: float = CST_OFFSET
    name: str = ""
    day_rollover: str = "zi"
    show_alt: bool = True        # 多格局并行：并列展示有争议的备选格局（如专旺/润下）

    # -- 派生结果（延迟计算） --
    four_pillars: FourPillars = None
    power: WuXingPower = None
    strength: dict = None
    pattern: Pattern = None
    shensha: ShenShaResult = None
    dayun: list[DaYun] = None

    def __post_init__(self) -> None:
        if self.gender not in ("男", "女"):
            raise ValueError("gender 必须是 '男' 或 '女'")
        dt = datetime(self.year, self.month, self.day, self.hour, self.minute)
        self.four_pillars = cast_pillars(
            dt, self.gender, longitude=self.longitude,
            tz_hours=self.tz_hours, day_rollover=self.day_rollover)
        self.power = wuxing_balance(self.four_pillars)
        self.strength = day_master_strength(self.four_pillars)
        self.pattern = useful_god(self.four_pillars, self.strength, self.power)
        self.shensha = find_shensha(self.four_pillars)
        self.dayun = dayun_list(self.four_pillars, self.pattern, self.power, steps=10)

    # ------------------------------------------------------------------ #
    # 基本信息
    # ------------------------------------------------------------------ #
    def basic_info(self) -> dict:
        fp = self.four_pillars
        ld = fp.lunar_date
        return {
            "姓名": self.name or "—",
            "性别": self.gender,
            "公历": fp.raw_dt.strftime("%Y-%m-%d %H:%M"),
            "农历": str(ld) if ld else "—（超出农历表范围）",
            "生肖": fp.shengxiao,
            "星座": constellation(self.month, self.day),
            "命理年": f"{fp.bazi_year}（立春为界）",
            "排盘时刻": fp.dt.strftime("%Y-%m-%d %H:%M"),
            "真太阳时": "已启用" if fp.solar_time_applied else "未启用",
            "时区": f"UTC{self.tz_hours:+g}",
            "四柱": fp.pillar_names,
            "纳音": fp.nayin_all,
            "日主": fp.day_gan,
            "旬空": fp.xunkong,
        }

    def shishen_distribution(self) -> dict:
        return _ss_dist(self.four_pillars)

    def qiyun(self) -> dict:
        y, jiao, note = start_age(self.four_pillars)
        return {"起运岁数": round(y, 3), "交运时刻": jiao.strftime("%Y-%m-%d %H:%M"),
                "说明": note}

    # ------------------------------------------------------------------ #
    # 流年
    # ------------------------------------------------------------------ #
    def liunian(self, year: int) -> LiuNian:
        dy = dayun_at(self.dayun, year, self.tz_hours)
        return liunian_of(self.four_pillars, year, self.pattern, dy)

    def liunian_table(self, start: int, end: int) -> list[dict]:
        out = []
        for y in range(start, end + 1):
            ln = self.liunian(y)
            out.append({"年份": y, "干支": ln.name, "岁": int(ln.age),
                        "十神": ln.shishen, "大运": ln.dayun,
                        "标记": "、".join(ln.tags) or "—"})
        return out

    def liuyue(self, year: int) -> list[tuple[str, str, str]]:
        return liuyue_of(self.four_pillars, year)

    def good_years(self, start: int, end: int) -> list[tuple[int, str, str]]:
        """用神/喜神当值的年份（宜进取）。"""
        out = []
        for y in range(start, end + 1):
            ln = self.liunian(y)
            wx = GAN_WUXING[TIANGAN.index(ln.gan)]
            zwx = ZHI_WUXING[DIZHI.index(ln.zhi)]
            if wx == self.pattern.yongshen or zwx == self.pattern.yongshen:
                out.append((y, ln.name, f"用神{self.pattern.yongshen}当值"))
            elif wx in self.pattern.xishen:
                out.append((y, ln.name, f"喜神{wx}当值"))
        return out

    def yearly_forecast(self, year: int) -> dict:
        from .analyze import yearly_forecast
        return yearly_forecast(self, year)

    def poem(self, variant: int = 0):
        """命理诗：据本命盘实算结果生成的七言八句（含逐句注解与评分）。"""
        from .poem import destiny_poem
        return destiny_poem(self, variant=variant)

    def rating(self) -> dict:
        """命局综合评分（0–100）与分项。"""
        from .poem import chart_rating
        return chart_rating(self)

    # ------------------------------------------------------------------ #
    # 输出
    # ------------------------------------------------------------------ #
    def to_dict(self, deep: bool = True) -> dict:
        d = {
            "基本信息": self.basic_info(),
            "四柱": self.four_pillars.to_dict(),
            "五行力量": self.power.percent,
            "旺衰": self.strength,
            "格局用神": self.pattern.to_dict(),
            "穷通宝鉴调候": qiongtong(self.four_pillars.day.gan,
                                     self.four_pillars.month.zhi),
            "子平格局成败": geju_cheng_bai(self),
            "官杀混杂": guan_sha_hun_za(self),
            "从格清浊": cong_quality(self),
            "备选格局": alternative_patterns(self) if self.show_alt else [],
            "神煞": self.shensha.to_dict(),
            "起运": self.qiyun(),
            "命局评分": self.rating(),
            "命理诗": self.poem().to_dict(),
            "大运": [{"干支": x.name, "起岁": round(x.start_age, 2),
                      "止岁": round(x.end_age, 2), "起年": x.start_year,
                      "止年": x.end_year, "十神": x.shishen,
                      "地支十神": x.zhi_shishen, "长生": x.changsheng,
                      "评分": x.score} for x in self.dayun],
        }
        if deep:
            from .analyze import full_analysis
            d["分析"] = full_analysis(self)
        return d

    def report(self, *, width: int = 78, sections: tuple[str, ...] | None = None,
               years: tuple[int, int] | None = None) -> str:
        """生成中文文本命书。"""
        from .analyze import full_analysis
        L: list[str] = []
        bar = "═" * width

        def h1(t: str) -> None:
            L.append("")
            L.append(bar)
            L.append(f"  {t}")
            L.append(bar)

        def h2(t: str) -> None:
            L.append("")
            L.append(f"◆ {t}")
            L.append("─" * width)

        def kv(pairs) -> None:
            for k, v in pairs:
                L.append(f"  {k:<10}{v}")

        fp = self.four_pillars
        bi = self.basic_info()
        h1(f"八字命书　{self.name or '（未具名）'}　{bi['性别']}")
        kv([("公历", bi["公历"]), ("农历", bi["农历"]), ("生肖", bi["生肖"]),
            ("星座", bi["星座"]), ("命理年", bi["命理年"]),
            ("排盘时刻", bi["排盘时刻"] + f"（真太阳时：{bi['真太阳时']}）")])

        h2("四柱排盘")
        labels = ("年柱", "月柱", "日柱", "时柱")
        L.append("         " + "".join(f"{lbl:<12}" for lbl in labels))
        L.append("  天干   " + "".join(f"{p.gan:<12}" for p in fp.pillars))
        L.append("  地支   " + "".join(f"{p.zhi:<12}" for p in fp.pillars))
        L.append("  十神   " + "".join(
            f"{('日主' if i == 2 else shishen(fp.day_gan, p.gan)):<12}"
            for i, p in enumerate(fp.pillars)))
        L.append("  藏干   " + "".join(
            f"{'/'.join(p.zanggan):<12}" for p in fp.pillars))
        L.append("  纳音   " + "".join(f"{p.nayin:<12}" for p in fp.pillars))
        L.append("  长生   " + "".join(
            f"{fp.changsheng_map()[k + '支']:<12}" for k in "年月日时"))
        L.append(f"  旬空   {fp.xunkong[0]}{fp.xunkong[1]}")
        L.append(f"  月令   {fp.month_info.zhi}月（{fp.month_info.jie_name} "
                 f"{fp.month_info.jie_time:%m-%d %H:%M} 交节）")
        L.append(f"  关系   {'；'.join(fp.relations()) or '四柱无明显刑冲合害'}")

        h2("五行力量与旺衰")
        L.append("  " + "　".join(
            f"{w}{self.power.percent[w]:5.1f}%" for w in WUXING))
        L.append("  " + "　".join(
            f"{w}{'█' * int(round(self.power.percent[w] / 2))}" for w in WUXING))
        st = self.strength
        L.append(f"  日主 {fp.day_gan}：{st['de_ling']}，"
                 f"生扶 {st['support']:.2f} / 克泄耗 {st['drain']:.2f}，"
                 f"综合 {st['score']:.1f} 分 → "
                 f"{'偏强' if st['score'] >= 55 else '偏弱' if st['score'] <= 45 else '中和'}")
        L.append(f"  通根：{'有（' + ''.join(st['roots']) + '）' if st['tonggen'] else '无根'}"
                 f"；十神分布：" +
                 "　".join(f"{k}{v:.0f}%" for k, v in self.shishen_distribution().items()
                           if v >= 3))

        h2("格局与用神")
        p = self.pattern
        L.append(f"  格局：{p.name}（{p.kind}）")
        L.append(f"  依据：{p.basis}")
        L.append(f"  用神：{p.yongshen}　喜神：{'、'.join(p.xishen) or '—'}"
                 f"　忌神：{'、'.join(p.jishen) or '—'}"
                 f"　仇神：{'、'.join(p.choushen) or '—'}"
                 f"　闲神：{'、'.join(p.xianshen) or '—'}")
        if p.tiaohou:
            L.append(f"  调候（寒暖）：{p.tiaohou}")
        # 《穷通宝鉴》逐日干×月令的典籍调候用神（独立于扶抑，只供参校）
        from .qiongtong import qiongtong
        qt = qiongtong(self.four_pillars.day.gan, self.four_pillars.month.zhi)
        if qt:
            _as = "、".join(qt["assist"])
            _agree = "与扶抑用神一致" if qt["primary"] == p.yongshen else "与扶抑用神异路，二说并参"
            L.append(f"  调候（穷通宝鉴）：首取 {qt['primary']}"
                     + (f"，佐以 {_as}" if _as else "") + f"（{_agree}）")
        if p.tongguan:
            L.append(f"  通关：{p.tongguan}")
        for note in p.notes:
            L.append(f"  · {note}")
        # 《子平真诠》格局成败（月令格神透否、相神护卫、忌神明破）
        zb = geju_cheng_bai(self)
        if zb["reason"]:
            L.append(f"  格局成败（子平真诠）：{zb['verdict']} —— {zb['reason']}")
        # 官杀混杂去留
        _gs = guan_sha_hun_za(self)
        if _gs["hun"]:
            L.append(f"  官杀混杂：{_gs['note']}" + (f"（解救：{_gs['rescue']}）" if _gs["rescue"] else ""))
        # 真从 / 假从
        _cq = cong_quality(self)
        if _cq["is_cong"]:
            L.append(f"  从格清浊：{_cq['quality']} —— {_cq['reason']}")
        # 多格局并行：有争议的备选格局（专旺/润下等），只陈列不覆盖主判定
        if self.show_alt:
            for a in alternative_patterns(self):
                L.append(f"  备选格局（流派之争）：{a['alt']} —— {a['reason']}")

        h2("神煞")
        ji = "、".join(str(s) for s in self.shensha.group("吉")) or "—"
        xiong = "、".join(str(s) for s in self.shensha.group("凶")) or "—"
        zhong = "、".join(str(s) for s in self.shensha.group("中")) or "—"
        L.append(f"  吉：{ji}")
        L.append(f"  凶：{xiong}")
        L.append(f"  中：{zhong}")
        L.append(f"  神煞吉凶评分：{self.shensha.score:+.1f}")

        if sections is None or "命理诗" in sections:
            from .poem import destiny_poem
            pm = destiny_poem(self)
            h2(f"命理诗（综合 {pm.score:.0f} 分 · {pm.grade}）")
            for i, ln in enumerate(pm.lines):
                prefix = "　" if i % 2 == 0 else "　　"
                L.append(f"{prefix}{ln.text}")
            L.append("")
            for ln in pm.lines:
                L.append(f"  · {ln.text}  — {ln.note}")
            L.append(f"  总断：{pm.summary}")

        h2("大运")
        qy = self.qiyun()
        L.append(f"  起运：{qy['交运时刻']} 交运，{qy['起运岁数']} 岁起运（{qy['说明']}）")
        for d in self.dayun:
            L.append(f"  {d.name}  {int(d.start_age):>3}–{int(d.end_age):<3}岁  "
                     f"{d.start_year}–{d.end_year}  "
                     f"{d.shishen}/{d.zhi_shishen}  {d.changsheng}  "
                     f"{'吉' if d.score > 0.5 else '凶' if d.score < -0.5 else '平'}"
                     f"（{d.score:+.2f}）")

        if years:
            h2(f"流年 {years[0]}–{years[1]}")
            for row in self.liunian_table(*years):
                L.append(f"  {row['年份']}  {row['干支']}  {row['岁']:>3}岁  "
                         f"{row['十神']:<4} 运{row['大运'] or '—'}  {row['标记']}")

        if sections is None or "分析" in sections:
            a = full_analysis(self)
            for key in ("性格", "事业", "财运", "婚姻", "健康", "六亲", "子女",
                        "学业", "开运建议"):
                if sections is not None and key not in sections:
                    continue
                h2(key)
                val = a[key]
                for k, v in val.items():
                    if isinstance(v, list):
                        if not v:
                            continue
                        L.append(f"  {k}：")
                        for item in v:
                            L.append(f"    · {item}")
                    else:
                        txt = str(v)
                        for i, line in enumerate(txt.split("\n")):
                            L.append(f"  {k:<8}{line}" if i == 0 else f"          {line}")
        L.append("")
        L.append("（本命书由 bazi v1.0 生成：节气以太阳视黄经实时推算，"
                 "1900–2050 年与 JPL DE441 偏差 ≤1 分钟；"
                 "农历据权威朔望月年表，逐日往返零误差）")
        return "\n".join(L)

    def __str__(self) -> str:
        return self.report()

    def __repr__(self) -> str:      # pragma: no cover
        return (f"<BaziChart {self.four_pillars.ganzhi} "
                f"{self.gender} {self.pattern.name} 用{self.pattern.yongshen}>")
