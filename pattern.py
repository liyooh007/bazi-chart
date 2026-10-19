"""格局、用神、喜忌。

取格顺序（子平法）
------------------
1. **禄刃格**：月支为日干临官（建禄格）或帝旺（月刃/羊刃格）
2. **透干取格**：月支藏干透出年/月/时干者，取其十神为格（本气优先，次中气、余气）
3. **月令本气取格**：皆不透时，以月支本气十神为格
4. **变格**：专旺（曲直/炎上/稼穑/从革/润下）、从格（从财/从杀/从儿/从势）、
   化气格（日干与邻干五合而化神得地）

用神
----
* 正格：**扶抑**为主（身强取财官食伤、身弱取印比），
  叠加**寒暖燥湿调候**修正，两神交战叠加**通关**修正。
* 变格：顺其旺势（专旺取本气、从格取所从之神）。

说明：本模块的调候为"寒暖燥湿"规则化实现（冬生喜火、夏生喜水、
土多喜木疏、金寒喜火炼等），未内置《穷通宝鉴》120 条逐条表格，
如需严格比对可自行替换 :func:`tiaohou`。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .constants import (
    TIANGAN, WUXING, shishen, sheng, ke, sheng_wo, ke_wo,
    LUSHEN, YANGREN,
)

__all__ = ["Pattern", "determine_pattern", "tiaohou", "useful_god"]

#: 专旺格名称
ZHUANWANG = {"木": "曲直格", "火": "炎上格", "土": "稼穑格",
             "金": "从革格", "水": "润下格"}


@dataclass
class Pattern:
    """格局与用神综合结论。"""

    name: str                                  # 格局名，如"正官格"
    kind: str = "正格"                         # 正格 / 禄刃格 / 专旺格 / 从格 / 化气格
    basis: str = ""                            # 取格依据说明
    yongshen: str = ""                         # 用神（五行）
    xishen: list[str] = field(default_factory=list)     # 喜神五行
    jishen: list[str] = field(default_factory=list)     # 忌神五行
    choushen: list[str] = field(default_factory=list)   # 仇神五行
    xianshen: list[str] = field(default_factory=list)   # 闲神五行
    tiaohou: str = ""                          # 调候用神
    tongguan: str = ""                         # 通关之神
    yongshen_shishen: list[str] = field(default_factory=list)  # 用神对应的十神
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "格局": self.name, "类别": self.kind, "取格依据": self.basis,
            "用神": self.yongshen, "喜神": self.xishen, "忌神": self.jishen,
            "仇神": self.choushen, "闲神": self.xianshen,
            "调候": self.tiaohou, "通关": self.tongguan,
            "用神十神": self.yongshen_shishen, "说明": self.notes,
        }


# --------------------------------------------------------------------------- #
# 取格
# --------------------------------------------------------------------------- #
def _tou_gan(fp) -> set[str]:
    """透干之年/月/时天干。"""
    return {fp.year.gan, fp.month.gan, fp.hour.gan}


def determine_pattern(fp, strength: dict, power) -> Pattern:
    """判定格局并给出用神喜忌。

    :param fp: 四柱
    :param strength: :func:`bazi.pillars.day_master_strength` 的结果
    :param power: :func:`bazi.pillars.wuxing_balance` 的结果
    """
    dg = fp.day.gan
    dw = fp.day.gan_wuxing
    month_zhi = fp.month.zhi
    score = strength["score"]

    # ---------- 变格优先：专旺 / 从格 / 化气 ----------
    if score >= 72 and strength["de_ling"].startswith("得令"):
        p = Pattern(ZHUANWANG[dw], "专旺格",
                    basis=f"日主{dg}（{dw}）{strength['de_ling']}，印比得势（{score:.0f} 分），"
                          f"全局无强力克伐，顺其旺势")
        _set_yongshen(p, dw, [sheng(dw)], [ke_wo(dw), ke(dw)], fp)
        p.notes.append("专旺喜顺不宜逆：喜本气与食伤泄秀，最忌官杀制身、财星耗身。")
        return p

    if score <= 28:
        # 从弱：看谁最强
        dg_group = {"比劫": strength["support"]}
        star = max(("财星", "官杀", "食伤"), key=lambda g: _group_power(fp, power, g))
        gp = _group_power(fp, power, star)
        if gp >= 25:
            name = {"财星": "从财格", "官杀": "从杀格", "食伤": "从儿格"}[star]
            target = {"财星": ke(dw), "官杀": ke_wo(dw), "食伤": sheng(dw)}[star]
            p = Pattern(name, "从格",
                        basis=f"日主{dg}极弱（{score:.0f} 分），{strength['de_ling']}，"
                              f"{star}成势（{gp:.0f} 分），弃命从之")
            _set_yongshen(p, target, [sheng(target)], [dw, sheng_wo(dw)], fp)
            p.notes.append("从格忌印比帮身、忌生扶日主，行运顺所从之神则吉。")
            return p
        p = Pattern("从势格", "从格",
                    basis=f"日主{dg}极弱（{score:.0f} 分）而克泄耗之神混杂，势不可逆")
        _set_yongshen(p, ke_wo(dw) or ke(dw), [], [dw], fp)
        return p

    # 化气格：日干与年干或月干五合，且化神当令
    from .constants import GAN_HE
    for other in (fp.month.gan, fp.year.gan):
        key = frozenset((TIANGAN.index(dg), TIANGAN.index(other)))
        if key in GAN_HE:
            hua = GAN_HE[key]
            if hua == fp.month.zhi_wuxing or power.percent.get(hua, 0) >= 30:
                p = Pattern(f"化{hua}格", "化气格",
                            basis=f"日干{dg}与{other}相合化{hua}，且{hua}神当令得势")
                _set_yongshen(p, hua, [sheng(hua)], [huashen_enemy(hua)], fp)
                p.notes.append("化气格以化神为体，最忌争合、妒合与破化。")
                return p

    # ---------- 禄刃格 ----------
    if month_zhi == LUSHEN[dg]:
        p = Pattern("建禄格", "禄刃格", basis=f"月支{month_zhi}为日干{dg}临官（禄）之位")
        _finish_zhengge(p, fp, strength, power, force_strong=True)
        return p
    if month_zhi == YANGREN[dg]:
        p = Pattern("月刃格", "禄刃格", basis=f"月支{month_zhi}为日干{dg}帝旺（羊刃）之位")
        _finish_zhengge(p, fp, strength, power, force_strong=True)
        p.notes.append("羊刃格喜制伏（官杀），忌冲合刃与劫财夺财。")
        return p

    # ---------- 月令取格：透干优先 ----------
    chosen = None
    for g in fp.month.zanggan:
        if g in _tou_gan(fp):
            chosen = (g, "透干")
            break
    if chosen is None:
        chosen = (fp.month.zanggan[0], "本气")
    g, how = chosen
    ss = shishen(dg, g)
    p = Pattern(f"{ss}格", "正格",
                basis=f"月令{month_zhi}藏干{g}（{how}）为{dg}之{ss}")
    _finish_zhengge(p, fp, strength, power)
    return p


def huashen_enemy(hua: str) -> str:
    return ke_wo(hua)


def _group_power(fp, power, group: str) -> float:
    """某十神大类的五行力量（百分比）。"""
    dg = fp.day.gan
    dw = fp.day.gan_wuxing
    table = {"比劫": dw, "食伤": sheng(dw), "财星": ke(dw),
             "官杀": ke_wo(dw), "印星": sheng_wo(dw)}
    return sum(power.percent.get(wx, 0.0) for wx in table[group].split(","))


def _set_yongshen(p: Pattern, yong: str, xi: list[str], ji: list[str], fp) -> None:
    p.yongshen = yong
    p.xishen = [x for x in dict.fromkeys(xi) if x and x != yong]
    p.xishen = [x for x in p.xishen if x not in ji]        # 喜忌不可重叠
    p.jishen = [x for x in dict.fromkeys(ji)
                if x and x != yong and x not in p.xishen]
    p.choushen = [x for x in (sheng(j) for j in p.jishen)
                  if x not in (yong, *p.xishen, *p.jishen)]
    p.xianshen = [w for w in WUXING if w not in
                  {yong, *p.xishen, *p.jishen, *p.choushen}]
    dg = fp.day.gan
    dw = fp.day.gan_wuxing
    rel = {dw: "比劫", sheng(dw): "食伤", ke(dw): "财星",
           ke_wo(dw): "官杀", sheng_wo(dw): "印星"}
    p.yongshen_shishen = [rel[yong]] if yong in rel else []


def _finish_zhengge(p: Pattern, fp, strength: dict, power, force_strong=False) -> None:
    """正格（含禄刃格）用神：扶抑 + 调候 + 通关。"""
    dg = fp.day.gan
    dw = fp.day.gan_wuxing
    score = strength["score"]
    strong = force_strong or score >= 55
    dg_wx = {dw: "比劫", sheng(dw): "食伤", ke(dw): "财星",
             ke_wo(dw): "官杀", sheng_wo(dw): "印星"}

    if strong:
        # 身强喜抑：财、官杀、食伤中，取力量最旺者（且不与调候冲突）
        cands = [ke(dw), ke_wo(dw), sheng(dw)]
        cands = [w for w in cands if power.percent.get(w, 0) > 0]
        cands.sort(key=lambda w: -power.percent[w])
        yong = cands[0] if cands else ke(dw)
        xi = [sheng(yong)]
        ji = [dw, sheng_wo(dw)]
        p.notes.append(f"日主 {score:.0f} 分偏旺，取{dg_wx[yong]}（{yong}）为用，抑其有余。")
    else:
        cands = [dw, sheng_wo(dw)]
        cands = [w for w in cands if power.percent.get(w, 0) > 0]
        cands.sort(key=lambda w: -power.percent[w])
        yong = cands[0] if cands else sheng_wo(dw)
        xi = [sheng(yong)]
        ji = [ke(dw), ke_wo(dw)]
        p.notes.append(f"日主{score:.0f} 分偏弱，取{dg_wx[yong]}（{yong}）为用，扶其不及。")

    # 调候修正
    th = tiaohou(fp, power)
    if th:
        p.tiaohou = th
        if th == yong:
            p.notes.append(f"调候用神同取{th}，格局与气候一致，最为得力。")
        elif th in p.jishen:
            p.notes.append(f"气候偏枯欲用{th}，然与扶抑相战（{th}为忌），"
                           f"以扶抑为主、调候为辅。")
        else:
            p.notes.append(f"原局{th}气不足，寒暖燥湿失调，取{th}为调候之助。")
            p.xishen.append(th)

    # 通关修正（两神交战）
    tgu, desc = _tongguan(fp, power)
    if tgu:
        p.tongguan = tgu
        if tgu not in (yong, *p.xishen) and tgu not in p.jishen:
            p.notes.append(f"局中{desc}相战，取{tgu}通关，化敌为友。")
            p.xishen.append(tgu)

    _set_yongshen(p, yong, xi + [th or "", tgu or ""], ji, fp)


def _tongguan(fp, power) -> tuple[str, str]:
    """两神交战取通关之神。返回 ``(通关五行, 交战描述)``。"""
    dg = fp.day.gan
    dw = fp.day.gan_wuxing
    p = power.percent
    pairs = [
        (ke_wo(dw), sheng(dw), sheng_wo(dw), "官杀与食伤"),   # 印通关
        (ke(dw), sheng_wo(dw), ke_wo(dw), "财星与印星"),      # 官杀通关
        (dw, ke(dw), sheng(dw), "比劫与财星"),                # 食伤通关
        (ke_wo(dw), dw, sheng_wo(dw), "官杀与比劫"),          # 印通关
    ]
    for a, b, mid, desc in pairs:
        if p.get(a, 0) >= 22 and p.get(b, 0) >= 22 and p.get(mid, 0) < 12:
            return mid, desc
    return "", ""


# --------------------------------------------------------------------------- #
# 调候
# --------------------------------------------------------------------------- #
def tiaohou(fp, power=None) -> str:
    """寒暖燥湿调候用神（规则化实现）。

    * 严冬（亥、子月）水寒木冻 → 喜火解冻；丑月湿冷同理但需火更少
    * 盛夏（巳、午月）火炎土燥 → 喜水润局；未月燥土同理
    * 秋金（申、酉月）金寒喜火炼；春木（寅、卯月）木旺喜金裁
    仅在相应五行确实不足时给出，避免与扶抑结论冲突。
    """
    mz = fp.month.zhi
    dw = fp.day.gan_wuxing
    pct = power.percent if power is not None else {}
    fire, water = pct.get("火", 0.0), pct.get("水", 0.0)
    if mz in "亥子":
        return "火" if fire < 15 else ""
    if mz == "丑":
        return "火" if fire < 10 else ""
    if mz in "巳午":
        return "水" if water < 15 else ""
    if mz == "未":
        return "水" if water < 10 else ""
    if dw == "金" and mz in "申酉":
        return "火" if fire < 12 else ""
    if dw == "木" and mz in "寅卯":
        return "金" if pct.get("金", 0.0) < 10 else ""
    return ""


def useful_god(fp, strength=None, power=None) -> Pattern:
    """便捷入口：一次得到格局与用神（缺省自动计算旺衰与五行力量）。"""
    from .pillars import day_master_strength, wuxing_balance
    power = power or wuxing_balance(fp)
    strength = strength or day_master_strength(fp)
    return determine_pattern(fp, strength, power)
