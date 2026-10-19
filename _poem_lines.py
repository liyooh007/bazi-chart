"""命理诗的偶句（押韵句）诗库，供 :mod:`bazi.poem` 使用。

结构：``EVEN[slot]`` 为条目列表，每条
``(适用韵部, 条件标签, 成句函数, 注解函数)``；
条件标签见 :data:`CONDS`，``"all"`` 表示无条件（默认句放最后）。
所有成句由 :func:`bazi.poem.verify_library` 校验为 7 字。
"""

ALL = "ABCDE"

CONDS = {
    "cold": lambda c: c["cold"],
    "hot": lambda c: c["hot"],
    "tiao_ok": lambda c: c["tiao"] and not c["cold"] and not c["hot"],
    "yong_tou": lambda c: any(x in c["yong_sources"] for x in ("年干", "月干", "时干")),
    "tiao_need": lambda c: bool(c["tiao"]),
    "tianyi": lambda c: c["tianyi"],
    "noble": lambda c: c["noble"],
    "wencang": lambda c: c["wencang"],
    "blade": lambda c: c["blade"],
    "flower": lambda c: c["flower"],
    "huagai": lambda c: c["huagai"],
    "horse": lambda c: c["horse"],
    "high": lambda c: c["total"] >= 75,
    "mid": lambda c: 55 <= c["total"] < 75,
    "lowmid": lambda c: 45 <= c["total"] < 55,
    "all": lambda c: True,
}


def _note_month(c):
    return f"月令为{c['pattern']}提纲，{c['de_ling']}"


def _note_cold(c):
    return f"生于冬令（月支{c['month_zhi']}），局寒，最喜火来调候暖局"


def _note_hot(c):
    return f"生于夏令（月支{c['month_zhi']}），局燥，最喜水来调候润局"


def _note_yong(c):
    return f"用神为{c['yong']}（喜神{c['xi']}），补偏救弊全在此字"


def _note_tiao(c):
    return f"局中寒暖失调，以「{c['tiao']}」调候"


def _note_tianyi(c):
    return "命带天乙贵人，主逢凶化吉、多得贵人提携"


def _note_noble(c):
    return "命带天德/月德等贵人，主有德神护佑、行事少阻"


def _note_wen(c):
    return "命带文昌，主聪慧好文，利考试、文书与技艺"


def _note_blade(c):
    return "羊刃入命，性刚烈，喜官杀制伏、忌冲合放纵"


def _note_flower(c):
    return "桃花/红艳入命，异性缘厚，宜守正自持"


def _note_huagai(c):
    return "华盖入命，性喜清静，有艺术、宗教或专精一技之缘"


def _note_horse(c):
    return "驿马入命，一生多动，宜外出发展、静守则滞"


def _note_plain(c):
    return "无显著贵人驿马，凡事靠自身经营，平稳中见功夫"


def _note_good(c):
    return f"命局综合评分 {c['total']:.0f}（{c['grade']}），根基较稳"


def _note_mid(c):
    return f"命局综合评分 {c['total']:.0f}（{c['grade']}），成败系于行运与人为"


def _note_low(c):
    return f"命局综合评分 {c['total']:.0f}（{c['grade']}），起伏较多，重在修德借运"


def _note_warn(c):
    return "命理只示倾向，非定数；趋吉避凶仍在人为"


EVEN = {
    # ---- 第 2 句：月令 / 寒暖 ----
    2: [
        (ALL, "cold",
         {"A": lambda c: "寒天喜火暖元神", "B": lambda c: "寒生喜火暖前程",
          "C": lambda c: "寒局须求暖局功", "D": lambda c: "寒生待火始相宜",
          "E": lambda c: "寒天盼火暖心头"}, _note_cold),
        (ALL, "hot",
         {"A": lambda c: "炎夏须水润燥身", "B": lambda c: "夏炎得水自清清",
          "C": lambda c: "炎炎喜水济其中", "D": lambda c: "夏生待润乃合宜",
          "E": lambda c: "伏中盼水一泓秋"}, _note_hot),
        (ALL, "all",
         {"A": lambda c: "月令为纲定此身", "B": lambda c: "月令提纲气象清",
          "C": lambda c: "月令提纲定主功", "D": lambda c: "月令为纲细品时",
          "E": lambda c: "月令为纲看命由"}, _note_month),
        (ALL, "all",
         {"A": lambda c: "月令为纲细品神", "B": lambda c: "提纲得力气自盈",
          "C": lambda c: "月令提纲定此中", "D": lambda c: "月令为纲定早迟",
          "E": lambda c: "提纲一语见根由"}, _note_month),
    ],
    # ---- 第 4 句：用神 / 调候 ----
    4: [
        (ALL, "yong_tou",
         {"A": lambda c: f"用神{c['yong']}透最相亲", "B": lambda c: f"用神{c['yong']}透自分明",
          "C": lambda c: f"用神{c['yong']}透必成功", "D": lambda c: f"用神{c['yong']}透最相宜",
          "E": lambda c: f"用神{c['yong']}透贵来求"},
         lambda c: f"用神「{c['yong']}」已透天干，取用真切、行运易应（{c['yong_sources']}）"),
        (ALL, "tiao_need",
         {"A": lambda c: f"调候须{c['tiao']}暖此身", "B": lambda c: f"调候凭{c['tiao']}始有成",
          "C": lambda c: f"调候还凭{c['tiao']}立功", "D": lambda c: f"调候须{c['tiao']}乃得宜",
          "E": lambda c: f"调候求{c['tiao']}解百忧"}, _note_tiao),
        (ALL, "all",
         {"A": lambda c: f"扶抑取{c['yong']}作养神", "B": lambda c: f"扶抑凭{c['yong']}定亏成",
          "C": lambda c: f"扶抑求{c['yong']}建事功", "D": lambda c: f"扶抑凭{c['yong']}最相宜",
          "E": lambda c: f"用神{c['yong']}为命所求"}, _note_yong),
    ],
    # ---- 第 6 句：神煞 / 助力 ----
    6: [
        (ALL, "tianyi",
         {"A": lambda c: "天乙相扶贵人亲", "B": lambda c: "天乙相扶贵显名",
          "C": lambda c: "天乙临门暗建功", "D": lambda c: "天乙相扶贵可期",
          "E": lambda c: "天乙相扶有贵求"}, _note_tianyi),
        (ALL, "noble",
         {"A": lambda c: "天德月德佑吉人", "B": lambda c: "德神护佑事能成",
          "C": lambda c: "二德临身暗积功", "D": lambda c: "二德临身灾自迟",
          "E": lambda c: "二德临身福自稠"}, _note_noble),
        (ALL, "wencang",
         {"A": lambda c: "文昌入命笔生神", "B": lambda c: "文昌入命好文名",
          "C": lambda c: "文昌入命建事功", "D": lambda c: "文昌入命显才奇",
          "E": lambda c: "文昌入命学优游"}, _note_wen),
        (ALL, "blade",
         {"A": lambda c: "刃星须制性方纯", "B": lambda c: "羊刃逢制始有成",
          "C": lambda c: "刃逢官杀化为功", "D": lambda c: "羊刃宜制不宜迟",
          "E": lambda c: "羊刃须制敛刚遒"}, _note_blade),
        (ALL, "flower",
         {"A": lambda c: "桃花缘厚守其身", "B": lambda c: "桃花缘重莫忘情",
          "C": lambda c: "桃花守正不迷中", "D": lambda c: "桃花宜正不宜痴",
          "E": lambda c: "桃花守正自悠悠"}, _note_flower),
        (ALL, "huagai",
         {"A": lambda c: "华盖孤高艺入神", "B": lambda c: "华盖临身近道清",
          "C": lambda c: "华盖临身艺有功", "D": lambda c: "华盖临身静者宜",
          "E": lambda c: "华盖临身趣自幽"}, _note_huagai),
        (ALL, "horse",
         {"A": lambda c: "驿马驱驰动里奔", "B": lambda c: "驿马他乡也成名",
          "C": lambda c: "驿马奔波动建功", "D": lambda c: "驿马他乡贵可期",
          "E": lambda c: "驿马他乡远游求"}, _note_horse),
        (ALL, "all",
         {"A": lambda c: "无煞无虚守本真", "B": lambda c: "神煞平和气自清",
          "C": lambda c: "神煞平和稳步功", "D": lambda c: "不靠神煞自撑持",
          "E": lambda c: "平平神煞自悠悠"}, _note_plain),
    ],
    # ---- 第 8 句：总断 / 劝勉 ----
    8: [
        (ALL, "high",
         {"A": lambda c: "福厚还须积德真", "B": lambda c: "根基既厚事可成",
          "C": lambda c: "顺理而行路自通", "D": lambda c: "好景长宜自护持",
          "E": lambda c: "福厚还须德泽留"}, _note_good),
        (ALL, "high",
         {"A": lambda c: "富贵由人也在身", "B": lambda c: "修德前程自有成",
          "C": lambda c: "顺理成章事事通", "D": lambda c: "好景还须自护持",
          "E": lambda c: "福厚还须德厚留"}, _note_good),
        (ALL, "mid",
         {"A": lambda c: "勤能补拙自通神", "B": lambda c: "步步为营事竟成",
          "C": lambda c: "稳步图之渐见功", "D": lambda c: "中人之质在坚持",
          "E": lambda c: "缓步前行莫强求"}, _note_mid),
        (ALL, "mid",
         {"A": lambda c: "勤勉为舟可立身", "B": lambda c: "勤而行之自有成",
          "C": lambda c: "稳步行来渐有功", "D": lambda c: "中平之命自撑持",
          "E": lambda c: "稳中求进莫贪求"}, _note_mid),
        (ALL, "lowmid",
         {"A": lambda c: "多劳少逸待时奔", "B": lambda c: "守正待时运再成",
          "C": lambda c: "借运而行可补功", "D": lambda c: "先难后易待明时",
          "E": lambda c: "莫叹沉浮且缓求"}, _note_mid),
        (ALL, "all",
         {"A": lambda c: "修心积德可回春", "B": lambda c: "积德修心命可更",
          "C": lambda c: "积德修心暗补功", "D": lambda c: "命虽有定数可移",
          "E": lambda c: "积善修心福自留"}, _note_low),
        (ALL, "all",
         {"A": lambda c: "命示三分人为本", "B": lambda c: "命示三分在己行",
          "C": lambda c: "命示趋避尽人功", "D": lambda c: "命示趋避贵自持",
          "E": lambda c: "命示三分七分修"}, _note_warn),
        (ALL, "all",
         {"A": lambda c: "命由己造运由人", "B": lambda c: "三分天定七分情",
          "C": lambda c: "命理只言趋避功", "D": lambda c: "趋吉避凶在自持",
          "E": lambda c: "莫问天机问自修"}, _note_warn),
    ],
}
