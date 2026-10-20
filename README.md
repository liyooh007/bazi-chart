# bazi-chart｜Python 四柱八字 CLI 排盘引擎

<!-- mcp-name: io.github.liyooh007/bazi-chart -->

[![PyPI version](https://img.shields.io/pypi/v/bazi-chart)](https://pypi.org/project/bazi-chart/)
[![Python](https://img.shields.io/pypi/pyversions/bazi-chart)](https://pypi.org/project/bazi-chart/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](./LICENSE)
[![Online Demo](https://img.shields.io/badge/▶_在线排盘-Demo-b8860b)](https://liyooh007.github.io/bazi-chart/demo.html)

中文 ｜ [English](README.en.md)

> 天文历实时推算节气 · 真太阳时跨时区自动换日柱 · 纯标准库离线运行
>
> 🌐 **不想安装？直接用浏览器在线排盘**：<https://liyooh007.github.io/bazi-chart/demo.html>
> （Pyodide 在本地浏览器 WASM 运行，出生信息不上传）

一个用 Python 从零实现的四柱八字排盘工具，重点解决很多开源库的共同短板：
**把输入时间直接当作当地时间，忽略真太阳时，海外出生场景不会自动跨日期换日柱**。

本项目用太阳视黄经实时推算节气，内置真太阳时校正，支持东经/西经输入；海外出生时间
换算落到前一天时，日柱、时柱会整体重算。CLI、Python API、JSON 输出都可用，适合做
历法学习、天文算法验证，也方便接入其它自动化工具。

> ⚠️ **免责声明**：本项目仅用于历法、天文算法与 Python 工程学习，属于传统民俗文化的
> 规则化实现，**不具备科学预测能力，不可作为人生决策依据**。文档中的名人出生时辰取
> 网络流传版本，仅用于排盘引擎回归测试，不作真实命例参考。

---

## ✨ 项目特性

- 🌍 **真太阳时校正**：支持东经/西经，自动处理经度时差、均时差和跨日期换日柱
- 🌌 **天文实时定节气**：VSOP87D 太阳黄经 + 章动 + 光行差 + ΔT，不硬编码节气表
- 🎯 **JPL DE441 对照验证**：1900–2050 年 240 个节气点误差 **≤1 分钟**
- 📅 **完整农历转换**：1899–2100，含闰月；73,000+ 天公历↔农历往返零误差
- 📜 **完整四柱排盘**：年/月/日/时柱、藏干、十神、纳音、十二长生、旬空、刑冲合害
- ⚖️ **五行力量量化**：日主旺衰、月令、通根、十神分布、用神/喜神/忌神/仇神/闲神
- 📚 **多流派并列输出**：扶抑、《穷通宝鉴》调候、《子平真诠》格局成败/官杀混杂/真假从
- 🧧 **神煞 40+**：天乙贵人、羊刃、桃花、华盖、驿马、十恶大败等，附查法与权重
- 📈 **大运/流年/流月**：顺排逆排、起运精确到小数岁、支持自定义流年区间
- 🪶 **命理诗与评分**：七言八句、逐句可核查；0–100 六项综合评分
- 💻 **跨平台**：Linux / Windows / macOS，树莓派 5 原生可跑
- 🤖 **MCP server**：内置 `bazi-mcp`（JSON-RPC stdio，零依赖），4 个工具供 Claude Desktop 等 AI 客户端调用，只返回确定性排盘事实
- 🔒 **纯本地离线**：无网络请求、无大模型调用、无第三方运行依赖

### 与同类项目对比

| 能力 | **bazi-chart（本项目）** | lunar-python | cantian/bazi-mcp | 多数 fork lunar 的八字库 |
|---|---|---|---|---|
| 语言 | 纯 Python（≥3.9，零依赖） | Python/JS 多语言 | TypeScript / Node | JS 为主 |
| 历法内核 | **自研 VSOP87D 实时推算**，对照 JPL DE441 ≤1 分钟 | 公式/查表推算 | 依赖第三方农历库 | 直接 fork lunar |
| 真太阳时 + 跨日换柱 | ✅ 东经/西经，自动重算日时柱 | 部分支持时差 | ✅ | 多数 ❌ 直接用输入时间 |
| 四柱 / 藏干 / 十神 / 纳音 | ✅ | ✅（基础干支层） | ✅ | ✅ |
| 上层推理：格局/用神/穷通/子平成败 | ✅ 多流派并列 | ❌（需自己写） | 较薄 | 参差 |
| 大运 / 流年 / 流月 / 神煞 40+ | ✅ | 部分 | ✅ | 部分 |
| MCP（AI Agent 直连） | ✅ 内置 `bazi-mcp`，`uvx` 一行起 | ❌ | ✅（Node） | ❌ |
| 浏览器离线运行 | ✅ Pyodide 单页 Demo | — | — | — |
| 安装 | `pip` / `uvx`，离线可跑 | 各包管理器 | 需 Node | 各异 |

> 定位差异：**lunar-python 是优秀的「历法/干支基石」**，本项目不重复造这一层的轮子之争，
> 而是用独立天文内核 + 完整子平上层推理 + MCP/Pyodide 分发，补「高精度四柱 + AI 可直连」这个位。
> 数据事实部分欢迎用边界日期（跨年、节气交界、海外跨日）在 [Issue](https://github.com/liyooh007/bazi-chart/issues) 挑错。

---

## 📦 安装

### PyPI

```bash
pip install bazi-chart
```

安装后得到 `bazi` 命令：

```bash
bazi --help
```

### 源码安装

```bash
git clone https://github.com/liyooh007/bazi-chart.git
cd bazi-chart
pip install .
# 或
uv pip install .
```

不安装也可以直接在源码目录运行：

```bash
python -m bazi --help
```

---

## 🚀 快速开始

### CLI：基础排盘

```bash
bazi chart 1990-05-12 14:30 -g 男 --lon 116.4
```

### 示例 1：国内出生（四川内江，东经）

```bash
bazi chart 1971-06-22 10:30 -g 男 --lon 105.06 --years 2000 2030
```

实际真太阳时校正结果：`10:30 → 09:28`。

### 示例 2：海外出生（美国旧金山，西经，跨日核心用例）

```bash
# 输入的是北京时间 1940-11-27 07:00，出生地经度 -122.42
bazi chart 1940-11-27 07:00 -g 男 --lon -122.42 --years 1950 1980
```

实跑结果：

```text
排盘时刻：1940-11-26 15:02（真太阳时：已启用）
天干：庚  丁  癸  庚
地支：辰  亥  酉  申
```

即北京时间输入 `1940-11-27 07:00`，按出生地经度校正后落到当地前一天，
**日柱自动由「甲戌」切换为「癸酉」**。

> 如果手上是出生地的**当地时钟时间**，需要同时指定 `--tz`：
>
> ```bash
> bazi chart 1940-11-27 07:00 -g 男 --lon -122.42 --tz -8
> ```
>
> `--lon` 管经度时差和均时差，`--tz` 管输入时间采用的时区。

---

## 📖 参数说明

```bash
bazi chart <YYYY-MM-DD> <HH:MM> -g <男|女> [--lon 经度] [--tz 时区] [--years 起 止]
```

| 参数 | 说明 |
| --- | --- |
| `chart` | 排盘并输出中文命书 |
| `<YYYY-MM-DD> <HH:MM>` | 公历时间，24 小时制 |
| `-g`, `--gender` | 性别：`男` / `女`，用于大运顺逆 |
| `--lon` | 出生地经度；东经为正，西经为负，用于真太阳时校正 |
| `--city` | 出生地城市短名（如 济南、大理），内置 356 个国内地级单位经度自动换算；与 `--lon` 同给时 `--lon` 优先。海外请用 `--lon` |
| `--tz` | 输入时钟相对 UTC 的时区偏移，默认 `8`；海外当地时间需显式指定 |
| `--years START END` | 输出指定区间的流年 |
| `--json` | 输出结构化 JSON |
| `--brief` | JSON 中省略长分析段 |
| `--sections 段名 ...` | 只输出指定命书段落 |
| `--rollover zi|midnight` | 日柱换日规则：默认 `zi`（23:00 晚子时换日） |

其它子命令：

```bash
bazi terms 2025                    # 2025 年 24 节气，精确到秒
bazi lunar 2025-01-29              # 公历 → 农历
bazi solar 2033 11 1 --leap        # 农历闰月 → 公历
bazi poem 1990-05-12 14:30 -g 男   # 七言八句命理诗
bazi verify                        # 41 项内置自检
```

---

## 🐍 Python API

```python
from bazi import BaziChart

c = BaziChart(1990, 5, 12, 14, 30, gender="男", longitude=116.4, name="张三")

print(c.four_pillars.ganzhi)          # 庚午 辛巳 丁丑 丁未
print(c.pattern.name)                 # 正财格
print(c.pattern.yongshen)             # 火
print(c.four_pillars.lunar_date)      # 庚午年四月十八

print(c.report(years=(2024, 2035)))   # 中文命书
data = c.to_dict()                    # JSON 友好的结构化数据
```

只排四柱和五行：

```python
from datetime import datetime
from bazi import cast_pillars, wu_xing_balance, day_master_strength, useful_god

fp = cast_pillars(datetime(1990, 5, 12, 14, 30), "男", longitude=116.4)
print(fp.ganzhi)
print(fp.relations())

power = wu_xing_balance(fp)
strength = day_master_strength(fp)
pattern = useful_god(fp, strength, power)
print(pattern.name, pattern.yongshen, pattern.xishen, pattern.jishen)
```

关闭多流派备选格局：

```python
c = BaziChart(1992, 12, 2, 12, 0, gender="男", longitude=120, show_alt=False)
```

更多模块化示例：

```python
from bazi import solar_to_lunar, lunar_to_solar, terms_of_year
from bazi import destiny_poem, chart_rating

print(solar_to_lunar(2024, 2, 10))            # 甲辰年正月初一
print(lunar_to_solar(2033, 11, 1, True))      # 2033-12-22（闰十一月）
print(terms_of_year(2025))                    # 24 节气

r = destiny_poem(c)
print(r.poem, r.score, r.grade)
for line in r.lines:
    print(line.text, "←", line.note)
print(chart_rating(c))
```

---

## 🤖 MCP（供 AI Agent 调用）

内置一个纯标准库的 MCP stdio server，零第三方依赖，**只返回确定性排盘事实，吉凶解读交给宿主模型**（facts only）。

```bash
bazi-mcp            # pip 安装后
python -m bazi.mcp_server   # 源码目录
```

**用 uvx 零安装自动跟最新版（推荐）**：无需 clone、无需 pip install，每次从 PyPI 拉起：

```bash
uvx --from bazi-chart bazi-mcp
```

已收录于[官方 MCP Registry](https://modelcontextprotocol.io/registry)（ID `io.github.liyooh007/bazi-chart`）。所有客户端本质都是启动同一个 stdio 命令：

- 命令 `uvx`，参数 `--from bazi-chart bazi-mcp`（需先装 [uv](https://github.com/astral-sh/uv)）

**Claude Code**

```bash
claude mcp add bazi -- uvx --from bazi-chart bazi-mcp
```

**Cursor / VS Code / Claude Desktop**（`mcp.json`）：

```json
{
  "mcpServers": {
    "bazi": { "command": "uvx", "args": ["--from", "bazi-chart", "bazi-mcp"] }
  }
}
```

**Codex CLI**（`~/.codex/config.toml`）：

```toml
[mcp_servers.bazi]
command = "uvx"
args = ["--from", "bazi-chart", "bazi-mcp"]
```

**Hermes Agent**

```bash
hermes mcp add bazi --command uvx --args --from bazi-chart bazi-mcp
```

> 无 uv / 网络受限时，先 `pip install bazi-chart`，再把命令换成 `bazi-mcp` 的绝对路径（如 `/home/you/.local/bin/bazi-mcp`）、args 留空即可。

连上后直接用自然语言提问，例如「公历 2026-10-20 12 时，男，山东济南，排八字」，客户端会自动调用对应工具。


| 工具 | 作用 |
|---|---|
| `bazi_chart` | 四柱、藏干、十神、纳音、五行旺衰、格局用神、穷通宝鉴、子平成败、神煞、起运与十步大运（`birth_year/month/day/hour`、`longitude` 等参数） |
| `bazi_liunian` | 某公历年流年：干支、十神、与原柱刑冲合害、流年神煞、所在大运 |
| `bazi_liuyue` | 某公历年 12 个流月（节气区间 + 干支十神） |
| `bazi_lunar` | 公历↔农历互转 |

出生信息统一用 `birth_*` 参数（与查询年 `year` 区分）。出生地支持两种：直接给 `longitude`（经度，海外用，西经为负），或给 `birth_city`（国内城市短名，如"济南""大理"，自动取经度）；二者同给时 `longitude` 优先。在线 Demo 见 GitHub Pages（`docs/demo.html`），城市名自动补全，内置 356 城、全程离线。

---

## 🧪 回归测试

```bash
bazi verify
# 或源码目录
python -m bazi verify
```

当前自检覆盖 **41 项**，包括：

- 240 个节气点与 JPL DE441 参考值偏差验证
- 73,000+ 天农历公历往返验证
- 日柱锚点验证：1900、1949、1960、2000、2024、2033 等
- 公开命盘四柱复现：乾隆、蒋介石、毛泽东、周恩来等
- 400 个随机命盘不变式验证
- 1043 条命理诗成句「7 字 + 偶句入韵」校验

### 为什么可信

| 验证项 | 方法 | 结果 |
| --- | --- | --- |
| 节气精度 | VSOP87D 天文算法 vs JPL DE441，10 年 × 24 节气 = 240 点 | 1900–2050 年 **≤1 分钟** |
| 农历年表 | 202 个农历年界的「月长合计 = 相邻正月日序之差」全量校验 | **零误差** |
| 农历转换 | 73,000+ 天「公历 → 农历 → 公历」往返 | **零误差** |
| 春节/闰月 | 1900 闰八、1984 闰十、2023 闰二、2025 闰六、2033 闰十一等 | 全部吻合 |
| 日柱锚点 | 1900、1949、2000、2024、2033 等独立日期 | 全部吻合 |
| 命例复现 | 乾隆、蒋介石、毛泽东、周恩来公开命盘 | 四柱逐字一致 |

2050 年后的分钟级偏差主要来自未来 ΔT 外推模型分歧，不是太阳黄经算法误差。

---

## 排盘规则

| 项目 | 规则 |
| --- | --- |
| 年柱 | **立春**换年，不是正月初一 |
| 月柱 | **节**换月（立春、惊蛰、小寒等），月干用五虎遁 |
| 日柱 | 儒略日连续推算；默认 **23:00 换日**，晚子时归次日 |
| 时柱 | 五鼠遁；子时从 23:00 开始 |
| 真太阳时 | 标准时 + 经度时差 + 均时差，实测均时差约 ±16.4 分钟 |
| 起运 | 阳男阴女顺排、阴男阳女逆排；3 天 = 1 岁，1 天 = 4 个月 |
| 流年 | 以立春为界 |
| 流月 | 流年干起五虎遁，以节换月 |

---

## 🛠️ 技术难点

### 1. 真太阳时跨日期处理

```text
真太阳时 = 标准时 + 经度时差 + 均时差
```

- 经度时差：`(出生地经度 - 时区中央经线) × 4 分钟`
- 均时差：地球轨道偏心率和黄赤交角导致，年内约在 -14 到 +16 分钟之间变化
- 若换算结果跨到前一天或后一天，日柱和时柱整体重算，而不是只改日期

### 2. 不硬编码节气表

节气由太阳视黄经实时求解，计算链为：

```text
VSOP87D 太阳黄经 → 章动 → 光行差 → ΔT → 目标黄经时刻反解
```

因此不受静态节气表年份限制，1900–2050 年分钟级稳定。

### 3. 多流派格局并列

项目将不同体系拆开：

- `pattern.py`：扶抑、正格、禄刃、专旺、从格、化气
- `qiongtong.py`：《穷通宝鉴》120 格逐日干×月令调候用神
- `ziping.py`：《子平真诠》格局成败、官杀混杂、真从/假从、专旺纯净度

不同流派结论可能不一致，例如身弱时扶抑派取印比，而调候派可能先取官杀。程序并列
输出依据，不强行合并成一个绝对答案。

### 4. 专旺格争议处理

润下、曲直、炎上等专旺格透出财星或官杀时存在流派争议。例如润下格透丙火/丁火：

- 严格派：财星破格，不入专旺
- 宽松派：气势成局，仍可取专旺

主判定保持稳定，同时在报告中追加「备选格局（流派之争）」；`show_alt=False` 可关闭。

---

## 📂 项目结构

```text
bazi/
├── __init__.py             对外 API
├── __main__.py             python -m bazi 入口
├── cli.py                  命令行：chart / terms / lunar / solar / poem / verify
├── constants.py            天干地支、藏干、十神、纳音、神煞、病候等常量表
├── astro.py                天文内核：儒略日、ΔT、VSOP87D、章动、均时差
├── solar_terms.py          节气服务：交节换月、立春换年、距节天数
├── lunar.py                农历转换与 LunarDate
├── pillars.py              四柱排盘、真太阳时、五行力量、旺衰
├── pattern.py              扶抑格局、用神、通关、寒暖调候
├── qiongtong.py            《穷通宝鉴》120 格调候表
├── ziping.py               《子平真诠》格局成败、官杀混杂、真假从、专旺纯净度
├── shensha.py              神煞体系
├── fortune.py              大运、流年、流月、起运
├── poem.py                 命理诗与综合评分
├── _poem_lines.py          诗库
├── analyze.py              中文断语层
├── chart.py                BaziChart 统一入口
├── data/                   农历年表、节气参考值
└── tests/                  内置验证套件
```

> `refs_bazi_skill/`（若存在）只是典籍参考数据对照，不属于运行依赖。

---

## 命理内容覆盖范围

- **基础**：天干地支、阴阳五行、生克、藏干、十神、纳音、旬空、十二长生、生肖星座
- **关系**：天干五合四冲、地支六合六冲六害、三合局、三会方、半合、三刑、自刑、伏吟
- **量化**：五行力量百分比、日主旺衰、十神分布、大运吉凶评分
- **格局**：正格、禄刃、专旺（曲直/炎上/稼穑/从革/润下）、从格、化气
- **用神**：扶抑、寒暖燥湿调候、通关，输出用/喜/忌/仇/闲神
- **典籍体系**：扶抑、《穷通宝鉴》120 格、《子平真诠》格局论
- **神煞**：40+ 神煞与流年十二神
- **运势**：大运、流年、流月、岁运并临、伏吟、用神到位标记
- **断语**：性格、事业、财运、婚姻、健康、六亲、子女、学业、开运建议
- **健康**：五行偏枯映射脏腑，并区分过旺/过弱症候；只作传统文化养生提示，不作医学诊断

---

## 边界说明

- 农历转换范围：**1899-02-10 至 2100-12-31**；四柱天文排盘不依赖农历年表，可排更早年份。
- 神煞、格局、换日、专旺破格存在流派差异，代码中保留开关或并列解释。
- 健康、性格、事业等文字是传统五行映射的规则化说明，仅作文化研究，不是医学或人生建议。
- 本项目不联网、不请求大模型；所有结果均可离线复现。

---

## Roadmap

- GitHub Actions：跨平台自动运行 `bazi verify`
- 合婚/双盘交互分析
- 紫微斗数安星模块
- 更多公开历法锚点与极端时区测试

---

## License

[MIT License](./LICENSE)

## 🔗 项目地址

GitHub：<https://github.com/liyooh007/bazi-chart>

欢迎 Star ⭐、Issue、PR，一起完善历法算法。
