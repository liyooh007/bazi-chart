"""干支运算：四柱排盘、十神、藏干、纳音、空亡、长生、刑冲合害、五行力量量化。

排盘规则（子平法通行标准）
--------------------------
* **年柱**：以**立春**为界（非正月初一）
* **月柱**：以**节**为界（立春、惊蛰……），月干由"五虎遁"从年干推得
* **日柱**：由儒略日数连续推算（60 日一循环，不分大小月），
  默认 **23:00 换日**（晚子时归次日），可用 ``day_rollover`` 调整
* **时柱**：由"五鼠遁"从日干推得，子时自 23:00 起算
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from . import solar_terms
from .astro import jdn_from_date, equation_of_time, CST_OFFSET
from .constants import (
    TIANGAN, DIZHI, GAN_WUXING, ZHI_WUXING, WUXING,
    ZANGGAN, ZANGGAN_WEIGHT, GAN_YANG, SHISHEN, SHISHEN_GROUP, changsheng, ganzhi_index, nayin, shishen,
    xunkong, sheng, ke, sheng_wo, ke_wo, relations, zhi_hour,
)

__all__ = [
    "Pillar", "FourPillars", "WuXingPower", "cast_pillars", "true_solar_time",
    "build_four_pillars", "shishen_distribution", "wuxing_balance",
]

_ZHI_BY_INDEX = DIZHI
_GAN_BY_INDEX = TIANGAN


# --------------------------------------------------------------------------- #
# 真太阳时
# --------------------------------------------------------------------------- #
def true_solar_time(dt: datetime, longitude: float,
                    tz_hours: float = CST_OFFSET) -> datetime:
    """把标准时换算为**真太阳时**。

    ``真太阳时 = 标准时 + (当地经度 − 时区中央经线) × 4 分钟 + 均时差``

    :param longitude: 当地地理经度（东经为正），如北京 116.4
    """
    standard_meridian = tz_hours * 15.0
    from .astro import jd_from_datetime
    eot = equation_of_time(jd_from_datetime(dt) - tz_hours / 24.0)
    shift = (longitude - standard_meridian) * 4.0 + eot      # 分钟
    return dt + timedelta(minutes=shift)


# --------------------------------------------------------------------------- #
# 单柱
# --------------------------------------------------------------------------- #
@dataclass
class Pillar:
    """一柱（干 + 支）。"""

    gan: str
    zhi: str

    @property
    def name(self) -> str:
        return self.gan + self.zhi

    @property
    def index(self) -> int:
        return ganzhi_index(self.gan, self.zhi)

    @property
    def gan_wuxing(self) -> str:
        return GAN_WUXING[TIANGAN.index(self.gan)]

    @property
    def zhi_wuxing(self) -> str:
        return ZHI_WUXING[DIZHI.index(self.zhi)]

    @property
    def nayin(self) -> str:
        return nayin(self.name)

    @property
    def zanggan(self) -> tuple[str, ...]:
        return ZANGGAN[self.zhi]

    def shishen(self, day_gan: str) -> str:
        return shishen(day_gan, self.gan)

    @property
    def is_yang(self) -> bool:
        return GAN_YANG[TIANGAN.index(self.gan)]

    def __str__(self) -> str:
        return self.name


# --------------------------------------------------------------------------- #
# 四柱
# --------------------------------------------------------------------------- #
@dataclass
class FourPillars:
    """四柱排盘结果（含排盘过程信息）。"""

    year: Pillar
    month: Pillar
    day: Pillar
    hour: Pillar
    dt: datetime                       # 采用的出生时刻（已按需换算真太阳时）
    raw_dt: datetime                   # 原始输入时刻
    bazi_year: int                     # 命理年（立春界）
    month_info: solar_terms.MonthInfo
    lunar_date: object = None          # LunarDate（若可用）
    gender: str = "男"
    solar_time_applied: bool = False
    tz_hours: float = CST_OFFSET

    # ---------- 便捷属性 ----------
    @property
    def day_gan(self) -> str:
        return self.day.gan

    @property
    def pillars(self) -> tuple[Pillar, Pillar, Pillar, Pillar]:
        return (self.year, self.month, self.day, self.hour)

    @property
    def pillar_names(self) -> tuple[str, ...]:
        return tuple(p.name for p in self.pillars)

    @property
    def ganzhi(self) -> str:
        return " ".join(self.pillar_names)

    @property
    def shengxiao(self) -> str:
        from .constants import SHENGXIAO
        return SHENGXIAO[DIZHI.index(self.year.zhi)]

    @property
    def nayin_all(self) -> tuple[str, ...]:
        return tuple(p.nayin for p in self.pillars)

    @property
    def xunkong(self) -> tuple[str, str]:
        return xunkong(self.day.gan, self.day.zhi)

    @property
    def is_yang_year(self) -> bool:
        return GAN_YANG[TIANGAN.index(self.year.gan)]

    def shishen_map(self) -> dict[str, str]:
        """天干十神（年/月/时干，日干为"日主"）。"""
        dg = self.day_gan
        return {
            "年干": shishen(dg, self.year.gan),
            "月干": shishen(dg, self.month.gan),
            "日干": "日主",
            "时干": shishen(dg, self.hour.gan),
        }

    def zanggan_shishen(self) -> dict[str, list[tuple[str, str]]]:
        """四支藏干及其十神。"""
        dg = self.day_gan
        out: dict[str, list[tuple[str, str]]] = {}
        for label, p in zip(("年支", "月支", "日支", "时支"), self.pillars):
            out[label] = [(g, shishen(dg, g)) for g in p.zanggan]
        return out

    def changsheng_map(self, gan: str | None = None) -> dict[str, str]:
        """某天干（默认日干）在四支中的十二长生。"""
        g = gan or self.day_gan
        return {lbl: changsheng(g, p.zhi)
                for lbl, p in zip(("年支", "月支", "日支", "时支"), self.pillars)}

    def relations(self) -> list[str]:
        """四柱之间的刑冲合害关系描述。"""
        from .constants import ZHI_HE, ZHI_CHONG, ZHI_HAI, DIZHI
        out: list[str] = []
        labels = ("年", "月", "日", "时")
        for i in range(4):
            for j in range(i + 1, 4):
                a, b = self.pillars[i].zhi, self.pillars[j].zhi
                for r in relations(a, b):
                    out.append(f"{labels[i]}{a}—{labels[j]}{b} {r}")
        return out

    def to_dict(self) -> dict:
        return {
            "公历": self.raw_dt.strftime("%Y-%m-%d %H:%M"),
            "排盘用时": self.dt.strftime("%Y-%m-%d %H:%M"),
            "真太阳时校正": self.solar_time_applied,
            "性别": self.gender,
            "农历": str(self.lunar_date) if self.lunar_date else None,
            "命理年": self.bazi_year,
            "生肖": self.shengxiao,
            "四柱": list(self.pillar_names),
            "纳音": list(self.nayin_all),
            "旬空": list(self.xunkong),
            "十神": self.shishen_map(),
            "藏干十神": self.zanggan_shishen(),
            "月令": f"{self.month_info.zhi}月（{self.month_info.jie_name} "
                    f"{self.month_info.jie_time:%Y-%m-%d %H:%M} 交节）",
            "日主": self.day_gan,
        }


# --------------------------------------------------------------------------- #
# 排盘
# --------------------------------------------------------------------------- #
def _year_pillar(bazi_year: int) -> Pillar:
    i = (bazi_year - 4) % 60
    return Pillar(TIANGAN[i % 10], DIZHI[i % 12])


def _month_pillar(year_gan: str, zhi_name: str) -> Pillar:
    """五虎遁：甲己之年丙作首，乙庚之岁戊为头，丙辛必定寻庚起，
    丁壬壬位顺行流，戊癸之年甲寅求。"""
    order = (DIZHI.index(zhi_name) - 2) % 12          # 寅=0 … 丑=11
    gan_idx = ((TIANGAN.index(year_gan) % 5) * 2 + 2 + order) % 10
    return Pillar(TIANGAN[gan_idx], zhi_name)


def _day_pillar(y: int, m: int, d: int) -> Pillar:
    """日柱：以儒略日数连续推算，(JDN + 49) mod 60。

    校验锚点：2000-01-01 戊午 · 2024-01-01 甲子 · 1949-10-01 甲子 · 1900-01-01 甲戌
    """
    jdn = jdn_from_date(y, m, d)
    i = (jdn + 49) % 60
    return Pillar(TIANGAN[i % 10], DIZHI[i % 12])


def _hour_pillar(day_gan: str, hour: int) -> Pillar:
    """五鼠遁：甲己还加甲，乙庚丙作初，丙辛从戊起，丁壬庚子居，戊癸壬子居。"""
    zi = zhi_hour(hour)
    gan_idx = ((TIANGAN.index(day_gan) % 5) * 2 + zi) % 10
    return Pillar(TIANGAN[gan_idx], DIZHI[zi])


def cast_pillars(dt: datetime, gender: str = "男", *,
                 longitude: float | None = None,
                 tz_hours: float = CST_OFFSET,
                 day_rollover: str = "zi") -> FourPillars:
    """排四柱。

    :param dt: 出生时刻（标准时，默认中国标准时 UTC+8）
    :param gender: ``"男"`` / ``"女"``
    :param longitude: 若给出（东经为正），自动换算真太阳时
    :param tz_hours: 出生地时区相对 UTC 的偏移（小时）
    :param day_rollover: ``"zi"``（默认，23:00 换日）或 ``"midnight"``（00:00 换日）
    """
    # 统一入参校验：拼写错误宁可报错，也不静默排出另一张盘
    if gender not in ("男", "女"):
        raise ValueError(f"gender 只支持 '男'/'女'，收到 {gender!r}")
    if day_rollover not in ("zi", "midnight"):
        raise ValueError(f"day_rollover 只支持 'zi'/'midnight'，收到 {day_rollover!r}")
    if not -180.0 <= (longitude if longitude is not None else 0.0) <= 180.0:
        raise ValueError(f"longitude 必须在 [-180, 180]，收到 {longitude!r}")
    if not -12.0 <= tz_hours <= 14.0:
        raise ValueError(f"tz_hours 必须在 [-12, 14]，收到 {tz_hours!r}")
    if dt.tzinfo is not None:
        raise ValueError("dt 请传 naive datetime（本地标准时），时区用 tz_hours 表达")

    raw = dt
    applied = False
    if longitude is not None:
        dt = true_solar_time(dt, longitude, tz_hours)
        applied = True

    m_info = solar_terms.lunar_month_info(dt, tz_hours)
    byear = solar_terms.bazi_year(dt, tz_hours)
    ypillar = _year_pillar(byear)
    mpillar = _month_pillar(ypillar.gan, m_info.zhi)

    # 日柱：晚子时（23:00 后）归次日
    d0 = dt.date()
    if day_rollover == "zi" and dt.hour >= 23:
        d0 = d0 + timedelta(days=1)
    dpillar = _day_pillar(d0.year, d0.month, d0.day)
    hpillar = _hour_pillar(dpillar.gan, dt.hour)

    lunar_date = None
    try:
        from .lunar import solar_to_lunar
        lunar_date = solar_to_lunar(dt.year, dt.month, dt.day)
    except ValueError:             # 超出农历年表范围时忽略，不掩盖别的 bug
        lunar_date = None

    return FourPillars(ypillar, mpillar, dpillar, hpillar, dt, raw, byear,
                       m_info, lunar_date, gender, applied, tz_hours)


build_four_pillars = cast_pillars        # 兼容别名


# --------------------------------------------------------------------------- #
# 十神统计与五行力量
# --------------------------------------------------------------------------- #
@dataclass
class WuXingPower:
    """五行力量量化结果（0–100 的相对占比 + 明细）。"""

    scores: dict[str, float] = field(default_factory=dict)
    percent: dict[str, float] = field(default_factory=dict)
    detail: dict[str, list[str]] = field(default_factory=dict)

    def strongest(self) -> str:
        return max(self.scores, key=lambda k: self.scores[k])

    def weakest(self) -> str:
        return min(self.scores, key=lambda k: self.scores[k])

    def missing(self) -> list[str]:
        return [w for w in WUXING if self.scores.get(w, 0.0) <= 1e-9]

    def ranked(self) -> list[tuple[str, float]]:
        return sorted(self.scores.items(), key=lambda kv: -kv[1])


#: 天干力量权重（月/年/时干透出）
GAN_WEIGHT = 1.0
#: 地支力量权重：月支得令最重
ZHI_WEIGHT = {"年支": 0.8, "月支": 1.6, "日支": 1.2, "时支": 0.8}


def wuxing_balance(fp: FourPillars) -> WuXingPower:
    """按加权法量化五行力量。

    模型（可复现，权重公开）：
      1. 天干：年/月/时干各计 1.0；日干计 1.0 但标记为"日主"
      2. 地支：按宫位权重（月支 1.6、日支 1.2、年支 0.8、时支 0.8）
         乘藏干权重（本气 0.6–1.0、中气 0.3、余气 0.1）
      3. 月令得时：当令五行 ×1.2；被月令所克者 ×0.85
      4. 归一化为百分比
    """
    scores = {w: 0.0 for w in WUXING}
    detail: dict[str, list[str]] = {w: [] for w in WUXING}

    # 天干
    for label, p in zip(("年干", "月干", "日干", "时干"), fp.pillars):
        wx = p.gan_wuxing
        w = GAN_WEIGHT
        scores[wx] += w
        detail[wx].append(f"{label}{p.gan}({w:.1f})")

    # 地支藏干
    month_wx = fp.month.zhi_wuxing
    for label, p in zip(("年支", "月支", "日支", "时支"), fp.pillars):
        base = ZHI_WEIGHT[label]
        for g, wt in zip(p.zanggan, ZANGGAN_WEIGHT[p.zhi]):
            wx = GAN_WUXING[TIANGAN.index(g)]
            v = base * wt
            scores[wx] += v
            detail[wx].append(f"{label}{p.zhi}藏{g}({v:.2f})")

    # 月令加权
    for wx in WUXING:
        if wx == month_wx:
            scores[wx] *= 1.2
        elif ke(wx) == month_wx:            # 被月令所克
            scores[wx] *= 0.85
        elif ke_wo(month_wx) == wx:         # 克月令者稍抑
            scores[wx] *= 0.95

    total = sum(scores.values()) or 1.0
    percent = {w: round(v / total * 100, 2) for w, v in scores.items()}
    return WuXingPower({w: round(v, 3) for w, v in scores.items()}, percent, detail)


def shishen_distribution(fp: FourPillars) -> dict[str, float]:
    """十神力量分布（把五行力量折算到十神，便于看"格局之气"）。"""
    dg = fp.day_gan
    dw = fp.day.gan_wuxing
    power = wuxing_balance(fp)
    out = {s: 0.0 for s in SHISHEN}
    table = {dw: "比劫", sheng(dw): "食伤", ke(dw): "财星",
             ke_wo(dw): "官杀", sheng_wo(dw): "印星"}
    for wx, val in power.scores.items():
        grp = table[wx]
        # 同组内按阴阳关系拆分（同我者取同阴阳，仅作示意分配）
        for s in SHISHEN:
            if SHISHEN_GROUP[s] == grp:
                out[s] += val / 2.0
    total = sum(out.values()) or 1.0
    return {k: round(v / total * 100, 2) for k, v in out.items()}


def day_master_strength(fp: FourPillars) -> dict[str, float]:
    """日主旺衰量化：返回各项得分与综合判断。

    * ``support``  印比（生扶）力量
    * ``drain``    财官食伤（克泄耗）力量
    * ``score``    0–100，>55 偏强，<45 偏弱
    * 另计月令状态（得令/失令）、通根与否
    """
    power = wuxing_balance(fp)
    dw = fp.day.gan_wuxing
    sheng_wo_wx = sheng_wo(dw)
    support = power.scores[dw] + power.scores[sheng_wo_wx]
    total = sum(power.scores.values()) or 1.0
    drain = total - support
    score = support / total * 100.0

    month_wx = fp.month.zhi_wuxing
    if month_wx == dw:
        de_ling = "得令（月令同气）"
    elif month_wx == sheng_wo_wx:
        de_ling = "得令（月令生我）"
    elif month_wx == sheng(dw):
        de_ling = "失令（月令泄我）"
    elif month_wx == ke(dw):
        de_ling = "失令（月令耗我）"
    else:
        de_ling = "失令（月令克我）"

    # 通根：四支藏干中有日主同类五行
    roots = [g for g in (g for p in fp.pillars for g in p.zanggan)
             if GAN_WUXING[TIANGAN.index(g)] == dw]
    return {
        "support": round(support, 3),
        "drain": round(drain, 3),
        "score": round(score, 2),
        "de_ling": de_ling,
        "roots": roots,
        "tonggen": len(roots) > 0,
    }
