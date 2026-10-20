"""Bazi（八字命理）—— 全方位、多融合、经过验证的命理计算引擎。

特性
----
* **节气自算**：VSOP87D 太阳黄经 + 章动 + 光行差 + ΔT，实时求 24 节气时刻，
  1900–2050 年与 JPL DE441 数值历表偏差 ≤1 分钟（240 点回归验证）
* **农历转换**：1899–2100 年权威朔望月年表，支持闰月，逐日往返零误差
* **四柱排盘**：立春换年、交节换月、五虎遁/五鼠遁、日柱儒略日递推、
  真太阳时校正、23 点换日可切换
* **完整体系**：藏干、十神、纳音、旬空、十二长生、刑冲合害三合三会、
  大运起运（3 天 1 岁）、流年流月、小运
* **格局用神**：禄刃格、透干取格、月令取格、专旺、从格、化气格；
  扶抑 + 调候 + 通关三法合参定用神喜忌
* **神煞 40+**：天乙/天德/月德/文昌/国印/禄神/羊刃/将星/华盖/驿马/桃花/
  劫煞/亡神/孤辰寡宿/魁罡/金神/十恶大败/阴差阳错/天赦/三奇……
* **综合断验**：性格、事业、财运、婚姻、健康、六亲、子女、学业、开运建议、
  逐年运势（含大运流年交互与岁运并临等标记）
* **可验证**：``python -m bazi verify`` 一键跑 7 大项 29 个子项自检

快速开始
--------
::

    from bazi import BaziChart

    c = BaziChart(1990, 5, 12, 14, 30, gender="男", longitude=116.4, name="张三")
    print(c.report())              # 文本命书
    c.to_dict()                    # 结构化数据（JSON 友好）
    c.liunian_table(2024, 2035)    # 流年表
    c.good_years(2024, 2035)       # 用神当值之年

命令行
------
::

    python -m bazi chart 1990-05-12 14:30 -g 男 --lon 116.4 --years 2024 2035
    python -m bazi chart 1990-05-12 14:30 --json > pan.json
    python -m bazi terms 2025          # 某年 24 节气时刻
    python -m bazi lunar 2025-01-29    # 公历→农历
    python -m bazi solar 2033 11 1 --leap
    python -m bazi verify              # 自检
"""

from __future__ import annotations

__version__ = "1.1.1"
__all__ = [
    "BaziChart", "cast_pillars", "FourPillars", "Pillar",
    "wu_xing_balance", "day_master_strength", "useful_god", "Pattern",
    "find_shensha", "solar_to_lunar", "lunar_to_solar", "LunarDate",
    "terms_of_year", "solar_term_datetime", "true_solar_time",
    "dayun_list", "liunian_of", "liuyue_of", "full_analysis",
    "destiny_poem", "chart_rating", "PoemResult", "PoemLine", "verify_library",
    "TIANGAN", "DIZHI", "WUXING", "SOLAR_TERMS", "ZANGGAN", "NAYIN_30",
    "ganzhi", "shishen", "nayin", "changsheng", "xunkong",
]

from .constants import (
    TIANGAN, DIZHI, WUXING, SOLAR_TERMS, ZANGGAN, NAYIN_30,
    ganzhi, shishen, nayin, changsheng, xunkong,
)
from .astro import terms_of_year, solar_term_datetime
from .lunar import LunarDate, solar_to_lunar, lunar_to_solar
from .pillars import (
    Pillar, FourPillars, cast_pillars, wuxing_balance as wu_xing_balance,
    day_master_strength, true_solar_time,
)
from .pattern import Pattern, useful_god
from .shensha import find_shensha
from .fortune import dayun_list, liunian_of, liuyue_of
from .analyze import full_analysis
from .poem import destiny_poem, chart_rating, PoemResult, PoemLine, verify_library
from .chart import BaziChart
