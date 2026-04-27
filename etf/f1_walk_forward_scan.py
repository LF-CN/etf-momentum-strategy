#!/usr/bin/env python3
"""F1 因子权重扫描 - Phase 3: Walk-Forward 验证候选因子"""
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

# ── 候选方案 ──
CANDIDATES = {
    'baseline': {
        'desc': '基线 (400/150/200/50/30)',
        'fw': {'momentum_20d': 400, 'momentum_60d': 150, 'momentum_strength': 200,
               'volatility_reward': 50, 'r_squared': 30},
    },
    'vol_25': {
        'desc': 'volatility_reward=25',
        'fw': {'momentum_20d': 400, 'momentum_60d': 150, 'momentum_strength': 200,
               'volatility_reward': 25, 'r_squared': 30},
    },
    'rsq_15': {
        'desc': 'r_squared=15',
        'fw': {'momentum_20d': 400, 'momentum_60d': 150, 'momentum_strength': 200,
               'volatility_reward': 50, 'r_squared': 15},
    },
    'combined': {
        'desc': 'vol=25 + rsq=15 组合',
        'fw': {'momentum_20d': 400, 'momentum_60d': 150, 'momentum_strength': 200,
               'volatility_reward': 25, 'r_squared': 15},
    },
}

BACKTEST_START = '2016-01-01'
BACKTEST_END = '2026-04-27'
TRAIN_DAYS = 252 * 3  # 3年训练
TEST_DAYS = 252       # 1年测试
STEP_DAYS = 252       # 步长1年


def run_one(fw, prices, start, end):
    s = DailyMonitoringBLM(**BASE, factor_weights=fw)
    s.constraints = CONSTRAINTS
    r = s.backtest(start, end, verbose=False, prices=prices.copy(),
                   return_details=False, record_signals=False)
    return r


def generate_windows(prices, train_days, test_days, step_days):
    """生成 Walk-Forward 窗口"""
    windows = []
    dates = prices.index
    n = len(dates)
    i = train_days
    while i + test_days <= n:
        train_start = dates[0]
        train_end = dates[i - 1]
        test_start = dates[i]
        test_end = dates[min(i + test_days - 1, n - 1)]
        windows.append({
            'train_start': str(train_start)[:10],
            'train_end': str(train_end)[:10],
            'test_start': str(test_start)[:10],
            'test_end': str(test_end)[:10],
        })
        i += step_days
    return windows


def main():
    print('加载共享价格数据...')
    s0 = DailyMonitoringBLM(**BASE)
    prices = s0.fetch_data(BACKTEST_START, BACKTEST_END)
    print(f'  {len(prices)} 天数据\n')

    windows = generate_windows(prices, TRAIN_DAYS, TEST_DAYS, STEP_DAYS)
    print(f'Walk-Forward: {len(windows)} 个窗口 (3年Train + 1年Test, 步长1年)\n')

    for w in windows:
        print(f'  {w["train_start"]}~{w["train_end"]} → {w["test_start"]}~{w["test_end"]}')
    print()

    # ── 逐窗口逐候选跑回测 ──
    all_results = {}
    for cand_name, cand in CANDIDATES.items():
        print(f'=== {cand_name}: {cand["desc"]} ===')
        cand_results = []
        for w in windows:
            r_train = run_one(cand['fw'], prices, w['train_start'], w['train_end'])
            r_test = run_one(cand['fw'], prices, w['test_start'], w['test_end'])
            cand_results.append({
                'window': w,
                'train_sharpe': round(r_train['sharpe_ratio'], 4),
                'train_annual': round(r_train['annual_return'], 2),
                'test_sharpe': round(r_test['sharpe_ratio'], 4),
                'test_annual': round(r_test['annual_return'], 2),
                'test_dd': round(r_test['max_drawdown'], 2),
            })
            print(f'  {w["test_start"]}~{w["test_end"]}: '
                  f'Train夏普={r_train["sharpe_ratio"]:.4f} → '
                  f'Test夏普={r_test["sharpe_ratio"]:.4f}  '
                  f'Test年化={r_test["annual_return"]:.2f}%  '
                  f'Test回撤={r_test["max_drawdown"]:.2f}%')
        all_results[cand_name] = cand_results
        print()

    # ── Walk-Forward 汇总 ──
    print('=' * 70)
    print('Phase 3 阶段性总结: Walk-Forward 验证')
    print('=' * 70)

    summary = {}
    for cand_name, results in all_results.items():
        test_sharpes = [r['test_sharpe'] for r in results]
        test_annuals = [r['test_annual'] for r in results]
        test_dds = [r['test_dd'] for r in results]
        summary[cand_name] = {
            'desc': CANDIDATES[cand_name]['desc'],
            'avg_test_sharpe': round(np.mean(test_sharpes), 4),
            'min_test_sharpe': round(np.min(test_sharpes), 4),
            'avg_test_annual': round(np.mean(test_annuals), 2),
            'avg_test_dd': round(np.mean(test_dds), 2),
            'worst_dd': round(np.min(test_dds), 2),
            'windows_won': 0,  # vs baseline
        }

    # 统计每个窗口谁胜出
    baseline_results = all_results['baseline']
    for i in range(len(windows)):
        best_name = max(all_results.keys(),
                       key=lambda cn: all_results[cn][i]['test_sharpe'])
        if best_name == 'baseline':
            # 检查是否并列
            base_s = baseline_results[i]['test_sharpe']
            for cn in all_results:
                if cn != 'baseline' and all_results[cn][i]['test_sharpe'] >= base_s:
                    summary[cn]['windows_won'] += 1
        else:
            summary[best_name]['windows_won'] += 1

    # 汇总表
    print(f'\n{"方案":<12} {"avgTest夏普":>10} {"minTest夏普":>10} {"avgTest年化":>10} '
          f'{"avgTest回撤":>10} {"窗口胜出":>8} {"判定"}')
    print('-' * 80)

    base_avg = summary['baseline']['avg_test_sharpe']
    for cand_name, s in summary.items():
        vs_base = s['avg_test_sharpe'] - base_avg
        if cand_name == 'baseline':
            verdict = '◄ 基线'
        elif s['avg_test_sharpe'] >= base_avg and s['windows_won'] >= 2:
            verdict = '✅ 可采纳'
        elif s['avg_test_sharpe'] >= base_avg:
            verdict = '⚠️ 需谨慎'
        else:
            verdict = '❌ 不采纳'
        print(f'{cand_name:<12} {s["avg_test_sharpe"]:>10.4f} {s["min_test_sharpe"]:>10.4f} '
              f'{s["avg_test_annual"]:>9.2f}% {s["avg_test_dd"]:>9.2f}% '
              f'{s["windows_won"]:>5}/{len(windows)} {verdict}')

    # 逐窗口对比
    print(f'\n逐窗口 Test 夏普对比:')
    print(f'{"测试期":<22}', end='')
    for cn in CANDIDATES:
        print(f'{cn:>10}', end='')
    print('  胜出')
    print('-' * 65)
    for i, w in enumerate(windows):
        period = f'{w["test_start"]}~{w["test_end"]}'
        print(f'{period:<22}', end='')
        vals = {}
        for cn in CANDIDATES:
            v = all_results[cn][i]['test_sharpe']
            vals[cn] = v
            print(f'{v:>10.4f}', end='')
        winner = max(vals, key=lambda k: vals[k])
        print(f'  {winner}')

    # 保存
    output = {
        'phase': 'F1_walk_forward',
        'windows': windows,
        'summary': summary,
        'detail': {cn: results for cn, results in all_results.items()},
    }
    out_path = '/opt/data/scripts/etf/f1_walk_forward_results.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f'\n结果已保存: {out_path}')


if __name__ == '__main__':
    main()
