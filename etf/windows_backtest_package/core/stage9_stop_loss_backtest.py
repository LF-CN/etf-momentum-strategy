#!/usr/bin/env python3
"""
Stage9 止损策略升级回测
分步实施：baseline → ATR → Trailing → Momentum Decay → 组合
"""
from __future__ import annotations
import sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from momentum_backtest import DailyMonitoringBLM
import pandas as pd
import numpy as np

# ============ 基线参数 ============
BASE_PARAMS = {
    'initial_capital': 52000,
    'trigger_deviation': 0.24,
    'signal_weight': 0.2,
    'stop_loss_threshold': -0.18,
    'lookback_period': 30,
    'cooldown_days': 20,
    'top_n': 3,
    'transaction_cost': 0.0002,
    'factor_weights': {
        'momentum_20d': 425, 'momentum_60d': 175,
        'momentum_strength': 200, 'volatility_reward': 75, 'r_squared': 30,
    },
    'style_factors': {
        'small_cap': 1.0, 'growth': 1.0, 'mid_cap': 1.0, 'large_cap': 1.0,
        'tech': 1.0, 'cyclical': 1.0, 'defensive': 1.0, 'gov_bond': 1.0,
        'convertible': 1.0, 'commodity': 1.0, 'a_share': 1.0, 'us_tech': 1.0,
    },
}
BASE_CONSTRAINTS = {'max_single_weight': 0.325, 'min_holding': 1000}
START_DATE = '2016-01-01'
END_DATE = '2026-04-27'


def build_strategy(stop_loss_config=None):
    s = DailyMonitoringBLM(
        initial_capital=BASE_PARAMS['initial_capital'],
        trigger_deviation=BASE_PARAMS['trigger_deviation'],
        signal_weight=BASE_PARAMS['signal_weight'],
        stop_loss_threshold=BASE_PARAMS['stop_loss_threshold'],
        lookback_period=BASE_PARAMS['lookback_period'],
        cooldown_days=BASE_PARAMS['cooldown_days'],
        top_n=BASE_PARAMS['top_n'],
        transaction_cost=BASE_PARAMS['transaction_cost'],
        factor_weights=BASE_PARAMS['factor_weights'],
        style_factors=BASE_PARAMS['style_factors'],
    )
    s.constraints = {**BASE_CONSTRAINTS}
    if stop_loss_config:
        s.stop_loss_config = stop_loss_config
    return s


def run_one(prices, mode, stop_loss_config=None):
    """跑一次回测，返回关键指标"""
    s = build_strategy(stop_loss_config)
    r = s.backtest(START_DATE, END_DATE, verbose=False, prices=prices,
                   return_details=False, record_signals=False)
    return {
        'mode': mode,
        'annual_return': r['annual_return'],
        'sharpe_ratio': r['sharpe_ratio'],
        'max_drawdown': r['max_drawdown'],
        'rebalance_count': r['rebalance_count'],
    }


def print_results(results, baseline=None):
    print(f"\n{'='*80}")
    print(f"{'Mode':<25} {'年化%':>7} {'夏普':>7} {'回撤%':>8} {'调仓':>5} {'Δ夏普':>8} {'Δ回撤':>8}")
    print(f"{'-'*80}")
    b = baseline or results[0]
    for r in results:
        ds = r['sharpe_ratio'] - b['sharpe_ratio']
        dd = r['max_drawdown'] - b['max_drawdown']
        s_mark = "✓" if ds > 0.03 else ("✗" if ds < -0.03 else "")
        d_mark = "✓" if dd > 0.3 else ("✗" if dd < -0.3 else "")
        print(f"{r['mode']:<25} {r['annual_return']:>7.2f} {r['sharpe_ratio']:>7.3f} "
              f"{r['max_drawdown']:>8.2f} {r['rebalance_count']:>5} "
              f"{ds:>+7.3f}{s_mark:>2} {dd:>+7.2f}{d_mark:>2}")
    print(f"{'='*80}")


# ============ 各步测试配置 ============

def step1_baseline(prices):
    """Step1: baseline 对照组"""
    print("\n" + "="*40)
    print("Step1: Baseline 对照组")
    print("="*40)
    r = run_one(prices, 'baseline')
    print_results([r])
    expected = {'annual_return': 16.45, 'sharpe_ratio': 1.197, 'max_drawdown': -12.79}
    ok = (abs(r['annual_return'] - expected['annual_return']) < 0.5 and
          abs(r['sharpe_ratio'] - expected['sharpe_ratio']) < 0.02 and
          abs(r['max_drawdown'] - expected['max_drawdown']) < 0.5)
    print(f"基线验证: {'PASS ✓' if ok else 'FAIL ✗'}")
    return r


def step2_atr(prices, baseline):
    """Step2: ATR 自适应止损"""
    print("\n" + "="*40)
    print("Step2: ATR 自适应止损")
    print("="*40)
    configs = [
        ('baseline', None),
        ('ATR 1.5x', {'atr_stop': {'atr_period': 20, 'atr_multiplier': 1.5}}),
        ('ATR 2.0x', {'atr_stop': {'atr_period': 20, 'atr_multiplier': 2.0}}),
        ('ATR 2.5x', {'atr_stop': {'atr_period': 20, 'atr_multiplier': 2.5}}),
        ('ATR 3.0x', {'atr_stop': {'atr_period': 20, 'atr_multiplier': 3.0}}),
        ('ATR14 2.0x', {'atr_stop': {'atr_period': 14, 'atr_multiplier': 2.0}}),
    ]
    results = []
    t0 = time.time()
    for mode, cfg in configs:
        r = run_one(prices, mode, cfg)
        results.append(r)
    t1 = time.time()
    print(f"\n总耗时: {t1-t0:.1f}s")
    print_results(results, baseline)
    return results


def step3_trailing(prices, baseline):
    """Step3: Trailing Stop"""
    print("\n" + "="*40)
    print("Step3: Trailing Stop")
    print("="*40)
    configs = [
        ('baseline', None),
        ('Trail 5%', {'trailing_stop': {'trail_pct': 0.05}}),
        ('Trail 8%', {'trailing_stop': {'trail_pct': 0.08}}),
        ('Trail 10%', {'trailing_stop': {'trail_pct': 0.10}}),
        ('Trail 8%+锁利', {'trailing_stop': {'trail_pct': 0.08, 'lock_profit': True}}),
    ]
    results = []
    t0 = time.time()
    for mode, cfg in configs:
        r = run_one(prices, mode, cfg)
        results.append(r)
    t1 = time.time()
    print(f"\n总耗时: {t1-t0:.1f}s")
    print_results(results, baseline)
    return results


def step4_momentum_decay(prices, baseline):
    """Step4: 动量衰减止损"""
    print("\n" + "="*40)
    print("Step4: 动量衰减止损")
    print("="*40)
    configs = [
        ('baseline', None),
        ('Mom<30', {'momentum_decay_stop': {'score_threshold': 30}}),
        ('Mom<25', {'momentum_decay_stop': {'score_threshold': 25}}),
        ('Mom<20', {'momentum_decay_stop': {'score_threshold': 20}}),
        ('Mom<15', {'momentum_decay_stop': {'score_threshold': 15}}),
    ]
    results = []
    t0 = time.time()
    for mode, cfg in configs:
        r = run_one(prices, mode, cfg)
        results.append(r)
    t1 = time.time()
    print(f"\n总耗时: {t1-t0:.1f}s")
    print_results(results, baseline)
    return results


def step5_combo(prices, baseline, best_atr, best_trail, best_mom):
    """Step5: 组合测试"""
    print("\n" + "="*40)
    print("Step5: 组合测试（用前几步最优参数）")
    print("="*40)
    configs = [
        ('baseline', None),
        ('ATR+Trail', {**best_atr, **best_trail}),
        ('ATR+Mom', {**best_atr, **best_mom}),
        ('Trail+Mom', {**best_trail, **best_mom}),
        ('ATR+Trail+Mom', {**best_atr, **best_trail, **best_mom}),
    ]
    results = []
    t0 = time.time()
    for mode, cfg in configs:
        r = run_one(prices, mode, cfg)
        results.append(r)
    t1 = time.time()
    print(f"\n总耗时: {t1-t0:.1f}s")
    print_results(results, baseline)
    return results


def main():
    print("Stage9 止损策略升级回测")
    print(f"区间: {START_DATE} ~ {END_DATE}")
    
    # 加载数据
    s = build_strategy()
    prices = s.fetch_data(START_DATE, END_DATE)
    print(f"数据: {len(prices)} 天\n")

    # Step1
    baseline = step1_baseline(prices)
    
    # Step2
    step2_atr(prices, baseline)
    
    # Step3
    step3_trailing(prices, baseline)
    
    # Step4
    step4_momentum_decay(prices, baseline)
    
    # Step5 (先用默认最优参数)
    step5_combo(prices, baseline,
                best_atr={'atr_stop': {'atr_period': 20, 'atr_multiplier': 2.0}},
                best_trail={'trailing_stop': {'trail_pct': 0.08}},
                best_mom={'momentum_decay_stop': {'score_threshold': 25}})


if __name__ == '__main__':
    main()
