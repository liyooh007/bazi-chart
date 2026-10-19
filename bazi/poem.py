"""命理诗生成：据八字实算结果作七言八句律诗（前途 / 命运 / 好坏），逐句作注。

设计原则
========
* **切命不切空**：每句都来自命盘实算要素——日干、月令格局、日主旺衰、
  用神五行、寒暖调候、关键神煞、大运早中晚走势、命局综合评分；
  每句附 ``note``，说明它对应命盘的哪一处，可核查。
* **纯标准库、确定性**：默认同一八字每次得到同一首诗（以四柱干支为种子），
  传 ``variant`` 可取其它成稿。
* **诗体**：七言八句，二、四、六、八句押韵（按命局评级选韵部）。

成句库：奇句在本文件 :data:`ODD_LINES`，押韵句在
:mod:`bazi._poem_lines`；:func:`verify_library` 对全部成句做
「必为 7 字 + 偶句韵脚合规」的校验。
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass

from .constants import sheng, ke, sheng_wo, ke_wo, WUXING_DIRECTION
from ._poem_lines import EVEN, CONDS

__all__ = ["PoemLine", "PoemResult", "chart_rating", "build_context",
           "destiny_poem", "verify_library", "GRADES", "RHYME"]

GRADES = (
    (85, "上上", "气象清和，福禄深厚"),
    (75, "上中", "根基稳实，有为有守"),
    (65, "中上", "先难后易，自成家门"),
    (55, "中平", "平稳中求，勤能补拙"),
    (45, "中下", "多劳少逸，守正待时"),
    (30, "下中", "起伏较大，宜借运而行"),
    (0, "下下", "磨砺重重，积德修心"),
)

RHYME = {
    # 人辰辙（en/in/un/ün）
    "A": set("新春身人尘臣津伦辰臻匀巡仁嗔元神真亲奔纯本"),
    # 庚青（eng/ing）
    "B": set("成明程平情行声名清荣盈宁生晴争更"),
    # 东钟（ong/iong）
    "C": set("通功丰中风同隆红"),
    # 一七辙（i/ü 及 zhi/chi/shi 类空韵）
    "D": set("时迟持期宜奇危移痴"),
    # 由求辙（ou/iu）
    "E": set("悠流秋求收舟休酬游头油筹谋由忧稠幽遒留修"),
}

GAN_VERSE = {
    "甲": "甲木参天志不群", "乙": "乙木藤萝善屈伸",
    "丙": "丙火当空万象新", "丁": "丁火灯窗夜向晨",
    "戊": "戊土高山重信诚", "己": "己土田园善养人",
    "庚": "庚金横剑世途巡", "辛": "辛金珠玉自无尘",
    "壬": "壬水奔流智绝伦", "癸": "癸水涵珠润物匀",
}
GAN_VERSE_NOTE = {
    "甲": "日主甲木，如参天之木，正直向上",
    "乙": "日主乙木，如藤萝之木，柔韧善攀",
    "丙": "日主丙火，如太阳当空，磊落热情",
    "丁": "日主丁火，如灯烛之火，细致温煦",
    "戊": "日主戊土，如高山厚土，可靠守成",
    "己": "日主己土，如田园之土，含蓄务实",
    "庚": "日主庚金，如刀剑之金，刚毅果决",
    "辛": "日主辛金，如珠玉之金，精致敏锐",
    "壬": "日主壬水，如江河之水，聪敏善变",
    "癸": "日主癸水，如雨露之水，灵秀内细",
}

PATTERN_PHRASE = {
    "正官格": "官印清奇", "七杀格": "杀印相生", "正财格": "财星有气",
    "偏财格": "偏财倜傥", "食神格": "食神吐秀", "伤官格": "伤官泄秀",
    "正印格": "印绶护身", "偏印格": "偏印多谋", "建禄格": "建禄自强",
    "月刃格": "羊刃驾杀", "从财格": "从财顺势", "从杀格": "从杀借威",
    "从儿格": "从儿泄秀", "从势格": "从势随流",
    "曲直格": "曲直仁寿", "炎上格": "炎上文明", "稼穑格": "稼穑厚重",
    "从革格": "从革坚刚", "润下格": "润下通达",
}


@dataclass
class PoemLine:
    text: str
    note: str
    slot: str


@dataclass
class PoemResult:
    title: str
    lines: list[PoemLine]
    poem: str
    grade: str
    grade_comment: str
    score: float
    score_detail: dict
    rhyme: str
    summary: str

    def to_dict(self) -> dict:
        return {
            "标题": self.title, "命理诗": self.poem, "评级": self.grade,
            "评级说明": self.grade_comment, "综合评分": round(self.score, 1),
            "韵部": self.rhyme, "评分解项": self.score_detail,
            "逐句注解": [{"句": x.text, "对应命盘": x.note} for x in self.lines],
            "总断": self.summary,
        }


# --------------------------------------------------------------------------- #
# 评分 & 上下文
# --------------------------------------------------------------------------- #
def _avg(dys, sl):
    return round(sum(d.score for d in dys[sl]) / max(1, len(dys[sl])), 2)


def chart_rating(chart) -> dict:
    """命局综合评分（0–100）：流通/用神/格局/调候/神煞/行运六项。"""
    fp, p, power, dys = (chart.four_pillars, chart.pattern, chart.power, chart.dayun)
    yong = p.yongshen or "木"
    d: dict[str, float] = {}
    vals = list(power.percent.values())
    dev = sum(abs(v - 20.0) for v in vals) / 5.0
    d["五行流通"] = round(max(0.0, min(100.0, 100 - dev * 2.2)) * 0.20, 1)
    ys_src = []
    for pillar, label in zip(fp.pillars, "年月日时"):
        if pillar.gan_wuxing == yong:
            ys_src.append(f"{label}干")
        if pillar.zhi_wuxing == yong:
            ys_src.append(f"{label}支")
    ys = 6.0 * len(ys_src)
    if any(x in ys_src for x in ("月干", "月支")):
        ys += 4                      # 用神得月令之地，最贵
    if power.percent.get(yong, 0) >= 18:
        ys += 3
    d["用神有力"] = round(min(25, ys), 1)
    if p.kind in ("专旺格", "从格", "化气格"):
        ge = 15 if power.ranked()[0][1] >= 45 else 10
    else:
        ge = 16 if p.name in {"正官格", "正印格", "正财格", "食神格", "建禄格"} \
            else 13 if p.name in {"偏财格", "七杀格", "月刃格"} else 11
        if power.missing():
            ge -= 2                  # 五行有缺，格局难纯
        if 40 <= chart.strength["score"] <= 60:
            ge += 2                  # 中和为贵
    # 格局项实现上限 18，标称 20：等比放大到 20 分量纲
    d["格局清浊"] = round(float(ge) * 20.0 / 18.0, 1)
    # 调候：先看《穷通宝鉴》逐日干×月令的首要调候用神在命局是否得力；
    # 该五行透出/坐支得地即暖燥寒润得宜（满分），仅力量够 8% 给半分，缺失最低分。
    from .qiongtong import qiongtong_wuxing
    qw = qiongtong_wuxing(fp.day.gan, fp.month.zhi)
    if qw:
        pw = qw["primary"]
        rooted = any(pl.gan_wuxing == pw or pl.zhi_wuxing == pw for pl in fp.pillars)
        tiaohou = 10.0 if rooted else (7.0 if power.percent.get(pw, 0) >= 8 else 4.0)
    else:
        tiaohou = 10.0 if (not p.tiaohou or power.percent.get(p.tiaohou, 0) >= 8) else 4.0
    d["调候寒暖"] = tiaohou
    d["神煞吉凶"] = round(max(0.0, min(10.0, 5 + chart.shensha.score * 0.8)), 1)
    yun = (_avg(dys, slice(0, 3)) + _avg(dys, slice(3, 6)) + _avg(dys, slice(6, 10))) / 3
    d["行运辅成"] = round(max(0.0, min(15.0, 7.5 + yun * 2.6)), 1)
    total = round(min(100.0, sum(d.values())), 1)
    grade, comment = next((g[1], g[2]) for g in GRADES if total >= g[0])
    return {"总分": total, "分项": d, "评级": grade, "评级说明": comment,
            "大运": {"早年": _avg(dys, slice(0, 3)), "中年": _avg(dys, slice(3, 6)),
                     "晚年": _avg(dys, slice(6, 10))}}


def build_context(chart) -> dict:
    """从命盘抽取作诗与评分所需的要素。"""
    fp, p, power, st = chart.four_pillars, chart.pattern, chart.power, chart.strength
    dg, dw = fp.day.gan, fp.day.gan_wuxing
    ss = {s.name for s in chart.shensha.items}
    yong = p.yongshen or "木"
    rating = chart_rating(chart)
    yong_sources = []
    for pillar, label in zip(fp.pillars, "年月日时"):
        if pillar.gan_wuxing == yong:
            yong_sources.append(f"{label}干")
        if pillar.zhi_wuxing == yong:
            yong_sources.append(f"{label}支")
    groups = {
        "比劫": power.percent.get(dw, 0), "食伤": power.percent.get(sheng(dw), 0),
        "财星": power.percent.get(ke(dw), 0), "官杀": power.percent.get(ke_wo(dw), 0),
        "印星": power.percent.get(sheng_wo(dw), 0),
    }
    return {
        "gan": dg, "dw": dw, "pattern": p.name, "kind": p.kind,
        "phrase": PATTERN_PHRASE.get(p.name, p.name.replace("格", "")),
        "score": st["score"], "de_ling": st["de_ling"],
        "strong_word": "身强" if st["score"] >= 55 else "身弱" if st["score"] <= 45 else "身平",
        "yong": yong, "xi": p.xishen[0] if p.xishen else yong,
        "tiao": p.tiaohou, "cold": fp.month.zhi in "亥子丑",
        "hot": fp.month.zhi in "巳午未", "lead": max(groups, key=groups.get),
        "missing": power.missing(), "tianyi": "天乙贵人" in ss,
        "noble": bool({"天乙贵人", "天德贵人", "月德贵人"} & ss),
        "wencang": "文昌贵人" in ss, "blade": "羊刃" in ss,
        "flower": bool({"桃花", "红艳煞"} & ss), "huagai": "华盖" in ss,
        "horse": "驿马" in ss, "month_zhi": fp.month.zhi,
        "yun_early": rating["大运"]["早年"], "yun_mid": rating["大运"]["中年"],
        "yun_late": rating["大运"]["晚年"],
        "yong_sources": yong_sources, "rating": rating,
        "total": rating["总分"], "grade": rating["评级"],
        "gender": fp.gender, "bazi": fp.ganzhi,
    }


# --------------------------------------------------------------------------- #
# 奇句（不押韵）
# --------------------------------------------------------------------------- #
def _phrase(c, tail3):
    return c["phrase"] + tail3


def _pattern7(c, tail):
    """把 2 字或 4 字格局短语稳定补成 7 字句。

    4 字短语（官印清奇）→ 「<4字>＋<3字尾>」
    2 字短语（劫财）    → 「格成<2字>＋<3字尾>」
    """
    ph = c["phrase"]
    if len(ph) == 4:
        return ph + tail            # 4 + 3 = 7
    return "格成" + ph + tail        # 2 + 2 + 3 = 7


def _biange_line(c):
    return _pattern7(c, "势绝伦")


ODD_LINES = {
    1: [(lambda c: True,
         lambda c: GAN_VERSE[c["gan"]],
         lambda c: GAN_VERSE_NOTE[c["gan"]])],
    3: [
        (lambda c: c["kind"] == "专旺格",
         lambda c: _pattern7(c, "势独尊"),
         lambda c: f"{c['pattern']}（专旺）：一行独旺、气势专一，贵在顺其旺势、忌逆势强克"),
        (lambda c: c["kind"] == "正格" and c["score"] >= 55,
         lambda c: _pattern7(c, "身气稳"),
         lambda c: f"{c['pattern']}，日主 {c['score']:.0f} 分身强，月令提纲有力"),
        (lambda c: c["kind"] == "正格" and c["score"] <= 45,
         lambda c: _pattern7(c, "待扶身"),
         lambda c: f"{c['pattern']}，日主 {c['score']:.0f} 分身弱，宜印比扶身"),
        (lambda c: c["kind"] == "正格" and 45 < c["score"] < 55,
         lambda c: _pattern7(c, "势自匀"),
         lambda c: f"{c['pattern']}，日主 {c['score']:.0f} 分中和，气势较匀"),
        (lambda c: c["kind"] != "正格",
         lambda c: _biange_line(c),
         lambda c: f"成{c['pattern']}（{c['kind']}），气势偏于一方，贵在顺势"),
    ],
    5: [
        (lambda c: c["kind"] == "专旺格",
         lambda c: "顺其旺势泄为珍",
         lambda c: "专旺格喜印比帮扶、食伤顺泄，忌财官逆势；立身宜顺势而为、忌硬碰"),
        (lambda c: c["lead"] == "官杀",
         lambda c: "功名有路凭" + c["yong"] + "引",
         lambda c: f"十神以官杀为主，用神{c['yong']}，宜{WUXING_DIRECTION[c['yong']]}、功名规矩之途"),
        (lambda c: c["lead"] in ("财星", "食伤"),
         lambda c: "经营才艺为生计",
         lambda c: f"十神以{c['lead']}为主，宜凭技艺、经营立身（{c['phrase']}）"),
        (lambda c: c["lead"] == "印星",
         lambda c: "文章学业堪凭信",
         lambda c: "十神以印星为主，宜以学识、名声、专业资格立身"),
        (lambda c: True,
         lambda c: "立身宜取" + c["yong"] + "为用",
         lambda c: f"用神为{c['yong']}，行业、方位、颜色皆宜取{c['yong']}气"),
    ],
    7: [
        (lambda c: c["kind"] == "专旺格",
         lambda c: "逆行财官莫轻亲",
         lambda c: "专旺行运顺食伤、印比则吉，逢财官旺地逆势多阻，行运取舍与正格相反"),
        (lambda c: c["yun_early"] + 0.4 <= c["yun_mid"] and c["yun_late"] >= 0.3,
         lambda c: "中年发迹晚尤昌",
         lambda c: f"大运先抑后扬：早{c['yun_early']:+.1f}/中{c['yun_mid']:+.1f}/晚{c['yun_late']:+.1f}，中年后渐入佳境"),
        (lambda c: c["yun_early"] > c["yun_mid"] + 0.4,
         lambda c: "早年顺意晚宜藏",
         lambda c: f"大运先扬后平：早{c['yun_early']:+.1f}/中{c['yun_mid']:+.1f}/晚{c['yun_late']:+.1f}，宜早积晚守"),
        (lambda c: c["yun_late"] >= 0.8,
         lambda c: "晚景安和福自坚",
         lambda c: f"晚运评分 {c['yun_late']:+.1f} 较佳，晚景安和"),
        (lambda c: True,
         lambda c: "一生起伏平常看",
         lambda c: f"大运早中晚 {c['yun_early']:+.1f}/{c['yun_mid']:+.1f}/{c['yun_late']:+.1f}，起伏有度"),
    ],
}


def _pick_odd(slot, ctx, rng):
    """奇句按"声明顺序 + 条件互斥"取首个满足者（保证不出现与命盘矛盾的句子）。

    变体（``variant``）不作用于奇句：奇句承载日干与格局的硬事实，必须唯一确定。
    """
    for cond, tf, nf in ODD_LINES[slot]:
        if cond(ctx):
            return tf(ctx), nf(ctx)
    raise RuntimeError(f"slot {slot} 无可用奇句")


def _pick_even(slot, ctx, rhyme, rng):
    """偶句：先看特定条件句（可多条备选，按种子择一），无则用 tag=='all' 的默认句。"""
    specific = [e for e in EVEN[slot]
                if rhyme in e[0] and e[1] != "all" and CONDS[e[1]](ctx)]
    default = [e for e in EVEN[slot]
               if rhyme in e[0] and e[1] == "all" and CONDS["all"](ctx)]
    pool = specific or default
    if not pool:
        raise RuntimeError(f"slot {slot} 韵部 {rhyme} 无可用成句")
    _, _, tf, nf = pool[rng.randrange(len(pool))] if len(pool) > 1 else pool[0]
    return tf[rhyme](ctx), nf(ctx)


def _rhyme_for(total: float) -> str:
    """评级选韵：高分用明朗韵（人辰/庚青），中分用平正韵（东钟），
    低分用沉缓韵（一七/由求），使诗的气韵与命局气象相称。"""
    if total >= 80:
        return "A"      # 人辰辙：开朗向上
    if total >= 65:
        return "B"      # 庚青辙：清朗平稳
    if total >= 55:
        return "C"      # 东钟辙：厚重中正
    if total >= 45:
        return "D"      # 一七辙：收敛自持
    return "E"          # 由求辙：沉缓悠长


def _seed_rng(ctx: dict, variant: int) -> random.Random:
    key = f"{ctx['bazi']}|{ctx['gender']}|{variant}".encode()
    return random.Random(int(hashlib.sha256(key).hexdigest()[:12], 16))


def _summary(ctx: dict) -> str:
    y, b, w = ctx["yun_early"], ctx["yun_mid"], ctx["yun_late"]
    trend = ("先抑后扬、晚运较佳" if b >= y and w >= 0.3 else
             "早运较顺、宜早积晚守" if y > b + 0.4 else
             "一生运势起伏较匀")
    plus = []
    if ctx["noble"]:
        plus.append("有贵人德神护佑")
    if ctx["wencang"]:
        plus.append("利文书学业")
    if ctx["blade"]:
        plus.append("性情刚烈宜制")
    if ctx["flower"]:
        plus.append("情缘宜守正")
    if ctx["horse"]:
        plus.append("宜外出发展")
    extra = ("，" + "、".join(plus)) if plus else ""
    return (f"综合 {ctx['total']:.0f} 分，评 {ctx['grade']} 等。"
            f"{ctx['pattern']}、{ctx['strong_word']}，用神在「{ctx['yong']}」{extra}；"
            f"大运{trend}。命示趋向，非为定数——趋吉避凶、修德敬业始终在人。")


def destiny_poem(chart, *, variant: int = 0) -> PoemResult:
    """据命盘生成命理诗（七言八句，二/四/六/八押韵）。

    :param variant: 0=默认成稿；>0 时在符合条件的成句中取另一套
    """
    ctx = build_context(chart)
    rhyme = _rhyme_for(ctx["total"])
    rng = _seed_rng(ctx, variant)
    slot_names = {1: "起·日主", 2: "承·月令", 3: "承·格局", 4: "转·用神",
                  5: "转·前程", 6: "合·神助", 7: "合·行运", 8: "结·总断"}
    lines: list[PoemLine] = []
    for slot in range(1, 9):
        if slot % 2 == 1:
            text, note = _pick_odd(slot, ctx, rng)
        else:
            text, note = _pick_even(slot, ctx, rhyme, rng)
        lines.append(PoemLine(text, note, slot_names[slot]))
    # 校验：全部 7 字
    for ln in lines:
        if len(ln.text) != 7:
            raise RuntimeError(f"诗库成句字数错误（应为 7）：{ln.text!r}")
    title = f"命理诗·{chart.four_pillars.day_gan}日主{ctx['pattern']}"
    body = "\n".join(f"{'　' if i % 2 == 0 else ''}{ln.text}"
                     for i, ln in enumerate(lines))
    grade_c = next(g[2] for g in GRADES if ctx["total"] >= g[0])
    return PoemResult(
        title=title, lines=lines, poem=body, grade=ctx["grade"],
        grade_comment=grade_c, score=ctx["total"],
        score_detail=ctx["rating"]["分项"], rhyme=rhyme,
        summary=_summary(ctx),
    )


def verify_library() -> tuple[int, list[str]]:
    """校验诗库：所有成句 7 字；偶句末字落在所声明韵部。"""
    errs = []
    n = 0
    for gan in GAN_VERSE:
        if len(GAN_VERSE[gan]) != 7:
            errs.append(f"日干句非7字：{GAN_VERSE[gan]}")
        n += 1
    samples = _sample_contexts()
    # 人工补齐 3 字格局短语样本（劫财格等）
    for ph in ("劫财", "化木"):
        c = dict(samples[0]); c["phrase"] = ph; c["kind"] = ("化气格" if ph.startswith("化") else "正格")
        c["pattern"] = ph + "格"
        samples.append(c)
    for ctx in samples:
        rng = random.Random(0)
        for slot in (3, 5, 7):
            for cond, tf, _ in ODD_LINES[slot]:
                if cond(ctx):
                    t = tf(ctx)
                    n += 1
                    if len(t) != 7:
                        errs.append(f"奇句 slot{slot} 非7字：{t!r}")
        for rhyme in "ABCDE":
            for slot in (2, 4, 6, 8):
                for groups, tag, tf, _ in EVEN[slot]:
                    if rhyme in groups and CONDS[tag](ctx):
                        t = tf[rhyme](ctx)
                        n += 1
                        if len(t) != 7:
                            errs.append(f"偶句 slot{slot}/{rhyme} 非7字：{t!r}")
                        if t[-1] not in RHYME[rhyme]:
                            errs.append(f"偶句 slot{slot}/{rhyme} 不押韵：{t!r}（末字 {t[-1]}）")
    return n, errs


def _sample_contexts():
    """覆盖诗库各条件分支的最小上下文样本集。"""
    base = dict(gan="甲", dw="木", pattern="正官格", kind="正格", phrase="官印清奇",
                score=50, de_ling="得令", strong_word="身平", yong="水", xi="木",
                tiao="", cold=False, hot=False, lead="官杀", missing=[],
                tianyi=False, noble=False, wencang=False, blade=False,
                flower=False, huagai=False, horse=False,
                yun_early=0.0, yun_mid=0.5, yun_late=0.6, yong_sources=["月干"],
                total=60, grade="中上", gender="男", bazi="甲子 丙寅 庚午 丁丑")
    def clone(**kw):
        c = dict(base); c.update(kw); return c
    return [
        base,
        clone(cold=True, tiao="火"),
        clone(hot=True, tiao="水"),
        clone(strong_word="身强", score=62),
        clone(strong_word="身弱", score=38),
        clone(kind="从格", pattern="从财格", phrase="从财顺势", lead="财星"),
        clone(kind="专旺格", pattern="润下格", phrase="润下通达", lead="比劫",
              strong_word="身旺", score=80),
        clone(tianyi=True, noble=True, wencang=True),
        clone(blade=True),
        clone(flower=True),
        clone(huagai=True),
        clone(horse=True, yun_early=1.0, yun_mid=-0.5),
        clone(tiao="火", yun_early=-1.0, yun_mid=0.8, yun_late=1.0),
        clone(total=80, grade="上中"),
        clone(total=40, grade="中下"),
        clone(total=28, grade="下中", strong_word="身弱", score=26),
    ]
