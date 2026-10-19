"""综合断验：性格、事业、财运、婚姻、健康、六亲、子女、学业与开运建议。

本模块是"规则 + 断语"层：所有结论都对应可核查的命理法则（十神、宫位、
旺衰、格局、神煞、刑冲合害），不做玄虚发挥。措辞取传统命书中性表述，
凶象给出化解方向而非断言。
"""

from __future__ import annotations

from .constants import (
    TIANGAN, DIZHI, WUXING, GAN_WUXING, ZHI_WUXING, ZANGGAN,
    WUXING_CAREER, WUXING_COLOR, WUXING_DIRECTION, WUXING_ORGAN,
    WUXING_SYMPTOM,
    WUXING_PERSONALITY, WUXING_SEASON, shishen, sheng, ke, sheng_wo, ke_wo, ZHI_HE, changsheng,
)

__all__ = ["full_analysis", "personality", "career", "wealth", "marriage",
           "health", "family", "children", "study", "advice", "yearly_forecast"]

#: 十干性情（子平传统表述）
GAN_NATURE = {
    "甲": "如参天之木，正直向上、有担当而略欠圆通",
    "乙": "如藤萝之木，柔韧善攀、随和而多思虑",
    "丙": "如太阳之火，光明磊落、热情而失之急躁",
    "丁": "如灯烛之火，细致温煦、内敛而心思绵密",
    "戊": "如城墙之土，厚重可靠、守成而稍显固执",
    "己": "如田园之土，含蓄包容、务实而多忧思",
    "庚": "如刀剑之金，刚毅果决、重义而失之刚烈",
    "辛": "如珠玉之金，精致敏锐、重面子而易生嫌隙",
    "壬": "如江河之水，聪敏善变、豁达而欠持守",
    "癸": "如雨露之水，灵秀内秀、细腻而易多愁",
}
#: 十神性情倾向
SHISHEN_TRAIT = {
    "比肩": "自立自主、主张平等、不喜受制", "劫财": "重情好胜、行动力强、易为友破财",
    "食神": "温和乐观、才艺口福、重生活品质", "伤官": "才华外露、善表达创新、不耐拘束",
    "偏财": "慷慨善交际、机会嗅觉灵、偏得之财", "正财": "务实节俭、重视积累、稳定理财",
    "七杀": "果敢有魄力、能抗压、宜制不宜纵", "正官": "守规重责、自律上进、宜体制内发展",
    "偏印": "思维独特、专精偏门、略孤僻", "正印": "仁厚好学、重名誉、得长辈之助",
}


def _pct(power) -> dict[str, float]:
    return power.percent


def _group_power(fp, power, group: str) -> float:
    dw = fp.day.gan_wuxing
    table = {"比劫": dw, "食伤": sheng(dw), "财星": ke(dw),
             "官杀": ke_wo(dw), "印星": sheng_wo(dw)}
    return power.percent.get(table[group], 0.0)


def _dominant_groups(fp, power, n: int = 3) -> list[tuple[str, float]]:
    groups = [(g, _group_power(fp, power, g))
              for g in ("比劫", "食伤", "财星", "官杀", "印星")]
    groups.sort(key=lambda kv: -kv[1])
    return groups[:n]


# --------------------------------------------------------------------------- #
# 性格
# --------------------------------------------------------------------------- #
def personality(fp, pattern, power, strength) -> dict:
    dg = fp.day.gan
    dw = fp.day.gan_wuxing
    yin_yang = "阳" if fp.day.is_yang else "阴"
    out = {
        "日主": f"{dg}（{yin_yang}{dw}）——{GAN_NATURE[dg]}",
        "五行性情": f"命局{dw}气为本，{WUXING_PERSONALITY[dw]}",
        "月令": f"生于{fp.month.zhi}月（{fp.month_info.jie_name}），"
                f"{strength['de_ling']}，月令为全局性情之主导",
    }
    dom = _dominant_groups(fp, power, 3)
    out["十神主导"] = "、".join(
        f"{g}（{v:.1f}%）" for g, v in dom)
    traits = []
    for ss, pctv in sorted(
            ((s, power.percent.get(w, 0)) for s, w in
             ((shishen(dg, g), GAN_WUXING[TIANGAN.index(g)])
              for g in TIANGAN)),
            key=lambda kv: -kv[1])[:3]:
        if pctv > 0:
            traits.append(f"{ss}——{SHISHEN_TRAIT[ss]}")
    out["性格倾向"] = traits
    # 神煞影响
    from .shensha import find_shensha
    ss = find_shensha(fp)
    extra = []
    if ss.by_name("羊刃"):
        extra.append("带羊刃：性刚而急，宜以礼制、以柔济，忌与人争强。")
    if ss.by_name("文昌贵人"):
        extra.append("带文昌：聪慧好文，利考试文书、文职与技艺。")
    if ss.by_name("华盖"):
        extra.append("带华盖：性喜清静、有艺术宗教缘，宜学一技一艺以自处。")
    if ss.by_name("魁罡"):
        extra.append("日坐魁罡：果断有威严，宜身旺有制，忌身弱泄气。")
    if ss.by_name("驿马"):
        extra.append("驿马入命：一生多动、宜外出发展，静守则困。")
    if ss.by_name("桃花") or ss.by_name("红艳煞"):
        extra.append("桃花/红艳入命：异性缘厚，宜守正自持，防情缘生乱。")
    out["神煞提示"] = extra
    grade = "偏强" if strength["score"] >= 55 else "偏弱" if strength["score"] <= 45 else "中和"
    out["总体"] = (f"日主 {dg} 得分 {strength['score']:.1f}（{grade}），"
                   f"格局为{pattern.name}，性情的落点在"
                   f"{_trait_focus(pattern)}。")
    return out


def _trait_focus(pattern) -> str:
    m = {
        "正官格": "自律与责任", "七杀格": "魄力与抗压", "正财格": "务实与积累",
        "偏财格": "经营与人际", "食神格": "才艺与涵养", "伤官格": "才华与突破",
        "正印格": "学养与声誉", "偏印格": "专精与独创", "建禄格": "自立与进取",
        "月刃格": "刚决与竞争",
    }
    if pattern.name in m:
        return m[pattern.name]
    if "专旺" in pattern.kind:
        return "气势与专精"
    if "从" in pattern.kind:
        return "顺势与借力"
    if "化气" in pattern.kind:
        return "圆融与转化"
    return "守中与变通"


# --------------------------------------------------------------------------- #
# 事业
# --------------------------------------------------------------------------- #
def career(fp, pattern, power, strength) -> dict:
    dg = fp.day.gan
    dw = fp.day.gan_wuxing
    gs = {g: _group_power(fp, power, g) for g in ("比劫", "食伤", "财星", "官杀", "印星")}
    yong = pattern.yongshen
    out = {}
    if gs["官杀"] >= 20:
        out["体制/管理"] = ("官杀有力，宜体制、公职、管理与需要规则和责任感的岗位；"
                            "官杀为用则贵，为忌则以技术、专业身份受制而用。")
    if gs["食伤"] >= 22:
        out["技术/表达"] = ("食伤旺，宜技术、研发、设计、教学、媒体、口才与创意类工作，"
                            "忌被过度约束的岗位。")
    if gs["财星"] >= 22:
        out["经营/财务"] = "财星旺，宜经营、销售、财务、贸易；身弱则宜合作经营、量力而行。"
    if gs["印星"] >= 22:
        out["文教/研究"] = "印星旺，宜文教、研究、医药、行政、咨讯等以知识与名声立身之业。"
    if gs["比劫"] >= 30:
        out["独立/竞争"] = "比劫重，宜独立创业或竞争性行业，忌合伙不清、忌替人担保。"
    if not out:
        out["综合"] = "十神分布较均，宜先立足专业再图扩展，随用神之运调整方向。"
    # 行业方向（用神五行）
    out["行业方向"] = f"取用神「{yong}」之气：{WUXING_CAREER[yong]}"
    out["补充方向"] = "、".join(
        f"{wx}：{WUXING_CAREER[wx]}" for wx in pattern.xishen[:2]) or "以用神所在行业为主"
    # 格局断语
    out["格局趋向"] = _career_by_pattern(pattern, strength)
    # 发展方位
    out["有利方位"] = "、".join(WUXING_DIRECTION[wx] for wx in [yong, *pattern.xishen[:1]])
    return out


def _career_by_pattern(pattern, strength) -> str:
    name, kind = pattern.name, pattern.kind
    if kind == "专旺格":
        return "专旺成格，宜深耕一行做到极致，忌频繁转行与人多口杂的合伙。"
    if kind == "从格":
        return "从格顺势，宜依附大平台、大趋势或强人合作，借力胜于硬拼。"
    if kind == "禄刃格":
        return "禄刃格自立自强，宜凭本事吃饭，适合技术、武职、竞技、创业。"
    if name == "正官格":
        return "正官格宜循规而上，仕途、管理、专业职称路线最稳，忌投机。"
    if name == "七杀格":
        return "七杀格宜逆境取贵，压力越大越出成绩，宜军警、法务、外科、竞争性行业。"
    if name in ("正财格", "偏财格"):
        return "财格宜以财为事，善经营者得利；须先固本（身旺）方能守财。"
    if name in ("食神格", "伤官格"):
        return "食伤格靠才华吃饭，宜技艺、内容、教育、设计，忌与上级硬碰。"
    if name in ("正印格", "偏印格"):
        return "印格以学识名声立身，宜考试、资格、研究、文化路线，宜稳不宜快。"
    return "格局平和，宜按用神方向择业，先专后广。"


# --------------------------------------------------------------------------- #
# 财运
# --------------------------------------------------------------------------- #
def wealth(fp, pattern, power, strength) -> dict:
    dg = fp.day.gan
    dw = fp.day.gan_wuxing
    cai = ke(dw)
    out = {}
    cai_pct = power.percent.get(cai, 0.0)
    bi_pct = power.percent.get(dw, 0.0)
    shi_pct = power.percent.get(sheng(dw), 0.0)
    strong = strength["score"] >= 55
    out["财星状态"] = f"财星（{cai}）占 {cai_pct:.1f}%，日主得分 {strength['score']:.1f}"
    if cai_pct >= 25 and strong:
        out["格局判断"] = "财旺身强，财能任我，主善于经营、财源较广，宜主动求财。"
    elif cai_pct >= 25 and not strong:
        out["格局判断"] = "财多身弱，财重身轻，主钱财流动大而积累难，宜稳收、合作、忌铺张与高杠杆。"
    elif cai_pct <= 8:
        out["格局判断"] = "财星偏弱，财源不显，宜以技艺、专业或名望间接生财，忌投机赌性。"
    else:
        out["格局判断"] = "财星适中，财自我生，宜稳步积累，量入为出。"
    if shi_pct >= 20 and cai_pct >= 15:
        out["生财方式"] = "食伤生财，宜靠作品、技术、服务、内容换钱，越主动越有财。"
    if bi_pct >= 30:
        out["风险提示"] = "比劫过重，易被朋友、兄弟、合伙分财，忌借贷担保、忌多人合股不清账。"
    # 财星宫位
    pos = []
    for label, p in zip(("年柱", "月柱", "日柱", "时柱"), fp.pillars):
        if any(GAN_WUXING[TIANGAN.index(g)] == cai for g in p.zanggan):
            pos.append(label)
    out["财星宫位"] = "、".join(pos) if pos else "四柱不见财星（财藏不透）"
    if "时柱" in pos:
        out["晚运"] = "财星居时，晚年得财或子女助力，宜早作积累。"
    if "年柱" in pos:
        out["祖业"] = "财星居年，祖上或有根基，但早年之财须自立方稳。"
    # 用神与财
    if pattern.yongshen == cai:
        out["用神"] = "以财为用：财星发达之运即为得利之时，宜积极经营。"
    elif cai in pattern.jishen:
        out["用神"] = "财星为忌：求财须防因财生灾，宜以正道、限量、专业取胜。"
    return out


# --------------------------------------------------------------------------- #
# 婚姻
# --------------------------------------------------------------------------- #
def marriage(fp, pattern, power, strength) -> dict:
    dg = fp.day.gan
    dw = fp.day.gan_wuxing
    out = {}
    spouse_star = ke(dw) if fp.gender == "男" else ke_wo(dw)
    star_name = "财星" if fp.gender == "男" else "官星"
    out["配偶星"] = (f"{'男' if fp.gender == '男' else '女'}命以{star_name}（{spouse_star}）"
                     f"为配偶，占 {power.percent.get(spouse_star, 0.0):.1f}%")
    # 日支（配偶宫）
    dz = fp.day.zhi
    rel = []
    for label, p in zip(("年", "月", "时"), (fp.year, fp.month, fp.hour)):
        if p.zhi == dz:
            rel.append(f"与{label}支伏吟")
        for a, b, name in ((dz, p.zhi, "六合"), (dz, p.zhi, "六冲"), (dz, p.zhi, "相害")):
            from .constants import relations as _rel
            r = _rel(a, b)
            if name in r:
                rel.append(f"与{label}支{name}")
    out["配偶宫"] = f"日支{dz}（{ZHI_WUXING[DIZHI.index(dz)]}）"
    if rel:
        out["宫位关系"] = "；".join(sorted(set(rel)))
    if any("六冲" in r for r in rel):
        out["提示"] = "配偶宫受冲，主感情易起波澜，宜晚婚、宜择性格互补者，忌意气用事。"
    elif any("六合" in r for r in rel):
        out["提示"] = "配偶宫逢合，夫妻缘厚、易得配偶之助。"
    elif any("相害" in r for r in rel):
        out["提示"] = "配偶宫受害，主口舌暗损，宜多沟通、少计较。"
    else:
        out["提示"] = "配偶宫清静，婚姻大体平顺，重在经营。"
    # 配偶星状态
    star_pct = power.percent.get(spouse_star, 0.0)
    if star_pct <= 8:
        out["配偶星状态"] = "配偶星弱而藏，主配偶低调或聚少离多，宜晚婚。"
    elif star_pct >= 30:
        out["配偶星状态"] = "配偶星旺，主配偶能力强、主见重，宜以柔济刚。"
    else:
        out["配偶星状态"] = "配偶星中和，配偶安分得力。"
    if star_pct >= 28 and strength["score"] <= 45:
        out["身星关系"] = "身弱财（官）旺，易因婚姻家事消耗精力，宜共同经营、忌一方独扛。"
    elif star_pct <= 10 and strength["score"] >= 60:
        out["身星关系"] = "身旺配偶星弱，主自视较高、宜主动经营与体谅。"
    # 神煞
    from .shensha import find_shensha
    ss = find_shensha(fp)
    notes = []
    if ss.by_name("阴差阳错"):
        notes.append("日柱阴差阳错：婚姻亲缘易有阻滞或误会，宜多包容、慎择偶。")
    if ss.by_name("孤辰") or ss.by_name("寡宿"):
        notes.append("命见孤辰或寡宿：性喜独处，宜择性格独立之伴侣。")
    if ss.by_name("红艳煞") or ss.by_name("桃花"):
        notes.append("带桃花/红艳：异性缘重，已婚宜守正，防第三者之扰。")
    if notes:
        out["神煞提示"] = notes
    # 婚期倾向
    out["婚期倾向"] = ("配偶星与日主相合之运、或配偶宫逢合之年易成婚；"
                       f"流年或大运出现{spouse_star}之旺地、或与日支{_he_zhi(dz)}相合之年，"
                       "婚事较易落定。")
    return out


def _he_zhi(zhi: str) -> str:
    idx = DIZHI.index(zhi)
    for pair, _ in ZHI_HE.items():
        if idx in pair:
            other = [z for z in pair if z != idx]
            if other:
                return DIZHI[other[0]]
    return "六合"


# --------------------------------------------------------------------------- #
# 健康
# --------------------------------------------------------------------------- #
def health(fp, pattern, power, strength) -> dict:
    out = {}
    pct = power.percent
    ranked = sorted(pct.items(), key=lambda kv: kv[1])
    weakest = [w for w, v in ranked if v <= 8]
    strongest = [w for w, v in ranked[::-1] if v >= 28]
    out["五行分布"] = "、".join(f"{w}{v:.1f}%" for w, v in ranked)
    if weakest:
        out["偏枯（弱）"] = "、".join(
            f"{w}弱（{WUXING_ORGAN[w]}）→ {WUXING_SYMPTOM[w]['弱']}" for w in weakest)
    if strongest:
        out["偏旺"] = "、".join(
            f"{w}过旺（{WUXING_ORGAN[w]}）→ {WUXING_SYMPTOM[w]['旺']}" for w in strongest)
    # 日主与月令
    dw = fp.day.gan_wuxing
    if strength["score"] <= 40:
        out["体质"] = f"日主{dw}偏弱，元气不足，宜保养为本、忌熬夜耗神与过度劳形。"
    elif strength["score"] >= 65:
        out["体质"] = f"日主{dw}偏旺，气血有余，宜多运动宣泄、忌情绪积压与饮食过量。"
    else:
        out["体质"] = "日主中和，体质较平衡，注意随季节调整作息即可。"
    # 忌神冲刑
    mz = fp.month.zhi
    dzz = fp.day.zhi
    risks = []
    for w in pattern.jishen:
        if power.percent.get(w, 0) >= 25:
            risks.append(f"忌神{w}当权，留意{WUXING_ORGAN[w]}")
    if risks:
        out["重点提示"] = "；".join(risks)
    out["养生方向"] = f"取用神「{pattern.yongshen}」之气：宜{WUXING_DIRECTION[pattern.yongshen]}"
    if pattern.tiaohou:
        out["调候"] = f"命局需「{pattern.tiaohou}」调候，饮食起居宜偏{pattern.tiaohou}性。"
    return out


# --------------------------------------------------------------------------- #
# 六亲 / 子女 / 学业
# --------------------------------------------------------------------------- #
def family(fp, pattern, power) -> dict:
    out = {}
    y, m, d, h = fp.pillars
    out["宫位"] = (f"年柱{y.name}主祖上根基与外缘；月柱{m.name}主父母兄弟与事业环境；"
                   f"日柱{d.name}主自身与配偶；时柱{h.name}主子女与晚运。")
    # 印星=母，财星=父（男命）
    dw = fp.day.gan_wuxing
    yin_pct = power.percent.get(sheng_wo(dw), 0.0)
    cai_pct = power.percent.get(ke(dw), 0.0)
    out["父母"] = (f"印星（母）{yin_pct:.1f}%、财星（父）{cai_pct:.1f}%："
                   + ("得长辈荫助，宜多亲近。" if yin_pct >= 18 else
                      "长辈助力有限，宜自立。" if yin_pct <= 8 else
                      "父母缘分中平。"))
    # 兄弟
    bi = power.percent.get(dw, 0.0)
    out["兄弟同辈"] = ("比劫旺，手足同辈往来多、竞争亦多，宜明算账。"
                       if bi >= 30 else
                       "比劫弱，同辈助力不多，凡事靠自己。" if bi <= 10 else
                       "同辈缘中平，互助互利。")
    return out


def children(fp, pattern, power, strength) -> dict:
    dw = fp.day.gan_wuxing
    star = ke_wo(dw) if fp.gender == "男" else sheng(dw)
    name = "官杀" if fp.gender == "男" else "食伤"
    pct = power.percent.get(star, 0.0)
    out = {}
    out["子女星"] = f"{'男' if fp.gender == '男' else '女'}命以{name}（{star}）为子女，占 {pct:.1f}%"
    hz = fp.hour.zhi
    out["子女宫"] = f"时支{hz}，藏干{''.join(ZANGGAN[hz])}"
    if pct <= 8:
        out["倾向"] = "子女星弱，子女缘较淡或得子较晚，宜早作规划、重质不重量。"
    elif pct >= 28:
        out["倾向"] = "子女星旺，子女缘分厚，但须防管束过度或为子女操劳。"
    else:
        out["倾向"] = "子女星中和，子女顺遂可期。"
    out["时支状态"] = changsheng_note(fp, hz)
    out["建议"] = ("子女之事以时柱为重：时柱喜用神到位之年，多有添丁、子女升学等喜事；"
                   "时柱受冲刑则宜多关心子女起居与身心。")
    return out


def changsheng_note(fp, zhi: str) -> str:
    """时支相对日干的十二长生状态（子女宫旺衰参考）。"""
    return f"日干{fp.day.gan}临{zhi}为「{changsheng(fp.day.gan, zhi)}」"


def study(fp, pattern, power) -> dict:
    dw = fp.day.gan_wuxing
    yin = power.percent.get(sheng_wo(dw), 0.0)
    shi = power.percent.get(sheng(dw), 0.0)
    guan = power.percent.get(ke_wo(dw), 0.0)
    out = {"印星": f"{yin:.1f}%", "食伤": f"{shi:.1f}%", "官杀": f"{guan:.1f}%"}
    score = yin * 0.5 + shi * 0.3 + guan * 0.2
    if score >= 30:
        out["结论"] = "印食官相生，学业根基好，宜深造、考资格、走专业路线。"
    elif score >= 18:
        out["结论"] = "学业中上，靠自律与积累见效，宜早定专业方向。"
    else:
        out["结论"] = "文书印星不显，宜以技能、实操取胜，不必强求学历路线。"
    from .shensha import find_shensha
    ss = find_shensha(fp)
    if ss.by_name("文昌贵人"):
        out["加成"] = "命带文昌，考试文书易得力。"
    if ss.by_name("国印贵人"):
        out["加成2"] = "命带国印，利公职、名誉与文书之贵。"
    return out


# --------------------------------------------------------------------------- #
# 开运建议
# --------------------------------------------------------------------------- #
def advice(fp, pattern, power) -> dict:
    yong = pattern.yongshen
    nums = {"木": "3、8", "火": "2、7", "土": "5、0", "金": "4、9", "水": "1、6"}
    return {
        "喜用五行": f"{yong}（喜：{'、'.join(pattern.xishen) or '无'}；"
                    f"忌：{'、'.join(pattern.jishen) or '无'}）",
        "方位": f"{WUXING_DIRECTION[yong]}（次选 "
                f"{'、'.join(WUXING_DIRECTION[w] for w in pattern.xishen[:2]) or '—'}）",
        "颜色": f"{WUXING_COLOR[yong]}（衣饰、居家、办公色调）",
        "行业": WUXING_CAREER[yong],
        "数字": nums[yong],
        "季节": f"{WUXING_SEASON[yong]}为得力之时，重大决策宜择此季",
        "饮食起居": _life_advice(yong),
        "合作宜忌": _partner_advice(fp, pattern, power),
        "行运要点": (f"行运逢{yong}、{'、'.join(pattern.xishen) or yong}之地，"
                     f"宜进取、扩张、签约；逢{'、'.join(pattern.jishen) or '忌神'}之地，"
                     "宜守成、稳健、忌大额投资与担保。"),
    }


def _life_advice(yong: str) -> str:
    m = {
        "木": "宜早起、多接触草木绿意，作息顺应春生之气；多舒展筋骨、少久坐。",
        "火": "宜见阳光、多运动出汗，作息忌熬夜；冬季注意保暖助阳。",
        "土": "宜规律饮食、定时作息，多接地气（散步、登山）；忌思虑过度伤脾。",
        "金": "宜呼吸吐纳、清肺气，居所通风；忌烟尘与久处闷室。",
        "水": "宜早睡养肾、多饮水、适度游泳；忌久坐憋尿与纵欲耗精。",
    }
    return m[yong]


def _partner_advice(fp, pattern, power) -> str:
    dw = fp.day.gan_wuxing
    tips = []
    if power.percent.get(dw, 0) >= 30:
        tips.append("比劫重：合伙须先立字据、分清权责，忌口头之约。")
    if power.percent.get(ke(dw), 0) >= 28 and fp.day.gan and power.percent.get(dw, 0) < 18:
        tips.append("财重身轻：宜借力合作、忌独自扛盘。")
    if not tips:
        tips.append("合作宜择用神五行之人（"
                    + WUXING_DIRECTION[pattern.yongshen] + "生长或行业对口者）为伴。")
    return " ".join(tips)


# --------------------------------------------------------------------------- #
# 流年断语
# --------------------------------------------------------------------------- #
def yearly_forecast(chart, year: int) -> dict:
    """某年运势要点（结合大运与命局）。"""
    from .fortune import liunian_of
    p = chart.pattern
    lines = []
    dy = None
    for d in chart.dayun:
        if d.start_year <= year <= d.end_year:
            dy = d
            break
    ln = liunian_of(chart.four_pillars, year, p, dy)
    lines.append(f"流年 {ln.name}（{ln.year}，{ln.age:.0f} 岁），年干十神为{ln.shishen}，"
                 f"年支本气为{ln.zhi_shishen}。")
    if dy:
        lines.append(f"正行 {dy.name} 大运（{dy.shishen}），大运评分 {dy.score:+.2f}。")
    for t in ln.tags:
        lines.append(t + "。")
    if ln.relations:
        lines.append("与命局关系：" + "；".join(ln.relations[:4]) + "。")
    if ln.shensha:
        lines.append("流年神煞：" + "、".join(f"{n}（{t}）" for n, t in ln.shensha) + "。")
    # 用神到位与否
    pct = chart.power.percent
    if p.yongshen in pct and pct[p.yongshen] < 12:
        lines.append(f"原局用神「{p.yongshen}」气弱，逢其流年大运最易见起色。")
    # 吉凶建议
    if dy and dy.score >= 0.8:
        lines.append("大运得力：宜主动进取、拓展、置产与签约。")
    elif dy and dy.score <= -0.8:
        lines.append("大运受制：宜守成、稳健、忌大额投资与为人担保。")
    return {"年份": year, "流年": ln.name, "十神": ln.shishen,
            "大运": dy.name if dy else None, "要点": lines,
            "神煞": [f"{n}({t})" for n, t in ln.shensha]}


# --------------------------------------------------------------------------- #
# 汇总
# --------------------------------------------------------------------------- #
def full_analysis(chart) -> dict:
    """汇总全部分析模块（chart 为 :class:`bazi.chart.BaziChart`）。"""
    fp, p, power, st = chart.four_pillars, chart.pattern, chart.power, chart.strength
    return {
        "基本信息": chart.basic_info(),
        "四柱": fp.to_dict(),
        "五行力量": power.percent,
        "十神分布": chart.shishen_distribution(),
        "格局用神": p.to_dict(),
        "旺衰": st,
        "神煞": chart.shensha.to_dict(),
        "性格": personality(fp, p, power, st),
        "事业": career(fp, p, power, st),
        "财运": wealth(fp, p, power, st),
        "婚姻": marriage(fp, p, power, st),
        "健康": health(fp, p, power, st),
        "六亲": family(fp, p, power),
        "子女": children(fp, p, power, st),
        "学业": study(fp, p, power),
        "开运建议": advice(fp, p, power),
        "大运": [str(d) for d in chart.dayun],
    }
