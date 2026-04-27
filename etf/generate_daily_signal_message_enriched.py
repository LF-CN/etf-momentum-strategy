#!/usr/bin/env python3
"""
ETF实盘提醒 - 增强版 v3
单一数据源：全部从 signal.json（daily_task_full.py 实时计算）读取，
不再依赖快照表做展示，避免双库不同步。
"""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

VENV_PYTHON = "/opt/data/scripts/etf/.venv/bin/python"

NAME_MAP = {
    '159941': '纳指ETF',
    '510500': '中证500ETF',
    '511010': '国债ETF',
    '518880': '黄金ETF',
    '159928': '消费ETF',
}
CODE_ORDER = ['159941', '510500', '511010', '518880', '159928']


def ensure_supported_runtime():
    try:
        import akshare
    except ModuleNotFoundError:
        if sys.executable != VENV_PYTHON and Path(VENV_PYTHON).exists():
            os.execv(VENV_PYTHON, [VENV_PYTHON, __file__, *sys.argv[1:]])
        raise


ensure_supported_runtime()


def get_trade_calendar():
    import akshare as ak
    cal = ak.tool_trade_date_hist_sina().copy()
    cal["trade_date"] = cal["trade_date"].astype(str)
    return cal


def is_trading_day(date_str: str) -> bool:
    cal = get_trade_calendar()
    return date_str in set(cal["trade_date"].tolist())


def get_next_trading_day(date_str: str):
    cal = get_trade_calendar()
    future = cal[cal["trade_date"] > date_str]["trade_date"].tolist()
    return future[0] if future else None


def load_cached_signal():
    signal_file = Path('/opt/data/scripts/etf/data/signal.json')
    if not signal_file.exists():
        raise FileNotFoundError(f"signal file not found: {signal_file}")
    return json.loads(signal_file.read_text(encoding='utf-8'))


def run_daily_task():
    python_exec = VENV_PYTHON if Path(VENV_PYTHON).exists() else sys.executable
    result = subprocess.run(
        [python_exec, "/opt/data/scripts/etf/daily_task_full.py"],
        capture_output=True, text=True, timeout=600,
    )
    if result.returncode != 0:
        raise RuntimeError(f"daily_task_full.py failed:\n{result.stdout}\n{result.stderr}")
    return load_cached_signal()


def fmt_yuan(v):
    return f"{v:,.2f}"


def fmt_pct(v):
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.2f}%"


def build_message(signal: dict) -> str:
    today = datetime.now().strftime('%Y-%m-%d')
    trading_today = is_trading_day(today)

    target = signal.get('target_weights', {})
    should_rebalance = signal.get('should_rebalance', False)
    reason = signal.get('reason', '')
    current_weights = signal.get('current_weights', {})
    momentum_scores = signal.get('momentum_scores', {})
    holdings_detail = signal.get('holdings_detail', {})

    total = signal.get('total_value', 0)
    cash = signal.get('cash', 0)
    profit = signal.get('profit', 0)
    profit_pct = signal.get('profit_pct', 0)

    # 日期行
    if trading_today and signal['date'] == today:
        date_line = f"日期：{today}（交易日）"
    elif trading_today:
        date_line = f"日期：{today}（交易日，行情截至 {signal['date']}）"
    else:
        nxt = get_next_trading_day(today)
        nxt_line = f"\n下一个交易日：{nxt}" if nxt else ""
        date_line = f"日期：{today}（非交易日）\n说明：沿用 {signal['date']} 信号{nxt_line}"

    lines = [f"ETF实盘提醒\n{date_line}"]

    # ── 账户总览 ──
    lines.append("")
    lines.append(f"总资产：{fmt_yuan(total)} 元")
    lines.append(f"浮盈亏：{fmt_yuan(profit)}（{fmt_pct(profit_pct)}）")
    lines.append(f"现金：{fmt_yuan(cash)} 元")

    # ── 各持仓盈亏（成本基准）──
    lines.append("")
    lines.append("━━ 各持仓盈亏（成本基准）")
    for code in CODE_ORDER:
        cw = current_weights.get(code, 0)
        if cw <= 0 and target.get(code, 0) <= 0:
            continue
        name = NAME_MAP.get(code, code)
        detail = holdings_detail.get(code, {})
        mv = detail.get('market_value', 0)
        cost = detail.get('cost_price', 0)
        cur_price = detail.get('current_price', 0)

        if cw > 0 and (mv > 0 or total > 0):
            mv = mv or (total * cw / 100)
            if cost > 0 and cur_price > 0:
                pl_pct = (cur_price / cost - 1) * 100
            else:
                pl_pct = 0
            lines.append(
                f"  {name}：{fmt_pct(pl_pct)}"
                f"｜市值 {fmt_yuan(mv)}｜占比 {fmt_pct(cw)}"
                f"｜动量 {momentum_scores.get(code, 'N/A')}"
            )
        elif target.get(code, 0) > 0:
            lines.append(f"  {name}：目标 {fmt_pct(target.get(code, 0))}（当前空仓）")

    # ── 策略目标仓位 ──
    lines.append("")
    lines.append("━━ 策略目标仓位")
    if target:
        for code in CODE_ORDER:
            w = target.get(code, 0)
            if w > 0:
                name = NAME_MAP.get(code, code)
                lines.append(f"  {name}：{fmt_pct(w)}")
    else:
        lines.append("  （无策略信号）")

    # ── 偏离度分析 ──
    has_dev = False
    dev_lines = []
    for code in CODE_ORDER:
        real_w = current_weights.get(code, 0)
        t_w = target.get(code, 0)
        dev = real_w - t_w
        if abs(dev) >= 0.5 or t_w > 0:
            name = NAME_MAP.get(code, code)
            arrow = "↑" if dev > 0.5 else ("↓" if dev < -0.5 else "—")
            dev_lines.append(
                f"  {name}：实盘 {fmt_pct(real_w)} → 目标 {fmt_pct(t_w)}"
                f"｜偏离 {'+' if dev >= 0 else ''}{fmt_pct(dev)} {arrow}"
            )
            has_dev = True
    if has_dev:
        lines.append("")
        lines.append("━━ 偏离度")
        lines.extend(dev_lines)

    # ── 调仓结论 ──
    lines.append("")
    if should_rebalance:
        lines.append(f"结论：需要调仓")
        lines.append(f"原因：{reason}")
    else:
        lines.append(f"结论：暂不调仓 ✓")
        lines.append(f"原因：{reason}")

    if signal.get('stop_loss_trigger'):
        lines.append("提示：本次包含止损触发。")

    return '\n'.join(lines)


def main():
    today = datetime.now().strftime('%Y-%m-%d')

    # 加载策略信号（已含实时计算的持仓明细）
    trading_today = is_trading_day(today)
    if trading_today:
        signal = run_daily_task()
    else:
        signal = load_cached_signal()

    print(build_message(signal))


if __name__ == '__main__':
    main()
