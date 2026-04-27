#!/usr/bin/env python3
"""
ETF 实盘每日任务
- 参数口径与 Stage7 低回撤正式基线一致
- 直接复用 windows_backtest_package/core 的 DailyMonitoringBLM
- 从数据库读取当前持仓/现金/初始本金
- 基于数据库中的 last_rebalance_date 计算冷却期
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path('/opt/data/scripts/etf')
PROJECT_PYTHON = PROJECT_ROOT / '.venv/bin/python'
SIGNAL_FILE = PROJECT_ROOT / 'data/signal.json'

CORE_SCRIPT = r'''
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd

import sys
sys.path.insert(0, '/opt/data/scripts/etf')
sys.path.insert(0, '/opt/data/scripts/etf/windows_backtest_package/core')

from config import ETF_POOL, STRATEGY_PARAMS, RISK_PARAMS, SIGNAL_FILE
from database import init_db, get_holdings, get_cash, get_initial_capital, get_setting, save_nav
from momentum_backtest import DailyMonitoringBLM


def append_latest_quote_if_needed(prices: pd.DataFrame) -> pd.DataFrame:
    """若本地历史数据未到今天，则尝试补入当日最新价。"""
    if prices.empty:
        return prices

    last_data_date = pd.Timestamp(prices.index[-1]).normalize()
    today = pd.Timestamp.today().normalize()
    if last_data_date >= today:
        return prices

    print(f'[Fallback] 历史数据最新为 {last_data_date.strftime("%Y-%m-%d")}，尝试补当天行情...')
    try:
        pq_code = """
import sys, json
sys.path.append('/opt/data/scripts/AkShare/.venv/Lib/site-packages')
import pqquotation
codes = ['510500.SH', '159941.SZ', '511010.SH', '518880.SH', '159928.SZ']
src = pqquotation.use('tencent')
rt = src.real(codes)
result = {}
for code, info in rt.items():
    now = info.get('now') or info.get('close')
    if now and float(now) > 0:
        pure = code.replace('.SH', '').replace('.SZ', '').replace('.BJ', '')
        close = float(now)
        volume = int(info.get('volume') or 0)
        result[pure] = {
            'open': float(info.get('open') or close),
            'high': float(info.get('high') or close),
            'low': float(info.get('low') or close),
            'close': close,
            'volume': volume,
            'amount': close * volume,
        }
print('__PQ_RESULT__' + json.dumps(result, ensure_ascii=False) + '__PQ_RESULT__')
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(pq_code)
            tmp_path = f.name
        try:
            result = subprocess.run(
                ['/opt/hermes/.venv/bin/python3', tmp_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            stdout = result.stdout or ''
            if '__PQ_RESULT__' not in stdout:
                print(f'[Fallback] subprocess 异常：{(result.stderr or "无输出")[:200]}')
                return prices
            patch_rows = json.loads(stdout.split('__PQ_RESULT__')[1])
            if not patch_rows:
                print('[Fallback] 实时源返回空数据，沿用最近历史数据')
                return prices

            today_ts = pd.Timestamp.today()
            close_row = {code: vals['close'] for code, vals in patch_rows.items()}
            new_row = pd.DataFrame([close_row], index=[today_ts])
            prices = pd.concat([prices, new_row])
            print(f'[Fallback] 成功补入 {today_ts.strftime("%Y-%m-%d")} 的最新价：{close_row}')

            csv_dir = Path('/opt/data/scripts/etf/windows_backtest_package/etf_data')
            for code, ohlcv in patch_rows.items():
                csv_file = csv_dir / f'{code}_kline.csv'
                if not csv_file.exists():
                    continue
                old_df = pd.read_csv(csv_file, parse_dates=['date'])
                old_df = old_df[old_df['date'].dt.normalize() != today_ts.normalize()]
                new_df = pd.DataFrame({
                    'date': [today_ts.normalize()],
                    'open': [ohlcv['open']],
                    'high': [ohlcv['high']],
                    'low': [ohlcv['low']],
                    'close': [ohlcv['close']],
                    'volume': [ohlcv['volume']],
                    'amount': [ohlcv['amount']],
                })
                pd.concat([old_df, new_df], ignore_index=True).to_csv(csv_file, index=False, encoding='utf-8')
            return prices
        finally:
            os.unlink(tmp_path)
    except Exception as exc:
        print(f'[Fallback] 补价异常：{type(exc).__name__}: {exc}，沿用最近历史数据')
        return prices


def compute_rows_since_rebalance(prices: pd.DataFrame, last_rebalance_date: str | None) -> int:
    if not last_rebalance_date:
        return 999
    try:
        last_ts = pd.Timestamp(last_rebalance_date).normalize()
    except Exception:
        return 999
    idx = pd.DatetimeIndex(prices.index).normalize()
    return int((idx > last_ts).sum())


def main():
    init_db()

    strategy = DailyMonitoringBLM(
        initial_capital=STRATEGY_PARAMS['initial_capital'],
        trigger_deviation=STRATEGY_PARAMS['trigger_deviation'],
        signal_weight=STRATEGY_PARAMS['signal_weight'],
        stop_loss_threshold=STRATEGY_PARAMS['stop_loss_threshold'],
        lookback_period=STRATEGY_PARAMS['lookback_period'],
        cooldown_days=STRATEGY_PARAMS['cooldown_days'],
        top_n=STRATEGY_PARAMS['top_n'],
        transaction_cost=STRATEGY_PARAMS['transaction_cost'],
        factor_weights=STRATEGY_PARAMS['factor_weights'],
        style_factors=STRATEGY_PARAMS['style_factors'],
    )
    strategy.constraints = {
        'max_single_weight': RISK_PARAMS['max_single_weight'],
        'min_holding': STRATEGY_PARAMS['min_trade_amount'],
    }

    print('正在获取历史K线数据...')
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = STRATEGY_PARAMS.get('data_start_date', '2016-01-01')
    prices = strategy.fetch_data(start_date, end_date)
    if prices.empty:
        raise RuntimeError('获取数据失败')
    prices = append_latest_quote_if_needed(prices)
    prices = prices.sort_index()
    print(f'获取到 {len(prices)} 天数据')

    holdings = get_holdings()
    cash = float(get_cash() or 0)
    initial_capital = float(get_initial_capital() or STRATEGY_PARAMS['initial_capital'])
    latest_prices = prices.iloc[-1]

    current_shares = {code: float(holdings.get(code, {}).get('shares', 0) or 0) for code in ETF_POOL.keys()}
    entry_prices = {
        code: float(holdings.get(code, {}).get('cost_price', 0) or 0)
        for code in ETF_POOL.keys()
        if float(holdings.get(code, {}).get('cost_price', 0) or 0) > 0
    }

    holdings_value = 0.0
    for code, shares in current_shares.items():
        price = float(latest_prices.get(code, 0) or 0)
        holdings_value += shares * price
    total_value = cash + holdings_value

    current_weights = {}
    for code in ETF_POOL.keys():
        price = float(latest_prices.get(code, 0) or 0)
        current_weights[code] = (current_shares[code] * price / total_value) if total_value > 0 else 0.0

    latest_date = prices.index[-1]
    momentum_scores = strategy.calculate_momentum_score(prices, latest_date)
    target_weights = strategy.calculate_BLM_weights(prices, latest_date)

    last_rebalance_date = get_setting('last_rebalance_date')
    rows_since_rebalance = compute_rows_since_rebalance(prices, last_rebalance_date)

    rebalance_check = strategy.check_trigger_conditions(
        prices,
        latest_date,
        pd.Series(current_weights),
        target_weights,
        current_shares,
        total_value,
        entry_prices,
        rows_since_rebalance=rows_since_rebalance,
    )

    save_nav(
        latest_date.strftime('%Y-%m-%d'),
        total_value=total_value,
        cash=cash,
        holdings_value=holdings_value,
    )

    signals = []
    for code in ETF_POOL.keys():
        target = float(target_weights.get(code, 0) or 0)
        current = float(current_weights.get(code, 0) or 0)
        deviation = abs(target - current)
        if deviation <= 0:
            continue

        action = 'hold'
        if target > current:
            action = 'buy'
        elif target < current:
            action = 'sell'

        if deviation > 0 or code in {asset.get('code') for asset in rebalance_check.get('stop_loss_assets', [])}:
            signals.append({
                'code': code,
                'name': ETF_POOL[code]['name'],
                'action': action,
                'current_weight': round(current * 100, 1),
                'target_weight': round(target * 100, 1),
                'deviation': round(deviation * 100, 1),
                'reason': f'目标{target:.1%} vs 当前{current:.1%}',
                'momentum_score': round(float(momentum_scores.get(code, 0) or 0), 1),
            })

    signals.sort(key=lambda item: item['deviation'], reverse=True)

    # 持仓明细：供展示推送用，避免 enriched 脚本重复查库
    holdings_detail = {}
    for code in ETF_POOL.keys():
        price = float(latest_prices.get(code, 0) or 0)
        shares = current_shares.get(code, 0)
        cost = float(holdings.get(code, {}).get('cost_price', 0) or 0)
        if shares > 0 or cost > 0:
            holdings_detail[code] = {
                'shares': shares,
                'cost_price': cost,
                'current_price': round(price, 4),
                'market_value': round(shares * price, 2),
            }

    result = {
        'date': latest_date.strftime('%Y-%m-%d'),
        'total_value': round(total_value, 2),
        'cash': round(cash, 2),
        'initial_capital': round(initial_capital, 2),
        'profit': round(total_value - initial_capital, 2),
        'profit_pct': round((total_value - initial_capital) / initial_capital * 100, 2) if initial_capital else 0,
        'strategy_params': {
            'trigger_deviation': STRATEGY_PARAMS['trigger_deviation'],
            'signal_weight': STRATEGY_PARAMS['signal_weight'],
            'stop_loss_threshold': STRATEGY_PARAMS['stop_loss_threshold'],
            'lookback_period': STRATEGY_PARAMS['lookback_period'],
            'cooldown_days': STRATEGY_PARAMS['cooldown_days'],
            'top_n': STRATEGY_PARAMS['top_n'],
            'transaction_cost': STRATEGY_PARAMS['transaction_cost'],
            'max_single_weight': RISK_PARAMS['max_single_weight'],
            'min_holding': STRATEGY_PARAMS['min_trade_amount'],
        },
        'last_rebalance_date': last_rebalance_date,
        'rows_since_rebalance': rows_since_rebalance,
        'momentum_scores': {k: round(float(v), 1) for k, v in momentum_scores.to_dict().items()},
        'target_weights': {k: round(float(v) * 100, 1) for k, v in target_weights.to_dict().items()},
        'current_weights': {k: round(float(v) * 100, 1) for k, v in current_weights.items()},
        'holdings_detail': holdings_detail,
        'should_rebalance': rebalance_check['rebalance'],
        'reason': rebalance_check['reason'],
        'reason_type': rebalance_check['reason_type'],
        'max_deviation': rebalance_check['detail'].get('max_deviation', 0),
        'avg_deviation': rebalance_check['detail'].get('avg_deviation', 0),
        'total_score': rebalance_check['detail'].get('total_score', 0),
        'strong_signal': rebalance_check['detail'].get('strong_signal', False),
        'stop_loss_trigger': rebalance_check.get('reason_type') == 'stop_loss',
        'stop_loss_assets': rebalance_check.get('stop_loss_assets', []),
        'signals': signals,
        'has_signal': rebalance_check['rebalance'] or len(signals) > 0,
    }

    print('\n__JSON_OUTPUT__')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
'''


def run_daily_task():
    print(f"\n{'=' * 60}")
    print(f"ETF 实盘策略 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print('（使用 Stage7 低回撤正式基线 + 同源回测核心）')
    print(f"{'=' * 60}\n")

    result = subprocess.run(
        [str(PROJECT_PYTHON), '-c', CORE_SCRIPT],
        capture_output=True,
        text=True,
        timeout=300,
    )

    if result.stdout:
        print(result.stdout)
    if result.returncode != 0:
        print('错误:', result.stderr)
        return None

    if '__JSON_OUTPUT__' not in result.stdout:
        print('错误: 未找到 JSON 输出标记')
        return None

    json_str = result.stdout.split('__JSON_OUTPUT__')[-1].strip()
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as exc:
        print(f'解析JSON失败: {exc}')
        return None

    SIGNAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    SIGNAL_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'信号已保存到: {SIGNAL_FILE}')
    return data


if __name__ == '__main__':
    run_daily_task()
