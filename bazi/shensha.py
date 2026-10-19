"""神煞体系（40+ 种，规则可溯源）。

每条神煞按"查法依据 → 目标"建模：

* ``basis``：取值的依据，可为 日干 / 年干 / 月支 / 年支 / 日支 / 日柱 / 年柱 / 月令季节 / 年纳音
* ``targets``：被查的位置——四支、四干、日柱、时柱……
* ``type``：``吉`` / ``凶`` / ``中``，用于吉凶评分

规则均为子平法通行版本（《渊海子平》《三命通会》《神峰通考》系统）；
流派有分歧者已在注释中标注所采版本，便于校验与替换。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .constants import (
    DIZHI, nayin, LUSHEN, YANGREN,
)

__all__ = ["ShenSha", "find_shensha", "shensha_score", "liunian_shensha"]

# --------------------------------------------------------------------------- #
# 基础查表
# --------------------------------------------------------------------------- #
# 天乙贵人（通行版：甲戊庚牛羊，乙己鼠猴乡，丙丁猪鸡位，壬癸兔蛇藏，辛逢马虎）
TIANYI = {"甲": "丑未", "戊": "丑未", "庚": "丑未", "乙": "子申", "己": "子申",
          "丙": "亥酉", "丁": "亥酉", "壬": "卯巳", "癸": "卯巳", "辛": "午寅"}
# 太极贵人
TAIJI = {"甲": "子午", "乙": "子午", "丙": "卯酉", "丁": "卯酉",
         "戊": "辰戌丑未", "己": "辰戌丑未", "庚": "寅亥", "辛": "寅亥",
         "壬": "巳申", "癸": "巳申"}
# 福星贵人
FUXING = {"甲": "寅子", "丙": "寅子", "乙": "卯丑", "癸": "卯丑",
          "戊": "申", "己": "未", "丁": "亥", "庚": "午", "辛": "巳", "壬": "辰"}
# 国印贵人
GUOYIN = {"甲": "戌", "乙": "亥", "丙": "丑", "丁": "寅", "戊": "丑",
          "己": "寅", "庚": "辰", "辛": "巳", "壬": "未", "癸": "申"}
# 文昌贵人
WENCHANG = {"甲": "巳", "乙": "午", "丙": "申", "丁": "酉", "戊": "申",
            "己": "酉", "庚": "亥", "辛": "子", "壬": "寅", "癸": "卯"}
# 金舆
JINYU = {"甲": "辰", "乙": "巳", "丙": "未", "丁": "申", "戊": "未",
         "己": "申", "庚": "戌", "辛": "亥", "壬": "丑", "癸": "寅"}
# 红艳煞
HONGYAN = {"甲": "午", "乙": "午", "丙": "寅", "丁": "未", "戊": "辰",
           "己": "辰", "庚": "戌", "辛": "酉", "壬": "子", "癸": "申"}
# 天德贵人（以月建查干支）
TIANDE = {"寅": "丁", "卯": "申", "辰": "壬", "巳": "辛", "午": "亥", "未": "甲",
          "申": "癸", "酉": "寅", "戌": "丙", "亥": "乙", "子": "巳", "丑": "庚"}
# 月德贵人（三合局定干）
YUEDE = {"寅": "丙", "午": "丙", "戌": "丙",
         "申": "壬", "子": "壬", "辰": "壬",
         "亥": "甲", "卯": "甲", "未": "甲",
         "巳": "庚", "酉": "庚", "丑": "庚"}
# 三合局中神 / 墓库 / 长生 / 绝 / 天干（用于将星、华盖、驿马、劫煞等）
SANHE_GROUP = {"申子辰": "水", "寅午戌": "火", "巳酉丑": "金", "亥卯未": "木"}
JIANGXING = {"申子辰": "子", "寅午戌": "午", "巳酉丑": "酉", "亥卯未": "卯"}
HUAGAI = {"申子辰": "辰", "寅午戌": "戌", "巳酉丑": "丑", "亥卯未": "未"}
YIMA = {"申子辰": "寅", "寅午戌": "申", "巳酉丑": "亥", "亥卯未": "巳"}
TAOHUA = {"申子辰": "酉", "寅午戌": "卯", "巳酉丑": "午", "亥卯未": "子"}
JIESHA = {"申子辰": "巳", "寅午戌": "亥", "巳酉丑": "寅", "亥卯未": "申"}
ZAISHA = {"申子辰": "午", "寅午戌": "子", "巳酉丑": "卯", "亥卯未": "酉"}
WANGSHEN = {"申子辰": "亥", "寅午戌": "巳", "巳酉丑": "申", "亥卯未": "寅"}
# 孤辰 / 寡宿（以年支三会方查）
GUCHEN = {"亥子丑": "寅", "寅卯辰": "巳", "巳午未": "申", "申酉戌": "亥"}
GUASU = {"亥子丑": "戌", "寅卯辰": "丑", "巳午未": "辰", "申酉戌": "未"}
# 十恶大败日
SHIE_DABAI = ("甲辰", "乙巳", "丙申", "丁亥", "戊戌",
              "己丑", "庚辰", "辛巳", "壬申", "癸亥")
# 阴差阳错日
YINCHAYANGCUO = ("丙子", "丙午", "丁丑", "丁未", "戊寅", "戊申",
                 "己卯", "己酉", "壬辰", "壬戌", "癸巳", "癸亥")
# 魁罡日
KUIGANG = ("庚辰", "庚戌", "壬辰", "戊戌")
# 金神（时柱或日柱见之）
JINSHEN = ("乙丑", "己巳", "癸酉")
# 六秀日
LIUXIU = ("丙午", "丁未", "戊子", "戊午", "己丑", "己未")
# 日德
RIDE = ("甲寅", "丙辰", "戊辰", "庚辰", "壬戌")
# 天赦日：春戊寅、夏甲午、秋戊申、冬甲子
TIANSHE = {"春": "戊寅", "夏": "甲午", "秋": "戊申", "冬": "甲子"}


def _sanhe_key(zhi: str) -> str:
    for k in SANHE_GROUP:
        if zhi in k:
            return k
    raise ValueError(zhi)


def _sanhui_key(zhi: str) -> str:
    groups = ("亥子丑", "寅卯辰", "巳午未", "申酉戌")
    for k in groups:
        if zhi in k:
            return k
    raise ValueError(zhi)


def _season(zhi: str) -> str:
    if zhi in "寅卯辰":
        return "春"
    if zhi in "巳午未":
        return "夏"
    if zhi in "申酉戌":
        return "秋"
    return "冬"


@dataclass
class ShenSha:
    """一条命中的神煞。"""

    name: str
    position: str            # 年支/月支/日支/时支/年干/月干/时干/日柱/时柱/四柱
    value: str               # 命中的干支
    type: str                # 吉 / 凶 / 中
    note: str = ""

    def __str__(self) -> str:
        return f"{self.name}({self.position}{self.value})"


@dataclass
class ShenShaResult:
    items: list[ShenSha] = field(default_factory=list)
    score: float = 0.0

    def names(self) -> list[str]:
        return sorted({s.name for s in self.items})

    def by_name(self, name: str) -> list[ShenSha]:
        return [s for s in self.items if s.name == name]

    def group(self, type_: str) -> list[ShenSha]:
        return [s for s in self.items if s.type == type_]

    def to_dict(self) -> dict:
        return {"items": [str(s) for s in self.items],
                "score": round(self.score, 2),
                "吉": [str(s) for s in self.group("吉")],
                "凶": [str(s) for s in self.group("凶")],
                "中": [str(s) for s in self.group("中")]}


# --------------------------------------------------------------------------- #
# 查神煞
# --------------------------------------------------------------------------- #
def find_shensha(fp) -> ShenShaResult:
    """查四柱神煞。``fp`` 为 :class:`bazi.pillars.FourPillars`。"""
    res = ShenShaResult()
    pillars = {"年": fp.year, "月": fp.month, "日": fp.day, "时": fp.hour}
    zhis = {f"{k}支": p.zhi for k, p in pillars.items()}
    gans = {f"{k}干": p.gan for k, p in pillars.items()}
    day_gan, year_gan = fp.day.gan, fp.year.gan
    month_zhi, year_zhi, day_zhi, hour_zhi = fp.month.zhi, fp.year.zhi, fp.day.zhi, fp.hour.zhi
    day_name, year_name, hour_name = fp.day.name, fp.year.name, fp.hour.name
    day_zhi_all = tuple(zhis.values())

    def add(name, pos, value, type_, note=""):
        key = (name, pos, value)
        if key in _seen:
            return
        _seen.add(key)
        res.items.append(ShenSha(name, pos, value, type_, note))

    _seen: set[tuple[str, str, str]] = set()

    def match(table: dict[str, str], basis: str, *,
              positions=("年支", "月支", "日支", "时支"), name="", type_="吉", note=""):
        want = table.get(basis)
        if not want:
            return
        for pos in positions:
            v = zhis[pos] if pos.endswith("支") else gans[pos]
            if v in want:
                add(name, pos, v, type_, note)

    # ---------- 贵人系 ----------
    for basis_gan, label in ((day_gan, "日干"), (year_gan, "年干")):
        want = TIANYI[basis_gan]
        for pos in ("年支", "月支", "日支", "时支"):
            if zhis[pos] in want:
                add("天乙贵人", pos, zhis[pos], "吉", f"{label}查")
    match(TAIJI, day_gan, name="太极贵人", note="日干查")
    match(FUXING, day_gan, name="福星贵人", note="日干查")
    match(GUOYIN, day_gan, name="国印贵人", note="日干查")
    match(WENCHANG, day_gan, name="文昌贵人", note="主聪慧、利文书功名")
    match(JINYU, day_gan, name="金舆", note="主婚姻财帛、得配偶助")
    match(LUSHEN, day_gan, name="禄神", type_="吉", note="临官之位，主食禄")
    match(YANGREN, day_gan, name="羊刃", type_="凶", note="性刚烈，忌冲合")
    match(HONGYAN, day_gan, name="红艳煞", type_="凶", note="主情缘纠葛")

    # 天德 / 月德（以月建查，可落干或落支）
    td = TIANDE[month_zhi]
    if td in gans.values() or td in zhis.values():
        for pos, v in list(gans.items()) + list(zhis.items()):
            if v == td:
                add("天德贵人", pos, v, "吉", "月建查")
    yd = YUEDE[month_zhi]
    for pos, v in gans.items():
        if v == yd:
            add("月德贵人", pos, v, "吉", "月建查")

    # ---------- 三合系（以年支或日支查）----------
    for basis_zhi, label in ((year_zhi, "年支"), (day_zhi, "日支")):
        key = _sanhe_key(basis_zhi)
        for pos in ("年支", "月支", "日支", "时支"):
            v = zhis[pos]
            if v == JIANGXING[key]:
                add("将星", pos, v, "吉", f"{label}查")
            if v == HUAGAI[key]:
                add("华盖", pos, v, "中", f"{label}查，主孤高、艺术、宗教")
            if v == YIMA[key]:
                add("驿马", pos, v, "中", f"{label}查，主奔波迁徙")
            if v == TAOHUA[key]:
                add("桃花", pos, v, "中", f"{label}查，主异性缘")
            if v == JIESHA[key]:
                add("劫煞", pos, v, "凶", f"{label}查")
            if v == ZAISHA[key]:
                add("灾煞", pos, v, "凶", f"{label}查")
            if v == WANGSHEN[key]:
                add("亡神", pos, v, "凶", f"{label}查")

    # ---------- 年支三会系 ----------
    gk = _sanhui_key(year_zhi)
    if GUCHEN[gk] in day_zhi_all:
        add("孤辰", "四支", GUCHEN[gk], "凶")
    if GUASU[gk] in day_zhi_all:
        add("寡宿", "四支", GUASU[gk], "凶")
    # 天罗地网（年纳音：火命戌亥天罗、水土命辰巳地网）
    na = nayin(year_name)[-1]
    if na == "火" and ("戌" in day_zhi_all or "亥" in day_zhi_all):
        add("天罗", "四支", "戌亥", "中", "火命见戌亥")
    if na in ("水", "土") and ("辰" in day_zhi_all or "巳" in day_zhi_all):
        add("地网", "四支", "辰巳", "中", f"{na}命见辰巳")

    # ---------- 日柱系 ----------
    if day_name in SHIE_DABAI:
        add("十恶大败", "日柱", day_name, "凶")
    if day_name in YINCHAYANGCUO:
        add("阴差阳错", "日柱", day_name, "凶", "主婚姻、亲缘多阻")
    if day_name in KUIGANG:
        add("魁罡", "日柱", day_name, "中", "性刚果断，喜身旺")
    if day_name in LIUXIU:
        add("六秀日", "日柱", day_name, "吉")
    if day_name in RIDE:
        add("日德", "日柱", day_name, "吉")
    if hour_name in JINSHEN or day_name in JINSHEN:
        pos = "时柱" if hour_name in JINSHEN else "日柱"
        add("金神", pos, hour_name if pos == "时柱" else day_name, "中", "喜制伏")
    # 天赦日
    tianshe = TIANSHE[_season(month_zhi)]
    if day_name == tianshe:
        add("天赦", "日柱", day_name, "吉", "四季赦日，解灾")
    # 天医（月建前一位）
    ty = DIZHI[(DIZHI.index(month_zhi) - 1) % 12]
    if ty in day_zhi_all:
        add("天医", "四支", ty, "吉", "利医药健康")
    # 童子煞（通行简化查法：月支+年支组合，见日时支）
    if (month_zhi in "寅卯辰" and year_zhi in "子丑亥" and "寅" in (day_zhi, hour_zhi)) or \
       (month_zhi in "巳午未" and year_zhi in "寅卯辰" and "卯" in (day_zhi, hour_zhi)):
        add("童子煞", "日时支", day_zhi, "凶", "流派分歧较大，仅供参考")
    # 三奇（天上甲戊庚、地下乙丙丁、人中壬癸辛，须天干顺连）
    seq = "".join(gans[k] for k in ("年干", "月干", "日干", "时干"))
    for trio, label in (("甲戊庚", "天上三奇"), ("乙丙丁", "地下三奇"), ("壬癸辛", "人中三奇")):
        for i in range(2):
            win = seq[i:i + 3]
            if win == trio or win == trio[::-1]:
                add(label, "四干", win, "吉")
    # 官符/词馆等略

    res.score = shensha_score(res)
    return res


#: 神煞吉凶权重
_WEIGHT = {"吉": 1.0, "中": 0.0, "凶": -1.0}
_PRIORITY = {"天乙贵人": 2.0, "天德贵人": 1.8, "月德贵人": 1.8, "天赦": 1.5,
             "禄神": 1.2, "文昌贵人": 1.2, "将星": 1.2,
             "羊刃": -1.6, "十恶大败": -1.2, "阴差阳错": -1.2, "天罗": -0.8,
             "地网": -0.8, "劫煞": -1.0, "灾煞": -1.0, "亡神": -0.9,
             "孤辰": -0.7, "寡宿": -0.7, "桃花": 0.2, "驿马": 0.3, "华盖": 0.3}


def shensha_score(res: ShenShaResult) -> float:
    """神煞吉凶评分（正为吉、负为凶，量级 ±10 左右）。"""
    total = 0.0
    for s in res.items:
        w = _PRIORITY.get(s.name, _WEIGHT[s.type])
        total += w
    return total


# --------------------------------------------------------------------------- #
# 流年神煞
# --------------------------------------------------------------------------- #
_LN_NAMES = ("太岁", "太阳", "丧门", "太阴", "官符", "死符", "岁破",
             "龙德", "白虎", "福德", "吊客", "病符")


def liunian_shensha(year_zhi: str, natal_year_zhi: str) -> list[tuple[str, str]]:
    """流年神煞（以生年支顺推十二神）。返回 ``[(神煞名, 吉凶), ...]``。"""
    step = (DIZHI.index(year_zhi) - DIZHI.index(natal_year_zhi)) % 12
    ji = {"太阳", "太阴", "龙德", "福德"}
    xiong = {"丧门", "官符", "死符", "岁破", "白虎", "吊客", "病符"}
    name = _LN_NAMES[step]
    out = [(name, "吉" if name in ji else "凶" if name in xiong else "中")]
    if year_zhi == natal_year_zhi:
        out.append(("值太岁（本命年）", "中"))
    chong = DIZHI[(DIZHI.index(natal_year_zhi) + 6) % 12]
    if year_zhi == chong:
        out.append(("冲太岁", "凶"))
    # 天喜：红鸾之对冲（红鸾以年支查表，非六冲）
    hongluan = {"子": "卯", "丑": "寅", "寅": "丑", "卯": "子", "辰": "亥", "巳": "戌",
                "午": "酉", "未": "申", "申": "未", "酉": "午", "戌": "巳", "亥": "辰"}
    tianxi = DIZHI[(DIZHI.index(hongluan[natal_year_zhi]) + 6) % 12]
    if year_zhi == tianxi:
        out.append(("天喜", "吉"))
    return out
