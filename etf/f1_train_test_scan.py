#!/usr/bin/env python3
"""F1 因子权重扫描 - Phase 2: Top-3 敏感因子 Train/Test 验证"""
import sys, time, json
sys.path.insert(0, '/opt/data/scripts/etf/windows_backtest_package/core')
from momentum_backtest import DailyMonitoringBLM
import pandas as pd
import numpy as np

# ── 基线参数 ──
BASE = dict(
    initial_capital=52000, trigger_deviation=0.20, signal_weight=0.2,
    stop_loss_threshold=-0.18, lookback_period=30, cooldown_days=20,
    top_n=3, transaction_cost=0.0002,
)
CONSTRAINTS = {'max_single_weight': 0.325, 'min_holding': 1000}
BASELINE_FW = {
    'momentum_20d': 400, 'momentum_60d': 150, 'momentum_strength': 200,
    'volatility_reward': 50, 'r_squared': 30,
}

# ── Top-3 敏感因子 + 细化网格（围绕F1最优值加密）──
SCAN_GRID = {
    'momentum_20d': [100, 150, 200, 250, 300, 350, 400, 500, 600, 700],
    'volatility_reward': [0, 25, 50, 75, 100, 125, 150],
    'r_squared': [0, 15, 30, 45, 60, 75, 90],
}

TRAIN_RATIO = 0.7
BACKTEST_START = '2016-01-01'
BACKTEST_END = '2026-04-27'


def run_one(fw, prices, start, end):
    s = DailyMonitoringBLM(**BASE, factor_weights=fw)
    s.constraints = CONSTRAINTS
    r = s.backtest(start, end, verbose=False, prices=prices.copy(),
                   return_details=False, record_signals=False)
    return r


def main():
    print('加载共享价格数据...')
    s0 = DailyMonitoringBLM(**BASE)
    prices = s0.fetch_data(BACKTEST_START, BACKTEST_END)
    print(f'  {len(prices)} 天数据\n')

    # Train/Test 切分
    n = len(prices)
    split_idx = int(n * TRAIN_RATIO)
    train_end = prices.index[split_idx - 1].strftime('%Y-%m-%d')
    test_start = prices.index[split_idx].strftime('%Y-%m-%d')
    print(f'Train: {BACKTEST_START} ~ {train_end} ({split_idx} 天)')
    print(f'Test:  {test_start} ~ {BACKTEST_END} ({n - split_idx} 天)\n')

    # 先跑基线
    print('=== 基线 ===')
    for phase, s, e in [('Train', BACKTEST_START, train_end), ('Test', test_start, BACKTEST_END)]:
        r = run_one(BASELINE_FW, prices, s, e)
        print(f'  {phase}: 年化={r["annual_return"]:.2f}%  夏普={r["sharpe_ratio"]:.4f}  '
              f'回撤={r["max_drawdown"]:.2f}%  调仓={r["rebalance_count"]}')

    all_results = {}

    for factor, values in SCAN_GRID.items():
        print(f'\n--- {factor} (基线={BASELINE_FW[factor]}) ---')
        print(f'{"值":>6} | {"Train夏普":>9} {"Train年化":>9} {"Train回撤":>9} | '
              f'{"Test夏普":>9} {"Test年化":>9} {"Test回撤":>9} | {"评级"}')
        print('-' * 95)

        factor_results = []
        for v in values:
            fw = dict(BASELINE_FW)
            fw[factor] = v
            r_train = run_one(fw, prices, BACKTEST_START, train_end)
            r_test = run_one(fw, prices, test_start, BACKTEST_END)

            # 评级逻辑
            base_train = run_one(BASELINE_FW, prices, BACKTEST_START, train_end)
            base_test = run_one(BASELINE_FW, prices, test_start, BACKTEST_END)
            train_better = r_train['sharpe_ratio'] > base_train['sharpe_ratio']
            test_better = r_test['sharpe_ratio'] > base_test['sharpe_ratio']
            test_dd_ok = r_test['max_drawdown'] >= base_test['max_drawdown'] - 3  # 回撤不比基线差3%以上

            if train_better and test_better and test_dd_ok:
                grade = '★★★'
            elif train_better and test_better:
                grade = '★★'
            elif test_better:
                grade = '★'
            else:
                grade = ''

            marker = ' ◄' if v == BASELINE_FW[factor] else ''
            print(f'{v:>6} | {r_train["sharpe_ratio"]:>9.4f} {r_train["annual_return"]:>8.2f}% {r_train["max_drawdown"]:>8.2f}% | '
                  f'{r_test["sharpe_ratio"]:>9.4f} {r_test["annual_return"]:>8.2f}% {r_test["max_drawdown"]:>8.2f}% | {grade}{marker}')

            factor_results.append({
                'factor': factor, 'value': v,
                'train_sharpe': round(r_train['sharpe_ratio'], 4),
                'train_annual': round(r_train['annual_return'], 2),
                'train_dd': round(r_train['max_drawdown'], 2),
                'test_sharpe': round(r_test['sharpe_ratio'], 4),
                'test_annual': round(r_test['annual_return'], 2),
                'test_dd': round(r_test['max_drawdown'], 2),
                'grade': grade,
            })

        all_results[factor] = factor_results

    # 保存
    output = {
        'phase': 'F1_train_test',
        'train_period': {'start': BACKTEST_START, 'end': train_end},
        'test_period': {'start': test_start, 'end': BACKTEST_END},
        'results': all_results,
    }
    out_path = '/opt/data/scripts/etf/f1_train_test_results.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f'\n结果已保存: {out_path}')

    # ── 阶段性总结 ──
    print('\n' + '=' * 60)
    print('Phase 2 阶段性总结: Train/Test 验证')
    print('=' * 60)

    for factor, results in all_results.items():
        print(f'\n【{factor}】')
        # 找 Train 最优
        best_train = max(results, key=lambda r: r['train_sharpe'])
        # 找 Test 最优
        best_test = max(results, key=lambda r: r['test_sharpe'])
        # 找★★★
        stars3 = [r for r in results if '★★★' in r['grade']]
        stars2 = [r for r in results if '★★' in r['grade'] and '★★★' not in r['grade']]

        print(f'  Train最优: 值={best_train["value"]} 夏普={best_train["train_sharpe"]:.4f} '
              f'→ Test夏普={best_train["test_sharpe"]:.4f}')
        print(f'  Test最优:  值={best_test["value"]} 夏普={best_test["test_sharpe"]:.4f}')
        if stars3:
            print(f'  ★★★ 候选: {", ".join(str(r["value"]) for r in stars3)}')
        if stars2:
            print(f'  ★★  候选: {", ".join(str(r["value"]) for r in stars2)}')

    # 跨因子对比
    print(f'\n{"因子":<20} {"Train最优→Test夏普":>20} {"★★★候选":>10} {"结论"}')
    print('-' * 70)
    for factor, results in all_results.items():
        best_train = max(results, key=lambda r: r['train_sharpe'])
        stars3 = [r for r in results if '★★★' in r['grade']]
        train_test_gap = best_train['test_sharpe'] - best_train['train_sharpe']
        if stars3:
            conclusion = '样本外成立 ✅'
        elif best_train['test_sharpe'] > 0:
            conclusion = '样本外尚可 ⚠️'
        else:
            conclusion = '样本外失败 ❌'
        s3_vals = ','.join(str(r['value']) for r in stars3) if stars3 else '-'
        print(f'{factor:<20} {best_train["test_sharpe"]:>20.4f} {s3_vals:>10} {conclusion}')


if __name__ == '__main__':
    main()
