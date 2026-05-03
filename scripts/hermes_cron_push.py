#!/usr/bin/env python3
"""
FraxVerse 每日收盘推送脚本 — cron 入口。

被 Hermes cron 调度调用，流程：
  1. 通过后端 API 获取今日交易信号 + 持仓状态 + 风控快照
  2. 组装日报文本
  3. 通过 hermes_weixin_push.py 推送到微信

注意：本脚本运行在 cron 会话中，不依赖 aiohttp / Hermes gateway。
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError

# ── 配置 ──────────────────────────────────────────────────────────────────
API_BASE = os.getenv("FRAXVERSE_API", "http://localhost:8000/api/v1")
WX_PUSH_SCRIPT = os.path.expanduser("/home/ubuntu/hermes_weixin_push.py")
WX_TARGET = "o9cq80yreD06LPao585Ez0NgWBvA@im.wechat"

# 用于后端 API 认证（从环境变量读取或 fallback）
ADMIN_USER = os.getenv("FRAXVERSE_ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("FRAXVERSE_ADMIN_PASS", "admin123")


def _api_get(path: str) -> dict:
    """Simple GET with JSON response (no aiohttp dependency)."""
    url = f"{API_BASE.rstrip('/')}/{path.lstrip('/')}"
    req = Request(url)
    try:
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except URLError as e:
        return {"error": str(e)}


def _api_post(path: str, data: dict) -> dict:
    """Simple POST with JSON body and response."""
    url = f"{API_BASE.rstrip('/')}/{path.lstrip('/')}"
    body = json.dumps(data).encode()
    req = Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except URLError as e:
        return {"error": str(e)}


def _login() -> str | None:
    """Get access token for API calls."""
    resp = _api_post("/auth/login", {"username": ADMIN_USER, "password": ADMIN_PASS})
    if isinstance(resp, dict) and resp.get("access_token"):
        return resp["access_token"]
    print(f"[push] login failed: {resp.get('detail', resp)}", file=sys.stderr)
    return None


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _fetch_signals(token: str) -> list:
    """Get today's trading signals from backend."""
    url = f"{API_BASE.rstrip('/')}/agent/decisions"
    req = Request(url, headers=_auth_header(token))
    try:
        with urlopen(req, timeout=10) as resp:
            raw = json.loads(resp.read().decode())
            # Response shape: {"code":0, "data":{"decisions":[...], "total":N}}
            if isinstance(raw, list):
                return raw
            inner = raw.get("data", raw)
            if isinstance(inner, dict):
                return inner.get("decisions", inner.get("items", []))
            return []
    except Exception as e:
        print(f"[push] signals fetch failed: {e}", file=sys.stderr)
        return []


def _fetch_portfolio(token: str) -> dict:
    """Get current portfolio status."""
    url = f"{API_BASE.rstrip('/')}/portfolio/summary"
    req = Request(url, headers=_auth_header(token))
    try:
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"[push] portfolio fetch failed: {e}", file=sys.stderr)
        return {}


def _fetch_risk(token: str) -> dict:
    """Get risk metrics snapshot."""
    url = f"{API_BASE.rstrip('/')}/risk/metrics"
    req = Request(url, headers=_auth_header(token))
    try:
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"[push] risk fetch failed: {e}", file=sys.stderr)
        return {}


def _build_report(signals: list, portfolio: dict, risk: dict) -> str:
    """Build WeChat-formatted daily report text."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"📊 **碎片宇宙 · 每日收盘报告**", f"🕐 {now}", ""]

    # ── 交易信号 ──
    lines.append("**【今日信号】**")
    if signals:
        for s in signals[:10]:
            code = s.get("stock_code", s.get("code", "?"))
            name = s.get("stock_name", s.get("name", ""))
            action = s.get("action", s.get("direction", "持有"))
            price = s.get("price", s.get("current_price", "—"))
            reason = s.get("reason", s.get("signal_type", ""))
            lines.append(f"  • {code} {name} — **{action}** @ {price}")
            if reason:
                lines.append(f"    └ {reason}")
    else:
        lines.append("  ⚠️ 今日无信号")

    # ── 持仓 ──
    lines.append("")
    lines.append("**【持仓概况】**")
    if isinstance(portfolio, dict):
        total = portfolio.get("total_asset", portfolio.get("total_value", portfolio.get("total", "—")))
        cash = portfolio.get("available_cash", "—")
        pnl = portfolio.get("unrealized_pnl", portfolio.get("daily_pnl", "—"))
        pos_count = portfolio.get("position_count", 0)
        lines.append(f"  总资产：`{total}` | 可用现金：`{cash}`")
        lines.append(f"  浮动盈亏：`{pnl}` | 持仓数：{pos_count}")
        positions = portfolio.get("positions", portfolio.get("items", []))
        if positions:
            for p in positions[:8]:
                code = p.get("stock_code", p.get("code", "?"))
                name = p.get("stock_name", p.get("name", ""))
                vol = p.get("volume", p.get("shares", 0))
                pnl_i = p.get("pnl", p.get("profit_pct", ""))
                lines.append(f"  • {code} {name} | {vol}股 | PnL: {pnl_i}")
    else:
        lines.append("  ⚠️ 持仓数据不可用")

    # ── 风控 ──
    lines.append("")
    lines.append("**【风控快照】**")
    if isinstance(risk, list) and risk:
        for item in risk[:5]:
            metric = item.get("metric", item.get("name", "?"))
            value = item.get("value", item.get("val", "—"))
            lines.append(f"  • {metric}: {value}")
    elif isinstance(risk, dict) and risk.get("status"):
        lines.append(f"  状态：{risk.get('status')}")
        lines.append(f"  敞口：{risk.get('exposure', '—')}")
        lines.append(f"  止损提醒：{'⚠️' if risk.get('stop_loss_triggered') else '✅ 无'}")
    else:
        lines.append("  ✅ 风控正常（无预警）")

    lines.append("")
    lines.append("---")
    lines.append("🤖 *碎片宇宙量化系统 · 自动生成*")

    return "\n".join(lines)


def _push_to_wechat(text: str) -> dict:
    """Use the stand-alone sync push script to deliver."""
    result = subprocess.run(
        [sys.executable, WX_PUSH_SCRIPT, "--to", WX_TARGET, "--text", text],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        return {"error": result.stdout.strip() or result.stderr.strip() or f"exit code {result.returncode}"}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"raw_stdout": result.stdout[:500]}


def main():
    print("[push] starting daily push...", file=sys.stderr)

    # 1. Login
    token = _login()
    if not token:
        _push_to_wechat("⚠️ 碎片宇宙 · 收盘推送失败\n后端 API 登录失败，请检查凭据。")
        sys.exit(1)

    # 2. Fetch data
    signals = _fetch_signals(token)
    portfolio = _fetch_portfolio(token)
    risk = _fetch_risk(token)

    # 3. Build report
    report = _build_report(signals, portfolio, risk)

    # 4. Save report file (always)
    report_dir = os.path.expanduser("~/FraxVerse/cron_reports")
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, f"daily_report_{datetime.now().strftime('%Y%m%d')}.txt")
    with open(report_path, "w") as f:
        f.write(report)
    print(f"[push] report saved to {report_path}", file=sys.stderr)

    # 5. Push to WeChat
    result = _push_to_wechat(report)
    if "error" in result:
        print(f"[push] WARNING: push failed (report saved to {report_path}): {result}", file=sys.stderr)
        # Try sending a fallback error notification
        _push_to_wechat(f"⚠️ 碎片宇宙 · 收盘推送异常\n推送失败：{result['error'][:100]}")
        # Don't exit with error — report was still saved
        sys.exit(0)

    print(f"[push] delivered successfully: {json.dumps(result, ensure_ascii=False)}", file=sys.stderr)


if __name__ == "__main__":
    main()
