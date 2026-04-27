#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

VENV_PYTHON = "/opt/data/scripts/etf/.venv/bin/python"


def ensure_supported_runtime():
    try:
        import akshare  # noqa: F401
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
    trade_dates = set(cal["trade_date"].tolist())
    return date_str in trade_dates


def get_next_trading_day(date_str: str):
    cal = get_trade_calendar()
    future = cal[cal["trade_date"] > date_str]["trade_date"].tolist()
    return future[0] if future else None


def load_cached_signal() -> dict:
    signal_file = Path('/opt/data/scripts/etf/data/signal.json')
    if not signal_file.exists():
        raise FileNotFoundError(f"signal file not found: {signal_file}")
    return json.loads(signal_file.read_text(encoding='utf-8'))


def run_daily_task() -> dict:
    python_exec = VENV_PYTHON if Path(VENV_PYTHON).exists() else sys.executable
    result = subprocess.run(
        [python_exec, "/opt/data/scripts/etf/daily_task_full.py"],
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.returncode != 0:
        raise RuntimeError(f"daily_task_full.py failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")

    return load_cached_signal()


def fmt_pct(v):
    return f"{v:.1f}%"


def main():
    today = datetime.now().strftime('%Y-%m-%d')
    trading_today = is_trading_day(today)

    if trading_today:
        signal = run_daily_task()
    else:
        signal = load_cached_signal()

    signal_date = signal['date']

    if trading_today and signal_date == today:
        header = f"ETF实盘提醒\n日期：{today}（交易日）"
    elif trading_today and signal_date != today:
        header = f"ETF实盘提醒\n日期：{today}（交易日，当前使用最近可得行情 {signal_date}）"
    else:
        next_trading_day = get_next_trading_day(today)
        next_line = f"\n下一个交易日：{next_trading_day}" if next_trading_day else ""
        header = f"ETF实盘提醒\n日期：{today}（非交易日）\n说明：今日非交易日，不重跑策略，沿用最近交易日 {signal_date} 的策略信号。{next_line}"

    current = signal.get('current_weights', {})
    target = signal.get('target_weights', {})
    lines = [
        header,
        f"总资产：{signal['total_value']:.2f} 元",
        f"浮盈亏：{signal['profit']:.2f} 元（{signal['profit_pct']:.2f}%）",
        "",
        f"当前权重：中证500ETF {fmt_pct(current.get('510500', 0))}｜纳指ETF {fmt_pct(current.get('159941', 0))}｜国债ETF {fmt_pct(current.get('511010', 0))}",
        f"目标权重：中证500ETF {fmt_pct(target.get('510500', 0))}｜纳指ETF {fmt_pct(target.get('159941', 0))}｜国债ETF {fmt_pct(target.get('511010', 0))}",
        "",
        f"结论：{'需要调仓' if signal['should_rebalance'] else '暂不调仓'}",
        f"原因：{signal['reason']}",
    ]

    if signal.get('stop_loss_trigger'):
        lines.append('提示：本次包含止损触发。')

    print('\n'.join(lines))


if __name__ == '__main__':
    main()
