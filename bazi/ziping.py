"""《子平真诠》格局成败与相神判定。

与 pattern.py 的区别
--------------------
``determine_pattern`` 解决"这是什么格、扶抑用神取哪个五行"；本模块解决沈孝瞻
《子平真诠》的另一层问题——**这个格是成是败、有没有相神护卫**：

* **用神**（此篇专指月令格局之神，非扶抑用神）：月令所藏、定格的那个十神。
* **相神**：辅格成格之神。正官格喜印（官印相生）或财（财生官）；食神格喜财；
  印格喜官杀；财格喜食伤（食伤生财）或官（财生官）……
* **成格**：格神透干/得根、不被冲克，且有相神。
* **败格**：格神被克制之神当头（如正官见伤官克官、正财见比劫夺财），又无印/
  食伤等相神解救，或格神不透、被月令/日支冲破。
* **成中有败 / 败中有成**：成格要素与破格要素并存，看谁有力。

只做正格（八格）评判；专旺/从/化等变格不在此篇范围，返回 kind 提示交回主格局。
全部为可复现的规则判断，不引网络、不断流年休咎。
"""

from __future__ import annotations

# 每个正格 -> (该格之神所属十神组, 生护它的"相神"十神组, 破它的"忌"十神组)
# 十神组沿用 constants.SHISHEN_GROUP：比劫/食伤/财星/官杀/印星
_GE_RULES: dict[str, dict] = {
    # 正官：官印相生（印化官）或财生官；忌伤官克官、七杀混杂
    "正官格": {"ge": "官杀", "xiang": ("印星", "财星"), "po": ("食伤",)},
    "七杀格": {"ge": "官杀", "xiang": ("印星", "食伤"), "po": ("财星",)},  # 杀印相生/食神制杀；忌财党杀
    "正印格": {"ge": "印星", "xiang": ("官杀",), "po": ("财星",)},          # 官印相生；忌财坏印
    "偏印格": {"ge": "印星", "xiang": ("官杀", "比劫"), "po": ("财星",)},
    "正财格": {"ge": "财星", "xiang": ("官杀", "食伤"), "po": ("比劫",)},   # 财生官/食伤生财；忌比劫夺财
    "偏财格": {"ge": "财星", "xiang": ("官杀", "食伤"), "po": ("比劫",)},
    "食神格": {"ge": "食伤", "xiang": ("财星",), "po": ("印星",)},          # 食神生财；忌偏印夺食
    "伤官格": {"ge": "食伤", "xiang": ("财星", "印星"), "po": ("官杀",)},   # 伤官生财/印制伤；伤官见官为祸
}


def _groups_present(fp) -> set[str]:
    """统计天干透出 + 地支藏干的十神组（是否在命局出现）。"""
    from .constants import SHISHEN_GROUP, shishen
    dg = fp.day.gan
    seen: set[str] = set()
    for p in fp.pillars:
        seen.add(SHISHEN_GROUP[shishen(dg, p.gan)])      # 天干
        for g in p.zanggan:                              # 地支藏干
            seen.add(SHISHEN_GROUP[shishen(dg, g)])
    return seen


def _ge_shen_shishen(fp) -> tuple[str, str]:
    """取定格之神（月令本气透干优先）相对日主的 (十神组, 天干)。"""
    from .constants import SHISHEN_GROUP, shishen
    from .pattern import _tou_gan
    dg = fp.day.gan
    chosen = None
    for g in fp.month.zanggan:
        if g in _tou_gan(fp):
            chosen = g
            break
    chosen = chosen or fp.month.zanggan[0]
    return SHISHEN_GROUP[shishen(dg, chosen)], chosen


def _tou_groups(fp) -> set[str]:
    """天干透出（年月日时）的十神组——透干才算明见、有力。"""
    from .constants import SHISHEN_GROUP, shishen
    dg = fp.day.gan
    # 透干只取年/月/时三干；日柱是日主自己（shishen=比肩），计入会让比劫永远"透出"
    # 注意 pillars 顺序是 (年,月,日,时)，不能用 [:3]（那会误取日、漏时）
    return {SHISHEN_GROUP[shishen(dg, p.gan)]
            for p in (fp.year, fp.month, fp.hour)}


def geju_cheng_bai(chart) -> dict:
    """判《子平真诠》格局成败。

    返回::

        {"ge":"伤官格","kind":"正格","ge_shen":"食伤","xiang":[...],"po":[...],
         "tou":True,"verdict":"成中有败"|"成格"|"败格","score":-2~+2,"reason":"..."}
    变格（专旺/从/化/禄刃）返回 kind 标注、verdict="不属正格成败"，不硬判。
    """
    fp, pat = chart.four_pillars, chart.pattern
    from .pattern import _tou_gan
    if pat.kind != "正格" or pat.name not in _GE_RULES:
        return {"ge": pat.name, "kind": pat.kind,
                "verdict": "不属正格成败（变格/禄刃另有专论）",
                "score": 0, "reason": "", "xiang": [], "po": []}

    rule = _GE_RULES[pat.name]
    present = _groups_present(fp)      # 全盘（含藏干）有无
    tou_groups = _tou_groups(fp)       # 仅天干透出者
    ge_group, ge_gan = _ge_shen_shishen(fp)

    # 格神是否透干（只看年/月/时三干，与 _tou_groups 口径一致）
    tou = ge_gan in _tou_gan(fp)

    # 相神：命局出现即可；破格神：必须透干才算"明破"（藏支只记隐患，不重罚）
    xiang = [x for x in rule["xiang"] if x in present]
    po_tou = [x for x in rule["po"] if x in tou_groups]
    po_hidden = [x for x in rule["po"] if x in present and x not in tou_groups]

    score = 0
    why = []
    if tou:
        score += 1; why.append(f"格神「{ge_gan}」透干，取用真切")
    else:
        why.append(f"格神「{ge_gan}」仅藏地支不透，力弱")
    if xiang:
        score += len(xiang); why.append("有相神「" + "、".join(xiang) + "」辅格")
    if po_tou:
        score -= len(po_tou); why.append("破格之神「" + "、".join(po_tou) + "」透干明克")
    if po_hidden:
        why.append("忌神「" + "、".join(po_hidden) + "」仅藏支，隐患而未明破")
    from .constants import relations as _rel
    if any("六冲" in _rel(fp.month.zhi, p.zhi) for p in (fp.year, fp.day, fp.hour)):
        score -= 1; why.append("月令提纲逢冲，格根动摇")

    # 判定：明破(po_tou)为主轴；相神数压过明破才叫"败中有成"
    if not po_tou and score >= 2:
        verdict = "成格"
    elif po_tou and len(xiang) >= len(po_tou) and score >= 1:
        verdict = "败中有成（忌神得制）"
    elif po_tou and score <= 0:
        verdict = "败格"
    elif po_tou:
        verdict = "成中有败"
    elif score >= 1:
        verdict = "成格（相神稍弱）"
    else:
        verdict = "成中有败"

    return {"ge": pat.name, "kind": "正格", "ge_shen": ge_group,
            "xiang": xiang, "po": po_tou + po_hidden, "tou": tou,
            "verdict": verdict, "score": score, "reason": "；".join(why)}


# --------------------------------------------------------------------------- #
# 官杀混杂
# --------------------------------------------------------------------------- #
def guan_sha_hun_za(chart) -> dict:
    """正官、七杀是否同时明透天干而混杂，及有无去留（合/制）解救。

    《子平真诠·论官杀混杂》：官杀并见为混，主事业、心性多歧、贵气不清；
    若一者被合去或被食神/伤官/印星制化，则"去留有情"反不为害。

    只判天干（地支藏干官杀不算明混）。返回::

        {"hun":bool,"zheng":bool,"qi":bool,"rescue":"合去七杀"|"食神制杀"|...,"note":str}
    """
    from .constants import shishen
    fp = chart.four_pillars
    dg = fp.day.gan
    tou = [shishen(dg, p.gan) for p in fp.pillars]
    has_zheng, has_qi = "正官" in tou, "七杀" in tou
    if not (has_zheng and has_qi):
        return {"hun": False, "zheng": has_zheng, "qi": has_qi,
                "rescue": "", "note": "官杀未并透，不杂"}

    # 找官、杀分别在哪个天干，看是否被相邻天干五合"合去"
    from .constants import GAN_HE, TIANGAN
    rescue = []
    gans = [p.gan for p in fp.pillars]
    for idx, ss in enumerate(tou):
        if ss not in ("正官", "七杀"):
            continue
        for j, og in enumerate(gans):
            if j == idx:
                continue
            key = frozenset((TIANGAN.index(gans[idx]), TIANGAN.index(og)))
            if key in GAN_HE:
                rescue.append(f"{'七杀' if ss=='七杀' else '正官'}与{og}合去")
    # 食神制杀 / 伤官驾杀：食伤透干可制七杀
    if has_qi and any(s in tou for s in ("食神", "伤官")):
        rescue.append("食伤透干制杀")
    # 印化：偏印/正印透干化杀
    if has_qi and any(s in tou for s in ("偏印", "正印")):
        rescue.append("印星化杀")

    if rescue:
        return {"hun": True, "zheng": True, "qi": True,
                "rescue": "；".join(dict.fromkeys(rescue)),
                "note": "官杀并透本杂，幸有去留制化，贵气转清"}
    return {"hun": True, "zheng": True, "qi": True, "rescue": "",
            "note": "官杀并透无制化，为真混杂，主心性多歧、贵气不清、易犯小人"}


# --------------------------------------------------------------------------- #
# 真从 / 假从
# --------------------------------------------------------------------------- #
def cong_quality(chart) -> dict:
    """对已判为"从格"的命局细分真从、假从；非从格返回空判定。

    《子平真诠·论从格》：日主极弱、全无根气印生，所从之神成势 → **真从**，
    格局清纯、运顺所从则大富贵；日主尚有一点根苗（地支余气通根）或天干
    微露印比而无力 → **假从**，格局有瑕，逢根气之运易反复。

    纯规则：看日主在四支藏干有无通根、天干有无印比、生扶力量占比。
    """
    pat, fp, st = chart.pattern, chart.four_pillars, chart.strength
    if pat.kind != "从格":
        return {"is_cong": False, "quality": "", "reason": "非从格"}

    dw = fp.day.gan_wuxing
    # 日主同类（比劫）与生我（印）的五行力量占比
    pct = chart.power.percent
    from .constants import sheng_wo
    yin_wx = sheng_wo(dw)
    root_pct = pct.get(dw, 0.0) + pct.get(yin_wx, 0.0)

    # 通根：年/日/时三支藏干中，按藏干权重累计日主本气（比劫之根）。
    # ponytail: 用本气0.6/中气0.3/余气0.1权重，比"存在即根"更贴近通根深浅；
    # 阈值0.5≈一支中气根，真从要求三支合计连半个中气根都没有。
    from .constants import GAN_WUXING, TIANGAN, ZANGGAN_WEIGHT
    root_w = 0.0
    root_detail = []
    for p, lab in zip(fp.pillars, "年月日时"):
        if lab == "月":
            continue
        for g, w in zip(p.zanggan, ZANGGAN_WEIGHT[p.zhi]):
            if GAN_WUXING[TIANGAN.index(g)] == dw:
                root_w += w
                root_detail.append(f"{lab}支{g}({w})")
    # 天干印比透出（除日主）
    from .constants import shishen, SHISHEN_GROUP
    tou_yinbi = []
    for p, lab in zip(fp.pillars, "年月日时"):
        if lab == "日":
            continue
        if SHISHEN_GROUP[shishen(fp.day.gan, p.gan)] in ("印星", "比劫"):
            tou_yinbi.append(f"{lab}干{p.gan}")

    # 真从：年日时三支无实质根(权重<0.5)、天干无印比、根气五行合计极低
    if root_w < 0.5 and not tou_yinbi and root_pct < 10:
        return {"is_cong": True, "quality": "真从",
                "root_pct": round(root_pct, 1),
                "reason": f"日主无根无印，生扶之气仅{root_pct:.1f}%，所从成势，格清"}
    # 假从：有微根或印比露而无力
    bits = []
    if root_w >= 0.5:
        bits.append(f"地支余气通根(权重{root_w:.1f}：" + "、".join(root_detail) + ")")
    if tou_yinbi:
        bits.append("印比露干(" + "、".join(tou_yinbi) + ")")
    if not bits:
        bits.append(f"生扶之气{root_pct:.1f}%偏高")
    return {"is_cong": True, "quality": "假从",
            "root_pct": round(root_pct, 1),
            "reason": "日主尚有" + "、".join(bits) + "，不能尽从，格有瑕疵，逢根气之运多反复"}


# --------------------------------------------------------------------------- #
# 专旺纯净度 / 备选格局（多格局并行）
# --------------------------------------------------------------------------- #
# 五行 -> 专旺格名；破格关系：财(我克)、官杀(克我)透干即不纯
_ZW_NAME = {"木": "曲直格", "火": "炎上格", "土": "稼穑格",
            "金": "从革格", "水": "润下格"}


def zhuanwang_purity(chart) -> dict:
    """专旺（一行独旺）纯净度诊断。

    专旺格要求日主本气极旺、印比成群且**无财官透干破格**。实践中同一命局
    常被两派争论（如润下格透丁火财星，严格派认为破局不入，宽松派仍取）。
    本函数只摆事实、不替流派拍板：

    * ``eligible``  气势上够不够格（身极旺 score>=72 且本气+印 >= 65%、得令）
    * ``flaws``     破格瑕疵（财/官杀透干、本气被冲等）
    * ``strict_ok`` 严格派（要求无财官透干）认不认
    * ``loose_ok``  宽松派认不认
    """
    from .constants import (SHISHEN_GROUP, shishen,
                            relations as _rel)
    fp, st, pw = chart.four_pillars, chart.strength, chart.power.percent
    dw = fp.day.gan_wuxing
    from .constants import sheng_wo
    yin = sheng_wo(dw)
    core = pw.get(dw, 0) + pw.get(yin, 0)      # 本气 + 印

    de_ling = st["de_ling"].startswith("得令")
    eligible = st["score"] >= 72 and de_ling and core >= 65

    flaws = []
    # 天干透出财 / 官杀？
    for p, lab in zip(fp.pillars, "年月日时"):
        if lab == "日":
            continue
        grp = SHISHEN_GROUP[shishen(fp.day.gan, p.gan)]
        if grp == "财星":
            flaws.append(f"财星「{p.gan}」透{lab}干")
        elif grp == "官杀":
            flaws.append(f"官杀「{p.gan}」透{lab}干")
    # 本气支被冲
    for p, lab in zip(fp.pillars, "年月日时"):
        if p.zhi_wuxing == dw and lab != "日":
            if "六冲" in _rel(p.zhi, fp.day.zhi):
                flaws.append(f"{lab}支本气逢冲")

    strict_ok = eligible and not flaws
    loose_ok = eligible                        # 宽松派：气势够即可，透财官作瑕疵看
    return {
        "ge": _ZW_NAME[dw], "wuxing": dw, "core_pct": round(core, 1),
        "score": st["score"], "eligible": eligible, "flaws": flaws,
        "strict_ok": strict_ok, "loose_ok": loose_ok,
    }


def alternative_patterns(chart) -> list[dict]:
    """多格局并行：返回主格局之外、有争议的备选格局（当前只列专旺候选）。

    主格局（扶抑/从/化，``chart.pattern``）永远保留不动；这里只附加"另一派
    可能怎么取"，供命书并列展示、不互相覆盖。无备选时返回空列表。
    """
    out = []
    zw = zhuanwang_purity(chart)
    if zw["eligible"]:
        if chart.pattern.kind == "专旺格":
            # 主判定已取专旺：反报扶抑视角下的破格争议（若有瑕疵）
            if zw["flaws"]:
                out.append({"alt": "按正格（扶抑）另论",
                            "reason": "主局已取" + zw["ge"] + "，但严格派以"
                                      + "、".join(zw["flaws"]) + "为破格，主张不取专旺",
                            "strict_side": "不取专旺"})
        else:
            # 主判定是正格/其他：报专旺候选
            out.append({"alt": zw["ge"] + "（专旺）",
                        "strict_ok": zw["strict_ok"], "loose_ok": zw["loose_ok"],
                        "reason": "本气+印达" + f"{zw['core_pct']:.0f}%、身极旺，宽松派可取专旺"
                                  + ("；但" + "、".join(zw["flaws"]) + "，严格派不取" if zw["flaws"]
                                     else "；无财官透干破格，两派皆可")})
    return out


