#!/usr/bin/env python3
"""
ETF 策略参数优化与验证
- 全样本网格优化
- 样本内 / 样本外验证
- Walk-forward 滚动验证
"""
import json
import sys
from collections import Counter
from itertools import product

import pandas as pd

sys.path.insert(0, '/opt/data/scripts/etf/windows_backtest_package/core')
from momentum_backtest import DailyMonitoringBLM

# 参数范围
PARAM_GRID = {
    'trigger_deviation': [0.10, 0.15, 0.20, 0.25],
    'lookback_period': [20, 30, 45, 60],
    'cooldown_days': [5, 10, 15, 20],
    'top_n': [2, 3, 4],
}

# 固定参数
FIXED_PARAMS = {
    'initial_capital': 52000,
    'signal_weight': 0.2,
    'stop_loss_threshold': -0.18,
    'transaction_cost': 0.0002,
}

BACKTEST_START = '2016-01-01'
BACKTEST_END = '2026-04-14'
OUTPUT_FILE = '/opt/data/scripts/etf/param_optimization_results.json'
VALIDATION_FILE = '/opt/data/scripts/etf/validation_results.json'


def build_strategy(params):
    return DailyMonitoringBLM(
        initial_capital=FIXED_PARAMS['initial_capital'],
        trigger_deviation=params['trigger_deviation'],
        signal_weight=FIXED_PARAMS['signal_weight'],
        stop_loss_threshold=FIXED_PARAMS['stop_loss_threshold'],
        lookback_period=params['lookback_period'],
        cooldown_days=params['cooldown_days'],
        top_n=params['top_n'],
        transaction_cost=FIXED_PARAMS['transaction_cost'],
    )


def build_param_combinations(param_grid=None):
    grid = param_grid or PARAM_GRID
    return [
        {
            'trigger_deviation': trigger_dev,
            'lookback_period': lookback,
            'cooldown_days': cooldown,
            'top_n': top_n,
        }
        for trigger_dev, lookback, cooldown, top_n in product(
            grid['trigger_deviation'],
            grid['lookback_period'],
            grid['cooldown_days'],
            grid['top_n'],
        )
    ]


def load_shared_prices(start_date=BACKTEST_START, end_date=BACKTEST_END):
    """一次性加载回测区间价格数据，供参数优化复用。"""
    bootstrap_params = {
        'trigger_deviation': PARAM_GRID['trigger_deviation'][0],
        'lookback_period': max(PARAM_GRID['lookback_period']),
        'cooldown_days': PARAM_GRID['cooldown_days'][0],
        'top_n': max(PARAM_GRID['top_n']),
    }
    strategy = build_strategy(bootstrap_params)
    return strategy.fetch_data(start_date, end_date)


def run_backtest(params, shared_prices=None, start_date=BACKTEST_START, end_date=BACKTEST_END):
    """运行单次回测并返回摘要指标。"""
    try:
        strategy = build_strategy(params)
        result = strategy.backtest(
            start_date,
            end_date,
            verbose=False,
            prices=shared_prices,
            return_details=False,
            record_signals=False,
        )
        if not result:
            return None
        return {
            'total_return': result.get('total_return', 0),
            'annual_return': result.get('annual_return', 0),
            'max_drawdown': result.get('max_drawdown', 0),
            'sharpe_ratio': result.get('sharpe_ratio', 0),
            'calmar_ratio': result.get('calmar_ratio', 0),
            'rebalance_count': result.get('rebalance_count', 0),
            'backtest_days': result.get('backtest_days', 0),
            'data_start_date': result.get('data_start_date'),
            'data_end_date': result.get('data_end_date'),
            'requested_start_date': result.get('requested_start_date'),
            'requested_end_date': result.get('requested_end_date'),
        }
    except Exception as e:
        print(f"Error: {e}")
        return None


def rank_results(results, sort_by='sharpe_ratio'):
    reverse = True
    sorted_results = sorted(
        results,
        key=lambda x: (x.get(sort_by, 0), x.get('annual_return', 0), x.get('max_drawdown', -9999)),
        reverse=reverse,
    )
    ranked = []
    for i, item in enumerate(sorted_results, start=1):
        copied = dict(item)
        copied['rank'] = i
        ranked.append(copied)
    return ranked


def evaluate_param_grid(shared_prices, start_date, end_date, param_grid=None, progress=False):
    combinations = build_param_combinations(param_grid)
    results = []
    total = len(combinations)
    for i, params in enumerate(combinations, start=1):
        if progress:
            print(
                f"[{i}/{total}] 偏离度={params['trigger_deviation']:.0%}, 回看={params['lookback_period']}天, "
                f"冷却={params['cooldown_days']}天, 持仓={params['top_n']}只",
                end=' ... ',
            )
        result = run_backtest(params, shared_prices=shared_prices, start_date=start_date, end_date=end_date)
        if result:
            result['params'] = params
            results.append(result)
            if progress:
                print(
                    f"年化={result['annual_return']:.1f}%, 夏普={result['sharpe_ratio']:.2f}, "
                    f"回撤={result['max_drawdown']:.1f}%"
                )
        elif progress:
            print('失败')
    return rank_results(results)


def split_train_test_dates(shared_prices, train_ratio=0.7):
    if shared_prices is None or shared_prices.empty:
        raise ValueError('共享价格数据为空，无法切分样本区间')
    dates = pd.DatetimeIndex(shared_prices.index).sort_values()
    split_idx = int(len(dates) * train_ratio)
    split_idx = min(max(split_idx, 1), len(dates) - 1)
    train_dates = dates[:split_idx]
    test_dates = dates[split_idx:]
    return {
        'train_start': train_dates[0].strftime('%Y-%m-%d'),
        'train_end': train_dates[-1].strftime('%Y-%m-%d'),
        'test_start': test_dates[0].strftime('%Y-%m-%d'),
        'test_end': test_dates[-1].strftime('%Y-%m-%d'),
        'train_days': len(train_dates),
        'test_days': len(test_dates),
    }


def optimize_train_then_evaluate_test(shared_prices, param_grid=None, train_ratio=0.7, top_k=10):
    split = split_train_test_dates(shared_prices, train_ratio=train_ratio)
    train_results = evaluate_param_grid(
        shared_prices,
        split['train_start'],
        split['train_end'],
        param_grid=param_grid,
        progress=False,
    )
    if not train_results:
        raise RuntimeError('训练样本优化失败，没有得到有效结果')
    best_train = train_results[0]
    test_evaluation = run_backtest(
        best_train['params'],
        shared_prices=shared_prices,
        start_date=split['test_start'],
        end_date=split['test_end'],
    )
    return {
        'train_period': split,
        'best_train': best_train,
        'test_evaluation': {
            **test_evaluation,
            'params': best_train['params'],
        },
        'train_top_results': train_results[:top_k],
    }


def generate_walk_forward_windows(shared_prices, train_days=252 * 3, test_days=252, step_days=252):
    if shared_prices is None or shared_prices.empty:
        raise ValueError('共享价格数据为空，无法生成 walk-forward 窗口')
    dates = pd.DatetimeIndex(shared_prices.index).sort_values()
    windows = []
    start_idx = 0
    while start_idx + train_days + test_days <= len(dates):
        train_start = dates[start_idx]
        train_end = dates[start_idx + train_days - 1]
        test_start = dates[start_idx + train_days]
        test_end = dates[start_idx + train_days + test_days - 1]
        windows.append({
            'train_start': train_start.strftime('%Y-%m-%d'),
            'train_end': train_end.strftime('%Y-%m-%d'),
            'test_start': test_start.strftime('%Y-%m-%d'),
            'test_end': test_end.strftime('%Y-%m-%d'),
            'train_days': train_days,
            'test_days': test_days,
        })
        start_idx += step_days
    return windows


def walk_forward_validation(shared_prices, param_grid=None, train_days=252 * 3, test_days=252, step_days=252, top_k=5):
    windows = generate_walk_forward_windows(shared_prices, train_days=train_days, test_days=test_days, step_days=step_days)
    if not windows:
        raise RuntimeError('无法生成有效的 walk-forward 窗口，请调整 train_days/test_days')

    window_results = []
    selected_params = []
    test_sharpes = []
    test_returns = []
    test_drawdowns = []

    for i, window in enumerate(windows, start=1):
        train_results = evaluate_param_grid(
            shared_prices,
            window['train_start'],
            window['train_end'],
            param_grid=param_grid,
            progress=False,
        )
        if not train_results:
            continue
        best_train = train_results[0]
        test_result = run_backtest(
            best_train['params'],
            shared_prices=shared_prices,
            start_date=window['test_start'],
            end_date=window['test_end'],
        )
        if not test_result:
            continue
        params_key = json.dumps(best_train['params'], sort_keys=True, ensure_ascii=False)
        selected_params.append(params_key)
        test_sharpes.append(test_result['sharpe_ratio'])
        test_returns.append(test_result['annual_return'])
        test_drawdowns.append(test_result['max_drawdown'])
        window_results.append({
            'window_index': i,
            'train_period': {
                'start': window['train_start'],
                'end': window['train_end'],
                'days': window['train_days'],
            },
            'test_period': {
                'start': window['test_start'],
                'end': window['test_end'],
                'days': window['test_days'],
            },
            'best_train': best_train,
            'test_result': {
                **test_result,
                'params': best_train['params'],
            },
            'train_top_results': train_results[:top_k],
        })

    param_counter = Counter(selected_params)
    best_params_frequency = [
        {'params': json.loads(params_text), 'count': count}
        for params_text, count in param_counter.most_common()
    ]

    return {
        'summary': {
            'window_count': len(window_results),
            'avg_test_sharpe': round(sum(test_sharpes) / len(test_sharpes), 4) if test_sharpes else None,
            'avg_test_annual_return': round(sum(test_returns) / len(test_returns), 4) if test_returns else None,
            'avg_test_max_drawdown': round(sum(test_drawdowns) / len(test_drawdowns), 4) if test_drawdowns else None,
            'best_params_frequency': best_params_frequency,
        },
        'windows': window_results,
    }


def print_top_results(results, limit=20):
    print(f"\n{'排名':<4} {'偏离度':<8} {'回看':<6} {'冷却':<6} {'持仓':<6} {'年化收益':<10} {'最大回撤':<10} {'夏普比率':<8} {'调仓次数':<8}")
    print('-' * 70)
    for r in results[:limit]:
        p = r['params']
        dev_str = f"{p['trigger_deviation']:.0%}"
        print(
            f"{r['rank']:<4} {dev_str:<8} {p['lookback_period']:<6} {p['cooldown_days']:<6} {p['top_n']:<6} "
            f"{r['annual_return']:>8.1f}% {r['max_drawdown']:>8.1f}% {r['sharpe_ratio']:>8.2f} {r['rebalance_count']:>8}"
        )


def save_json(path, payload):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def main():
    print('=' * 70)
    print('ETF 策略参数优化 + 验证')
    print('=' * 70)

    param_combinations = build_param_combinations(PARAM_GRID)
    print(f"\n共 {len(param_combinations)} 种参数组合")
    print(f"回测区间: {BACKTEST_START} 到 {BACKTEST_END}")
    print('-' * 70)

    shared_prices = load_shared_prices(BACKTEST_START, BACKTEST_END)
    if shared_prices.empty:
        raise RuntimeError('共享价格数据加载失败，无法执行参数优化')
    print(
        f"已预加载共享价格数据: {shared_prices.index.min().strftime('%Y-%m-%d')} ~ "
        f"{shared_prices.index.max().strftime('%Y-%m-%d')}，{len(shared_prices)} 个交易日"
    )

    print('\n开始全样本优化...')
    full_results = evaluate_param_grid(shared_prices, BACKTEST_START, BACKTEST_END, progress=True)
    print('\n' + '=' * 70)
    print('优化结果（按夏普比率排序）')
    print('=' * 70)
    print_top_results(full_results)

    best = full_results[0]
    print('\n' + '=' * 70)
    print('最优参数组合（全样本）')
    print('=' * 70)
    print(f"偏离度阈值: {best['params']['trigger_deviation']:.0%}")
    print(f"回看周期: {best['params']['lookback_period']} 天")
    print(f"冷却期: {best['params']['cooldown_days']} 天")
    print(f"最大持仓数: {best['params']['top_n']} 只")
    print(f"年化收益: {best['annual_return']:.2f}%")
    print(f"最大回撤: {best['max_drawdown']:.2f}%")
    print(f"夏普比率: {best['sharpe_ratio']:.2f}")
    print(f"调仓次数: {best['rebalance_count']}")

    validation = optimize_train_then_evaluate_test(shared_prices, train_ratio=0.7, top_k=10)
    print('\n' + '=' * 70)
    print('样本内 / 样本外验证')
    print('=' * 70)
    print(
        f"训练区间: {validation['train_period']['train_start']} ~ {validation['train_period']['train_end']} "
        f"({validation['train_period']['train_days']} 天)"
    )
    print(
        f"测试区间: {validation['train_period']['test_start']} ~ {validation['train_period']['test_end']} "
        f"({validation['train_period']['test_days']} 天)"
    )
    print(f"训练最优参数: {validation['best_train']['params']}")
    print(
        f"样本外表现: 年化={validation['test_evaluation']['annual_return']:.2f}%, "
        f"夏普={validation['test_evaluation']['sharpe_ratio']:.2f}, "
        f"回撤={validation['test_evaluation']['max_drawdown']:.2f}%"
    )

    walk_forward = walk_forward_validation(shared_prices, train_days=252 * 3, test_days=252, step_days=126, top_k=3)
    print('\n' + '=' * 70)
    print('Walk-forward 汇总')
    print('=' * 70)
    print(f"窗口数量: {walk_forward['summary']['window_count']}")
    print(f"平均样本外夏普: {walk_forward['summary']['avg_test_sharpe']}")
    print(f"平均样本外年化: {walk_forward['summary']['avg_test_annual_return']}")
    print(f"平均样本外最大回撤: {walk_forward['summary']['avg_test_max_drawdown']}")
    if walk_forward['summary']['best_params_frequency']:
        print(f"最常出现参数: {walk_forward['summary']['best_params_frequency'][0]}")

    save_json(
        OUTPUT_FILE,
        {
            'best_params': best['params'],
            'best_performance': {k: v for k, v in best.items() if k != 'params'},
            'all_results': full_results[:50],
        },
    )
    save_json(
        VALIDATION_FILE,
        {
            'train_test_validation': validation,
            'walk_forward_validation': walk_forward,
        },
    )
    print(f"\n优化结果已保存到: {OUTPUT_FILE}")
    print(f"验证结果已保存到: {VALIDATION_FILE}")


if __name__ == '__main__':
    main()
