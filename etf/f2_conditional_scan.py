#!/usr/bin/env python3
"""F2: 固定 rsq=15，对其余 4 因子做条件扫描 + Walk-Forward 验证"""
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

# ── F1 新基线: rsq=15 ──
NEW_BASELINE_FW = {
    'momentum_20d': 400, 'momentum_60d': 150, 'momentum_strength': 200,
    'volatility_reward': 50, 'r_squared': 15,
}
OLD_BASELINE_FW = {
    'momentum_20d': 400, 'momentum_60d': 150, 'momentum_strength': 200,
    'volatility_reward': 50, 'r_squared': 30,
}

# ── 扫描网格（加密 + 扩展）──
SCAN_GRID = {
    'momentum_20d':      [100, 150, 200, 250, 300, 350, 400, 500, 600, 700],
    'momentum_60d':      [50, 100, 150, 200, 250, 300, 350, 400, 500],
    'momentum_strength': [0, 50, 100, 150, 200, 250, 300, 400],
    'volatility_reward': [0, 25, 50, 75, 100, 125, 150],
}

BACKTEST_START = '2016-01-01'
BACKTEST_END = '2026-04-27'
TRAIN_RATIO = 0.7
TRAIN_DAYS = 252 * 3
TEST_DAYS = 252
STEP_DAYS = 252


def run_one(fw, prices, start, end):
    s = DailyMonitoringBLM(**BASE, factor_weights=fw)
    s.constraints = CONSTRAINTS
    r = s.backtest(start, end, verbose=False, prices=prices.copy(),
                   return_details=False, record_signals=False)
    return r


def generate_windows(prices, train_days, test_days, step_days):
    windows = []
    dates = prices.index
    n = len(dates)
    i = train_days
    while i + test_days <= n:
        windows.append({
            'train_start': str(dates[0])[:10],
            'train_end': str(dates[i - 1])[:10],
            'test_start': str(dates[i])[:10],
            'test_end': str(dates[min(i + test_days - 1, n - 1)])[:10],
        })
        i += step_days
    return windows


def main():
    print('加载共享价格数据...')
    s0 = DailyMonitoringBLM(**BASE)
    prices = s0.fetch_data(BACKTEST_START, BACKTEST_END)
    print(f'  {len(prices)} 天数据\n')

    # ── Part 1: 全样本 + Train/Test ──
    n = len(prices)
    split_idx = int(n * TRAIN_RATIO)
    train_end = prices.index[split_idx - 1].strftime('%Y-%m-%d')
    test_start = prices.index[split_idx].strftime('%Y-%m-%d')

    print(f'Part 1: 全样本 + Train/Test (rsq=15 固定)')
    print(f'Train: {BACKTEST_START} ~ {train_end} | Test: {test_start} ~ {BACKTEST_END}\n')

    # 新基线
    print('=== 新基线 (rsq=15, 其余不变) ===')
    for phase, s, e in [('全样本', BACKTEST_START, BACKTEST_END),
                         ('Train', BACKTEST_START, train_end),
                         ('Test', test_start, BACKTEST_END)]:
        r = run_one(NEW_BASELINE_FW, prices, s, e)
        print(f'  {phase}: 年化={r["annual_return"]:.2f}%  夏普={r["sharpe_ratio"]:.4f}  '
              f'回撤={r["max_drawdown"]:.2f}%  调仓={r["rebalance_count"]}')

    # 旧基线对比
    print('=== 旧基线 (rsq=30) ===')
    for phase, s, e in [('全样本', BACKTEST_START, BACKTEST_END),
                         ('Train', BACKTEST_START, train_end),
                         ('Test', test_start, BACKTEST_END)]:
        r = run_one(OLD_BASELINE_FW, prices, s, e)
        print(f'  {phase}: 年化={r["annual_return"]:.2f}%  夏普={r["sharpe_ratio"]:.4f}  '
              f'回撤={r["max_drawdown"]:.2f}%  调仓={r["rebalance_count"]}')

    candidates = {}  # 收集 Train/Test 双赢的候选

    for factor, values in SCAN_GRID.items():
        print(f'\n--- {factor} (新基线={NEW_BASELINE_FW[factor]}) ---')
        print(f'{"值":>6} | {"全样本夏普":>9} {"全样本年化":>9} | '
              f'{"Train夏普":>9} {"Test夏普":>9} {"Test年化":>9} | {"评级"}')
        print('-' * 85)

        new_base_test = run_one(NEW_BASELINE_FW, prices, test_start, BACKTEST_END)['sharpe_ratio']
        factor_cands = []

        for v in values:
            fw = dict(NEW_BASELINE_FW)
            fw[factor] = v
            r_full = run_one(fw, prices, BACKTEST_START, BACKTEST_END)
            r_train = run_one(fw, prices, BACKTEST_START, train_end)
            r_test = run_one(fw, prices, test_start, BACKTEST_END)

            train_better = r_train['sharpe_ratio'] > run_one(NEW_BASELINE_FW, prices, BACKTEST_START, train_end)['sharpe_ratio']
            test_better = r_test['sharpe_ratio'] > new_base_test
            test_dd_ok = r_test['max_drawdown'] >= run_one(NEW_BASELINE_FW, prices, test_start, BACKTEST_END)['max_drawdown'] - 3

            if train_better and test_better and test_dd_ok:
                grade = '★★★'
                factor_cands.append((factor, v, fw))
            elif train_better and test_better:
                grade = '★★'
                factor_cands.append((factor, v, fw))
            elif test_better:
                grade = '★'
            else:
                grade = ''

            marker = ' ◄' if v == NEW_BASELINE_FW[factor] else ''
            print(f'{v:>6} | {r_full["sharpe_ratio"]:>9.4f} {r_full["annual_return"]:>8.2f}% | '
                  f'{r_train["sharpe_ratio"]:>9.4f} {r_test["sharpe_ratio"]:>9.4f} {r_test["annual_return"]:>8.2f}% | '
                  f'{grade}{marker}')

        if factor_cands:
            candidates[factor] = factor_cands

    # ── Part 2: Walk-Forward 验证候选 ──
    windows = generate_windows(prices, TRAIN_DAYS, TEST_DAYS, STEP_DAYS)
    print(f'\n\nPart 2: Walk-Forward 验证 ({len(windows)} 窗口)')

    # 始终包含新旧基线
    wf_candidates = {
        'old_baseline': {'desc': '旧基线 rsq=30', 'fw': OLD_BASELINE_FW},
        'new_baseline': {'desc': '新基线 rsq=15', 'fw': NEW_BASELINE_FW},
    }

    # 加入通过 Train/Test 的候选
    for factor, cands in candidates.items():
        for f, v, fw in cands:
            key = f'{f}_{v}'
            if key not in wf_candidates:
                wf_candidates[key] = {'desc': f'{f}={v}', 'fw': fw}

    print(f'候选方案: {list(wf_candidates.keys())}\n')

    wf_results = {}
    for cand_name, cand in wf_candidates.items():
        cand_results = []
        for w in windows:
            r_test = run_one(cand['fw'], prices, w['test_start'], w['test_end'])
            cand_results.append({
                'test_sharpe': round(r_test['sharpe_ratio'], 4),
                'test_annual': round(r_test['annual_return'], 2),
                'test_dd': round(r_test['max_drawdown'], 2),
            })
        wf_results[cand_name] = cand_results

    # Walk-Forward 汇总
    print('=' * 70)
    print('F2 阶段性总结: rsq=15 条件扫描 + Walk-Forward')
    print('=' * 70)

    new_base_wf = wf_results['new_baseline']
    new_base_avg = np.mean([r['test_sharpe'] for r in new_base_wf])
    old_base_wf = wf_results['old_baseline']
    old_base_avg = np.mean([r['test_sharpe'] for r in old_base_wf])

    print(f'\n{"方案":<20} {"avg夏普":>8} {"min夏普":>8} {"avg年化":>8} {"窗口胜出":>8} {"判定"}')
    print('-' * 70)

    # 统计窗口胜出
    wins = {cn: 0 for cn in wf_candidates}
    for i in range(len(windows)):
        best = max(wf_candidates.keys(), key=lambda cn: wf_results[cn][i]['test_sharpe'])
        wins[best] += 1

    for cn in wf_candidates:
        rs = wf_results[cn]
        avg_s = np.mean([r['test_sharpe'] for r in rs])
        min_s = np.min([r['test_sharpe'] for r in rs])
        avg_a = np.mean([r['test_annual'] for r in rs])
        if cn == 'old_baseline':
            verdict = '◄ 旧基线'
        elif cn == 'new_baseline':
            verdict = '◄ 新基线'
        elif avg_s >= new_base_avg and wins[cn] >= 2:
            verdict = '✅ 可采纳'
        elif avg_s >= new_base_avg:
            verdict = '⚠️ 需谨慎'
        else:
            verdict = '❌ 不采纳'
        print(f'{cn:<20} {avg_s:>8.4f} {min_s:>8.4f} {avg_a:>7.2f}% {wins[cn]:>5}/{len(windows)} {verdict}')

    # 逐窗口
    print(f'\n逐窗口 Test 夏普:')
    print(f'{"测试期":<22}', end='')
    for cn in wf_candidates:
        print(f'{cn[:10]:>10}', end='')
    print()
    print('-' * (22 + 10 * len(wf_candidates)))
    for i, w in enumerate(windows):
        period = f'{w["test_start"]}~{w["test_end"][5:]}'
        print(f'{period:<22}', end='')
        for cn in wf_candidates:
            print(f'{wf_results[cn][i]["test_sharpe"]:>10.4f}', end='')
        print()

    # 保存
    output = {
        'phase': 'F2_conditional_scan',
        'new_baseline_fw': NEW_BASELINE_FW,
        'candidates': {cn: wf_candidates[cn]['fw'] for cn in wf_candidates},
        'wf_summary': {cn: {
            'avg_test_sharpe': round(np.mean([r['test_sharpe'] for r in rs]), 4),
            'min_test_sharpe': round(np.min([r['test_sharpe'] for r in rs]), 4),
            'avg_test_annual': round(np.mean([r['test_annual'] for r in rs]), 2),
            'windows_won': wins[cn],
        } for cn, rs in wf_results.items()},
        'wf_detail': {cn: rs for cn, rs in wf_results.items()},
    }
    out_path = '/opt/data/scripts/etf/f2_conditional_scan_results.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f'\n结果已保存: {out_path}')


if __name__ == '__main__':
    main()
