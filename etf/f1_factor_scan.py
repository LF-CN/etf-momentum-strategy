#!/usr/bin/env python3
"""F1 因子权重单变量扫描 - Phase 1: 全样本初筛"""
import sys, time, json
sys.path.insert(0, '/opt/data/scripts/etf/windows_backtest_package/core')
from momentum_backtest import DailyMonitoringBLM
import pandas as pd

# ── 基线参数（已验证，不动）──
BASE = dict(
    initial_capital=52000, trigger_deviation=0.20, signal_weight=0.2,
    stop_loss_threshold=-0.18, lookback_period=30, cooldown_days=20,
    top_n=3, transaction_cost=0.0002,
)
CONSTRAINTS = {'max_single_weight': 0.325, 'min_holding': 1000}

# ── 基线因子权重 ──
BASELINE_FW = {
    'momentum_20d': 400,
    'momentum_60d': 150,
    'momentum_strength': 200,
    'volatility_reward': 50,
    'r_squared': 30,
}

# ── 扫描网格 ──
SCAN_GRID = {
    'momentum_20d':      [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000],
    'momentum_60d':      [50, 100, 150, 200, 250, 300, 350, 400, 450, 500],
    'momentum_strength': [0, 50, 100, 150, 200, 250, 300, 350, 400],
    'volatility_reward': [0, 25, 50, 75, 100, 125, 150, 175, 200],
    'r_squared':         [0, 15, 30, 45, 60, 75, 90, 105, 120, 135, 150],
}

BACKTEST_START = '2016-01-01'
BACKTEST_END = '2026-04-27'


def run_one(fw, prices):
    s = DailyMonitoringBLM(**BASE, factor_weights=fw)
    s.constraints = CONSTRAINTS
    r = s.backtest(BACKTEST_START, BACKTEST_END, verbose=False, prices=prices.copy(),
                   return_details=False, record_signals=False)
    return r


def main():
    print('加载共享价格数据...')
    s0 = DailyMonitoringBLM(**BASE)
    prices = s0.fetch_data(BACKTEST_START, BACKTEST_END)
    print(f'  {len(prices)} 天数据\n')

    # 先跑基线
    print('=== 基线 (默认因子权重) ===')
    r0 = run_one(BASELINE_FW, prices)
    print(f'  年化={r0["annual_return"]:.2%}  夏普={r0["sharpe_ratio"]:.4f}  '
          f'回撤={r0["max_drawdown"]:.2%}  调仓={r0["rebalance_count"]}\n')

    all_results = {}

    for factor, values in SCAN_GRID.items():
        print(f'--- 扫描因子: {factor} (基线={BASELINE_FW[factor]}) ---')
        factor_results = []
        for v in values:
            fw = dict(BASELINE_FW)
            fw[factor] = v
            t0 = time.time()
            r = run_one(fw, prices)
            elapsed = time.time() - t0
            marker = ' ◄基线' if v == BASELINE_FW[factor] else ''
            print(f'  {factor}={v:>4}: 年化={r["annual_return"]:>7.2f}%  '
                  f'夏普={r["sharpe_ratio"]:.4f}  '
                  f'回撤={r["max_drawdown"]:>7.2f}%  '
                  f'调仓={r["rebalance_count"]:>3}  '
                  f'({elapsed:.1f}s){marker}')
            factor_results.append({
                'factor': factor, 'value': v,
                'annual_return': round(r['annual_return'], 4),
                'sharpe_ratio': round(r['sharpe_ratio'], 4),
                'max_drawdown': round(r['max_drawdown'], 4),
                'rebalance_count': r['rebalance_count'],
            })
        all_results[factor] = factor_results
        print()

    # 保存结果
    output = {
        'phase': 'F1_full_sample',
        'baseline': {k: round(v, 4) if isinstance(v, float) else v for k, v in r0.items()
                     if k in ('annual_return', 'sharpe_ratio', 'max_drawdown', 'rebalance_count')},
        'baseline_fw': BASELINE_FW,
        'scan_results': all_results,
    }
    out_path = '/opt/data/scripts/etf/f1_factor_scan_results.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f'结果已保存: {out_path}')

    # ── 阶段性总结 ──
    print('\n' + '=' * 60)
    print('F1 全样本初筛 - 因子敏感性排行')
    print('=' * 60)
    sensitivity = []
    for factor, results in all_results.items():
        sharpes = [r['sharpe_ratio'] for r in results]
        best = max(results, key=lambda r: r['sharpe_ratio'])
        worst = min(results, key=lambda r: r['sharpe_ratio'])
        spread = best['sharpe_ratio'] - worst['sharpe_ratio']
        baseline_r = [r for r in results if r['value'] == BASELINE_FW[factor]][0]
        sensitivity.append({
            'factor': factor,
            'best_sharpe': best['sharpe_ratio'],
            'best_value': best['value'],
            'worst_sharpe': worst['sharpe_ratio'],
            'spread': spread,
            'baseline_sharpe': baseline_r['sharpe_ratio'],
            'vs_baseline': best['sharpe_ratio'] - baseline_r['sharpe_ratio'],
        })

    sensitivity.sort(key=lambda x: x['spread'], reverse=True)
    print(f'{"因子":<20} {"夏普范围":>10} {"最优值":>6} {"vs基线":>8} {"敏感度"}')
    print('-' * 65)
    for s in sensitivity:
        bar = '█' * int(s['spread'] * 40)
        print(f'{s["factor"]:<20} {s["spread"]:>8.4f} {s["best_value"]:>6} '
              f'{s["vs_baseline"]:>+8.4f} {bar}')

    print(f'\n基线: 年化={r0["annual_return"]:.2f}%  夏普={r0["sharpe_ratio"]:.4f}  '
          f'回撤={r0["max_drawdown"]:.2f}%')


if __name__ == '__main__':
    main()
