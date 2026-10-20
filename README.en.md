# bazi-chart · Four Pillars of Destiny (BaZi) Engine in Python

[![PyPI version](https://img.shields.io/pypi/v/bazi-chart)](https://pypi.org/project/bazi-chart/)
[![Python](https://img.shields.io/pypi/pyversions/bazi-chart)](https://pypi.org/project/bazi-chart/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](./LICENSE)
[![Online Demo](https://img.shields.io/badge/▶_live_demo-Demo-b8860b)](https://liyooh007.github.io/bazi-chart/demo.html)

[中文](README.md) ｜ English

> Solar-terms computed in real time from an astronomical ephemeris ·
> true-solar-time with automatic cross-midnight pillar correction ·
> pure standard library, fully offline.

A from-scratch Python engine for the Chinese **Four Pillars of Destiny (八字 / BaZi)**.
It fixes the most common weakness of open-source libraries: treating the input
clock time as local time and **ignoring true solar time**, so charts for births
abroad keep the wrong day pillar even when the local apparent time falls on the
previous day.

Solar terms are derived from the Sun's apparent ecliptic longitude (VSOP87D),
true-solar-time correction is built in, and east/west longitudes are both
supported. When the corrected time crosses midnight (or the 23:00 zi-hour
boundary), the day and hour pillars are recomputed as a whole.

> ⚠️ **Disclaimer**: this is an astronomical-calendar and software-engineering
> project and a rule-based implementation of folk tradition. It has **no
> scientific predictive power** and must not be used for life decisions.

---

## Highlights

- 🌍 **True solar time** for east/west longitudes, with equation-of-time and cross-day pillar correction
- 🌌 **Astronomical solar terms**: VSOP87D heliocentric longitude + nutation (IAU1980) + aberration + ΔT — no hardcoded term table
- 🎯 **Validated against JPL DE441**: max deviation **≤ 1 minute** over 240 solar-term points (1900–2050)
- 📅 **Lunar conversion** 1899–2100 with leap months; 73,000+ day round-trip, zero error
- 📜 **Full chart**: four pillars, hidden stems, ten gods (十神), nayin, twelve life stages, void, combinations/clashes
- ⚖️ **Five-element strength**, day-master vigor, useful/auspicious/inauspicious gods
- 📚 **Multiple schools side by side**: strength-balance, *Qiongtong Baojian* season adjustment, *Ziping Zhenquan* pattern success/failure
- 🧧 **40+ shensha** (noble stars, blade, peach-blossom, canopy, travelling-horse, …)
- 📈 **Major luck / annual / monthly pillars**, with start age to a fraction of a year
- 🪶 **7-character destiny poem** and an auditable 0–100 composite score
- 💻 Cross-platform Linux / Windows / macOS, runs natively on a Raspberry Pi
- 🤖 **MCP server**: built-in `bazi-mcp` (JSON-RPC over stdio, zero dependencies), 4 tools for Claude Desktop and other AI clients — deterministic facts only
- 🔒 **Fully local & offline**: no network calls, no LLM calls, no third-party runtime dependencies

### Compared with similar projects

| Capability | **bazi-chart** | lunar-python | cantian/bazi-mcp | most forks of lunar |
|---|---|---|---|---|
| Language | pure Python (≥3.9), zero deps | Python/JS | TypeScript / Node | mostly JS |
| Calendar core | **own VSOP87D computation**, vs JPL DE441 ≤1 min | formula/table | third-party lunar lib | forks lunar |
| True solar time + cross-day pillars | ✅ both longitudes, recomputes pillars | partial | ✅ | often ❌ |
| Four pillars / hidden stems / ten gods / nayin | ✅ | ✅ (base layer) | ✅ | ✅ |
| Upper reasoning: patterns / useful god / Qiongtong / Ziping | ✅ multi-school | ❌ (DIY) | thin | uneven |
| Major luck / annual / monthly / 40+ shensha | ✅ | partial | ✅ | partial |
| MCP for AI agents | ✅ built-in, one-line `uvx` | ❌ | ✅ (Node) | ❌ |
| In-browser offline | ✅ Pyodide single-page demo | — | — | — |

Bug reports on edge dates (year boundaries, solar-term junctions, overseas
cross-day) are very welcome in [Issues](https://github.com/liyooh007/bazi-chart/issues).

---

## Install

```bash
pip install bazi-chart          # provides the `bazi` command
# or run without installing, always the latest PyPI build:
uvx --from bazi-chart bazi-mcp  # MCP server
```

From source:

```bash
git clone https://github.com/liyooh007/bazi-chart.git
cd bazi-chart && pip install .
```

---

## Quick start

CLI:

```bash
bazi chart 1990-05-12 14:30 -g 男 --lon 116.4
```

Overseas birth — a Beijing-time input of 1940-11-27 07:00 at San Francisco
(longitude −122.42) corrects to local apparent time **1940-11-26 15:02**, and
the day pillar automatically switches from 甲戌 to 癸酉:

```bash
bazi chart 1940-11-27 07:00 -g 男 --lon -122.42 --tz -8
```

Python API:

```python
from bazi import BaziChart

c = BaziChart(1990, 5, 12, 14, 30, gender="男", longitude=116.4)
print(c.four_pillars.ganzhi)    # 庚午 辛巳 丁丑 丁未
print(c.pattern.name)           # 正财格
print(c.report())               # full Chinese report
data = c.to_dict()              # JSON-friendly structured dict
```

---

## MCP (for AI agents)

A pure-stdlib MCP server over stdio that returns **deterministic chart facts
only** — interpretations are left to the host model.

```bash
uvx --from bazi-chart bazi-mcp
```

Claude Desktop config:

```json
{
  "mcpServers": {
    "bazi": { "command": "uvx", "args": ["--from", "bazi-chart", "bazi-mcp"] }
  }
}
```

| Tool | Purpose |
|---|---|
| `bazi_chart` | four pillars, hidden stems, ten gods, nayin, strength, patterns, Qiongtong, Ziping, shensha, start age + ten luck steps |
| `bazi_liunian` | one year's pillar: stems/branches, ten gods, interactions, annual shensha, current luck step |
| `bazi_liuyue` | the 12 solar-month pillars of a year (term ranges + ten gods) |
| `bazi_lunar` | Gregorian ↔ lunar conversion |

---

## Self-test

```bash
bazi verify        # 41 checks: 240 term points vs DE441, 73k-day lunar
                   # round-trips, day-pillar anchors, published charts,
                   # 400 randomized invariants
```

CI runs the suite on Python 3.9–3.13 across Linux/macOS/Windows.

---

## License

MIT. Birth data never leaves your machine; the live demo runs the wheel
locally in your browser via Pyodide/WASM.
