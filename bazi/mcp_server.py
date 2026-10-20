"""MCP (Model Context Protocol) stdio server for bazi-chart.

纯标准库实现的最小 MCP 服务端（JSON-RPC 2.0 over stdio），零第三方依赖。
设计原则：**只提供确定性排盘事实（facts only），不输出吉凶预测**——
格局/用神等规则化结论随 JSON 返回，命运解读交给宿主大模型。

用法（Claude Desktop / 任意 MCP 客户端）::

    bazi-mcp
    # 或：python -m bazi.mcp_server

工具（出生信息统一用 birth_* 参数，避免与查询年 year 撞名）：
    bazi_chart     四柱排盘（真太阳时、大运、格局用神、神煞）
    bazi_liunian   某公历年流年（干支/十神/与原局刑冲合害/神煞/所在大运）
    bazi_liuyue    某公历年 12 个流月（节气区间 + 干支十神）
    bazi_lunar     公历↔农历互转
"""
from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime

from . import __version__
from .lunar import lunar_to_solar, solar_to_lunar
from .solar_terms import terms_of_year

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "bazi-chart", "version": __version__}


# --------------------------------------------------------------------------- #
# 参数 & 工具实现
# --------------------------------------------------------------------------- #
# 出生信息参数（chart / liunian / liuyue 共用）
_BIRTH_PROPS = {
    "birth_year": {"type": "integer", "description": "出生公历年"},
    "birth_month": {"type": "integer"},
    "birth_day": {"type": "integer"},
    "birth_hour": {"type": "integer", "description": "0-23"},
    "birth_minute": {"type": "integer", "default": 0},
    "gender": {"type": "string", "enum": ["男", "女"], "default": "男"},
    "longitude": {"type": "number",
                  "description": "出生地经度，东经为正、西经为负（济南116.98、北京116.4、旧金山-122.42）；给出则换算真太阳时。与 birth_city 二选一，longitude 优先"},
    "birth_city": {"type": "string",
                   "description": "出生地城市短名（如 济南/北京/大理），内置 356 个国内地级单位经度，自动换算真太阳时；海外请直接用 longitude"},
    "tz": {"type": "number", "default": 8.0, "description": "出生钟表时区偏移，默认东八区"},
    "rollover": {"type": "string", "enum": ["zi", "midnight"], "default": "zi",
                 "description": "换日柱时刻：zi=23点晚子时（默认），midnight=0点"},
}
_BIRTH_REQUIRED = ["birth_year", "birth_month", "birth_day", "birth_hour"]


def _build_chart(a: dict):
    """从 MCP 参数构造 BaziChart，统一校验。"""
    from . import BaziChart
    missing = [k for k in _BIRTH_REQUIRED if a.get(k) is None]
    if missing:
        raise ValueError(f"缺少必填参数：{', '.join(missing)}")
    lon = a.get("longitude")
    if lon is None and a.get("birth_city"):
        from .data.city_longitude import lookup_longitude
        lon = lookup_longitude(a["birth_city"])
        if lon is None:
            raise ValueError(
                f"未收录城市「{a['birth_city']}」，国内可换城市短名，海外请直接用 longitude 参数")
    return BaziChart(
        int(a["birth_year"]), int(a["birth_month"]), int(a["birth_day"]),
        int(a["birth_hour"]), int(a.get("birth_minute", 0)),
        gender=a.get("gender", "男"),
        longitude=lon,
        tz_hours=float(a.get("tz", 8.0)),
        day_rollover=a.get("rollover", "zi"),
    )


def tool_chart(a: dict) -> dict:
    c = _build_chart(a)
    # facts-only：默认 brief（排盘事实），analysis=True 才附传统断语段
    return c.to_dict(deep=bool(a.get("analysis", False)))


def tool_liunian(a: dict) -> dict:
    year = int(a["year"])
    c = _build_chart(a)
    ln = c.liunian(year)
    return {
        "公历年份": year,
        "干支": ln.name,
        "周岁": int(ln.age),
        "天干十神": ln.shishen,
        "地支十神": ln.zhi_shishen,
        "十二长生": ln.changsheng,
        "与原柱关系": ln.relations,
        "流年神煞": [{"名称": n, "吉凶": t} for n, t in ln.shensha],
        "所在大运": ln.dayun or None,
        "提示": "流年以立春为界",
    }


def tool_liuyue(a: dict) -> list:
    """12 流月；返回每个流月的节气区间（公历）、干支、十神。"""
    year = int(a["year"])
    c = _build_chart(a)
    terms = terms_of_year(year)
    terms_next = terms_of_year(year + 1)
    months = c.liuyue(year)                       # (起始节, 干支, 十神)
    starts = [m[0] for m in months]
    # 流月从该年立春起、到次年立春前；第12月（丑月）始于“次年1月小寒”。
    # terms_of_year(year) 的“小寒”是本年1月，须替换为次年小寒，否则大雪月区间倒挂。
    merged = dict(terms)
    merged["小寒"] = terms_next["小寒"]
    out = []
    for i, (jie, gz, ss) in enumerate(months):
        s = merged[jie]
        e = merged[starts[i + 1]] if i < 11 else terms_next["立春"]
        out.append({
            "起节气": jie,
            "起": s.strftime("%Y-%m-%d %H:%M"),
            "止": e.strftime("%Y-%m-%d %H:%M"),
            "干支": gz,
            "天干十神": ss,
        })
    return out


def tool_lunar(a: dict) -> dict:
    y, mo, d = int(a["year"]), int(a["month"]), int(a["day"])
    if a.get("direction") == "lunar_to_solar":
        sd = lunar_to_solar(y, mo, d, bool(a.get("leap", False)))
        return {"公历": sd.isoformat()}
    ld = solar_to_lunar(y, mo, d)
    return {"农历": str(ld), "农历月天数": ld.month_days, "农历年天数": ld.year_days}


TOOLS = {
    "bazi_chart": {
        "description": (
            "四柱八字排盘（确定性事实，不做命运预测）。输入公历出生信息，"
            "返回四柱干支、藏干、十神、纳音、五行力量、旺衰、格局用神、"
            "穷通宝鉴调候、子平格局成败、神煞、起运与十步大运。"
            "给出出生地经度会自动换算真太阳时并处理跨日子时换柱。"),
        "inputSchema": {
            "type": "object",
            "properties": {**_BIRTH_PROPS,
                          "analysis": {"type": "boolean", "default": False,
                                       "description": "是否附带性格/事业/婚姻等传统断语段（默认只给排盘事实）"}},
            "required": _BIRTH_REQUIRED,
        },
        "fn": tool_chart,
    },
    "bazi_liunian": {
        "description": "排某公历年份的流年：干支、天干地支十神、与原四柱刑冲合害、流年神煞、所在大运。",
        "inputSchema": {
            "type": "object",
            "properties": {"year": {"type": "integer", "description": "要查询的公历流年"},
                           **_BIRTH_PROPS},
            "required": ["year", *_BIRTH_REQUIRED],
        },
        "fn": tool_liunian,
    },
    "bazi_liuyue": {
        "description": "排某公历年十二个流月（以节气为界），返回每段节气区间、干支、十神。",
        "inputSchema": {
            "type": "object",
            "properties": {"year": {"type": "integer"}, **_BIRTH_PROPS},
            "required": ["year", *_BIRTH_REQUIRED],
        },
        "fn": tool_liuyue,
    },
    "bazi_lunar": {
        "description": "公历转农历（默认）或农历转公历。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "direction": {"type": "string",
                              "enum": ["solar_to_lunar", "lunar_to_solar"],
                              "default": "solar_to_lunar"},
                "year": {"type": "integer"},
                "month": {"type": "integer"},
                "day": {"type": "integer"},
                "leap": {"type": "boolean", "default": False},
            },
            "required": ["year", "month", "day"],
        },
        "fn": tool_lunar,
    },
}


# --------------------------------------------------------------------------- #
# JSON-RPC 2.0 / MCP 最小传输层
# --------------------------------------------------------------------------- #
def _result(rid, result) -> str:
    return json.dumps({"jsonrpc": "2.0", "id": rid, "result": result},
                      ensure_ascii=False)


def _error(rid, code: int, message: str) -> str:
    return json.dumps({"jsonrpc": "2.0", "id": rid,
                       "error": {"code": code, "message": message}},
                      ensure_ascii=False)


def handle(msg: dict) -> str | None:
    method = msg.get("method")
    rid = msg.get("id")
    params = msg.get("params") or {}

    if method == "initialize":
        return _result(rid, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": SERVER_INFO,
        })
    if method in ("notifications/initialized", "initialized"):
        return None                       # 通知不回复
    if method == "ping":
        return _result(rid, {})
    if method == "tools/list":
        return _result(rid, {"tools": [
            {"name": n, "description": t["description"], "inputSchema": t["inputSchema"]}
            for n, t in TOOLS.items()]})
    if method == "tools/call":
        name = str(params.get("name") or "")
        args = params.get("arguments") or {}
        tool = TOOLS.get(name)
        if tool is None:
            return _error(rid, -32602, f"未知工具：{name}")
        try:
            data = tool["fn"](args)
        except (ValueError, KeyError) as exc:
            return _error(rid, -32602, f"参数错误：{exc}")
        except Exception as exc:                                        # noqa: BLE001
            traceback.print_exc(file=sys.stderr)
            return _error(rid, -32603, f"排盘失败：{type(exc).__name__}: {exc}")
        return _result(rid, {"content": [
            {"type": "text",
             "text": json.dumps(data, ensure_ascii=False, indent=2, default=str)}]})
    if rid is not None:
        return _error(rid, -32601, f"方法未实现：{method}")
    return None


def main() -> int:
    """逐行读取 stdin 的 JSON-RPC，结果写 stdout（日志一律 stderr）。"""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as exc:
            sys.stdout.write(_error(None, -32700, f"JSON 解析失败：{exc}") + "\n")
            sys.stdout.flush()
            continue
        out = handle(msg)
        if out is not None:
            sys.stdout.write(out + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
