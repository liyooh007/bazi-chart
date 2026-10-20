"""大运、流年、流月、小运。

起运规则
--------
* 阳年男 / 阴年女 → **顺排**（自月柱顺行），取出生后到**下一个节**的天数
* 阴年男 / 阳年女 → **逆排**（自月柱逆行），取出生前到**上一个节**的天数
* 折算：**3 天 = 1 年**，1 天 = 4 个月，1 时辰（2 小时）= 10 天
* 交运时刻 = 出生时刻 + 折算出的时间跨度

流年
----
* 流年干支以**立春**为界（与年柱一致）
* 流月干支由流年干"五虎遁"推得，交月以**节**为界
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from . import solar_terms
from .constants import (
    TIANGAN, DIZHI, ganzhi, shishen, relations, changsheng,
    GAN_WUXING, ZHI_WUXING, JIE_TERMS, JIE_TO_MONTH_ZHI,
)

__all__ = ["DaYun", "LiuNian", "dayun_list", "start_age", "liunian_of", "liuyue_of"]


# --------------------------------------------------------------------------- #
# 起运
# --------------------------------------------------------------------------- #
def start_age(fp, roll_days_per_year: float = 3.0) -> tuple[float, datetime, str]:
    """计算起运。

    返回 ``(起运岁数(含小数), 交运时刻, 顺逆说明)``。
    """
    forward = (fp.is_yang_year and fp.gender == "男") or \
              (not fp.is_yang_year and fp.gender == "女")
    tz = fp.tz_hours
    if forward:
        _, next_t = solar_terms.next_jie(fp.dt, tz)
        days = (next_t - fp.dt).total_seconds() / 86400.0
        direction = "顺排"
    else:
        _, prev_t = solar_terms.prev_jie(fp.dt, tz)
        days = (fp.dt - prev_t).total_seconds() / 86400.0
        direction = "逆排"
    years = days / roll_days_per_year
    # 3 天 = 1 年，1 天 = 4 个月，1 时辰(2h) = 10 天
    total_days = years * 365.2422
    jiao = fp.dt + timedelta(days=total_days)
    note = (f"{'阳' if fp.is_yang_year else '阴'}年{'男' if fp.gender == '男' else '女'}"
            f"→{direction}；距{'下' if forward else '上'}一节 {days:.3f} 天，"
            f"折 {years:.3f} 岁（3 天=1 岁）")
    return years, jiao, note


# --------------------------------------------------------------------------- #
# 大运
# --------------------------------------------------------------------------- #
@dataclass
class DaYun:
    """一步大运。"""

    index: int                 # 第几步（1 起）
    gan: str
    zhi: str
    start_age: float           # 起始虚岁（四舍五入前的精确值）
    end_age: float
    start_year: int
    end_year: int
    start_dt: datetime
    end_dt: datetime | None = None    # 下一步交运时刻（半开区间上界），末运为 None
    shishen: str = ""          # 大运天干十神
    zhi_shishen: str = ""      # 大运地支本气十神
    changsheng: str = ""       # 日干在大运支的十二长生
    wuxing: str = ""           # 干支五行
    score: float = 0.0         # 与命局的吉凶相关性粗评分

    @property
    def name(self) -> str:
        return self.gan + self.zhi

    @property
    def gan_wuxing(self) -> str:
        return GAN_WUXING[TIANGAN.index(self.gan)]

    @property
    def zhi_wuxing(self) -> str:
        return ZHI_WUXING[DIZHI.index(self.zhi)]

    def __str__(self) -> str:
        return (f"{self.name}（{int(self.start_age)}–{int(self.end_age)}岁，"
                f"{self.start_year}–{self.end_year}）")


def dayun_list(fp, pattern=None, power=None, steps: int = 10,
               roll_days_per_year: float = 3.0) -> list[DaYun]:
    """排大运（默认 10 步）。"""
    years, jiao, _ = start_age(fp, roll_days_per_year)
    forward = (fp.is_yang_year and fp.gender == "男") or \
              (not fp.is_yang_year and fp.gender == "女")
    base = fp.month.index
    out: list[DaYun] = []
    xishen, jishen, yong = set(), set(), ""
    qw = {}
    if pattern is not None:
        xishen = set(pattern.xishen)
        jishen = set(pattern.jishen)
        yong = pattern.yongshen
        from .qiongtong import qiongtong_wuxing
        qw = qiongtong_wuxing(fp.day.gan, fp.month.zhi)
    dg = fp.day.gan
    for k in range(1, steps + 1):
        idx = (base + k) % 60 if forward else (base - k) % 60
        name = ganzhi(idx)
        gan, zhi = name[0], name[1]
        s_age = years + (k - 1) * 10
        e_age = s_age + 10
        s_dt = jiao + timedelta(days=(k - 1) * 10 * 365.2422)
        e_dt = jiao + timedelta(days=k * 10 * 365.2422)
        dz = DaYun(k, gan, zhi, s_age, e_age,
                   s_dt.year, e_dt.year, s_dt, e_dt,
                   shishen(dg, gan), shishen(dg, _zhi_main_gan(zhi)),
                   changsheng(dg, zhi),
                   f"{GAN_WUXING[TIANGAN.index(gan)]}{ZHI_WUXING[DIZHI.index(zhi)]}")
        if pattern is not None:
            dz.score = _dayun_score(gan, zhi, fp, yong, xishen, jishen, qw)
        out.append(dz)
    return out


def dayun_at(dayuns: list[DaYun], year: int, tz_hours: float = 8.0) -> DaYun | None:
    """流年（以该年立春为界）落在哪一步大运：半开区间 [start_dt, end_dt)。

    边界年（交运年）不再同时命中两步；用立春时刻而非年初一/1月1日。
    """
    from .solar_terms import all_terms
    lichun = all_terms(year, tz_hours)["立春"]
    for d in dayuns:
        if d.start_dt <= lichun and (d.end_dt is None or lichun < d.end_dt):
            return d
    return None


def _zhi_main_gan(zhi: str) -> str:
    from .constants import ZANGGAN
    return ZANGGAN[zhi][0]


def _dayun_score(gan: str, zhi: str, fp, yong: str, xishen: set, jishen: set,
                 qw: dict | None = None) -> float:
    """大运干支对命局的粗略吉凶评分（-3 ~ +3）。

    qw 为《穷通宝鉴》调候五行（``{"primary","assist"}``）。调候与扶抑是两套
    取用：若某干支五行已被扶抑的用神/喜神计入，则不再重复加；只对"扶抑没
    认、但恰是调候首要"的干支补一笔（权重减半），避免异路两说 double-count。
    """
    s = 0.0
    qw = qw or {}
    for ch, w in ((gan, 1.0), (zhi, 1.2)):
        wx = GAN_WUXING[TIANGAN.index(ch)] if ch in TIANGAN else ZHI_WUXING[DIZHI.index(ch)]
        if wx == yong:
            s += w
        elif wx in xishen:
            s += w * 0.6
        elif wx in jishen:
            s -= w * 0.8
        elif qw and wx == qw.get("primary"):
            s += w * 0.5          # 扶抑未取而调候首取：半权加分
        elif qw and wx in qw.get("assist", []):
            s += w * 0.25         # 调候辅佐：轻加
    # 冲刑害月令 / 日支
    for a, b, pen in ((zhi, fp.month.zhi, 0.8), (zhi, fp.day.zhi, 1.0)):
        r = relations(a, b)
        if "六冲" in r:
            s -= pen
        if "三刑" in r or "自刑" in r:
            s -= pen * 0.6
        if "六合" in r or "半合" in r:
            s += pen * 0.3
    return round(max(-3.0, min(3.0, s)), 2)


# --------------------------------------------------------------------------- #
# 流年 / 流月
# --------------------------------------------------------------------------- #
@dataclass
class LiuNian:
    """一个流年。"""

    year: int
    gan: str
    zhi: str
    age: float                  # 周岁（按年差）
    shishen: str
    zhi_shishen: str
    changsheng: str
    relations: list[str] = field(default_factory=list)
    shensha: list[tuple[str, str]] = field(default_factory=list)
    dayun: str = ""
    tags: list[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.gan + self.zhi

    def __str__(self) -> str:
        return f"{self.year} {self.name}（{self.age:.0f}岁）"


def liunian_of(fp, year: int, pattern=None, dayun: DaYun | None = None) -> LiuNian:
    """排某公历年的流年（以立春为界）。"""
    i = (year - 4) % 60
    gan, zhi = TIANGAN[i % 10], DIZHI[i % 12]
    dg = fp.day.gan
    rels: list[str] = []
    for label, p in zip(("年", "月", "日", "时"), fp.pillars):
        for r in relations(zhi, p.zhi):
            rels.append(f"流年{zhi}—{label}{p.zhi} {r}")
    ln = LiuNian(year, gan, zhi, year - fp.raw_dt.year,
                 shishen(dg, gan), shishen(dg, _zhi_main_gan(zhi)),
                 changsheng(dg, zhi), rels)
    if dayun is not None:
        ln.dayun = dayun.name
        if dayun.zhi == zhi:
            ln.tags.append("岁运并临（大运与流年同支）")
        if dayun.name == ln.name:
            ln.tags.append("岁运伏吟（大运与流年干支完全相同）")
    if pattern is not None:
        wx = GAN_WUXING[TIANGAN.index(gan)]
        if wx == pattern.yongshen:
            ln.tags.append(f"流年天干为用神（{wx}），主得力")
        if wx in pattern.jishen:
            ln.tags.append(f"流年天干为忌神（{wx}），主耗损")
        zwx = ZHI_WUXING[DIZHI.index(zhi)]
        if zwx in pattern.jishen:
            ln.tags.append(f"流年地支为忌神（{zwx}）")
    from .shensha import liunian_shensha
    ln.shensha = liunian_shensha(zhi, fp.year.zhi)
    return ln


def liuyue_of(fp, year: int) -> list[tuple[str, str, str]]:
    """某流年的流月表：``[(节气月, 月干支, 十神), ...]``（自寅月起）。"""
    i = (year - 4) % 60
    year_gan = TIANGAN[i % 10]
    out = []
    for k, jie in enumerate(JIE_TERMS):
        zhi_idx = JIE_TO_MONTH_ZHI[jie]
        gan_idx = ((TIANGAN.index(year_gan) % 5) * 2 + 2 + k) % 10
        name = TIANGAN[gan_idx] + DIZHI[zhi_idx]
        out.append((jie, name, shishen(fp.day.gan, TIANGAN[gan_idx])))
    return out
