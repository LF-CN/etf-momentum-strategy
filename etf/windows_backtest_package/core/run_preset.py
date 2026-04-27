#!/usr/bin/env python3
from __future__ import annotations
import json
import sys
from pathlib import Path
from itertools import product
from collections import Counter
from datetime import datetime
import pandas as pd

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from momentum_backtest import DailyMonitoringBLM

DEFAULT_START = '2016-01-01'
DEFAULT_END = datetime.now().strftime('%Y-%m-%d')


def load_json(path: Path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_strategy(params: dict, constraints: dict | None = None):
    strategy = DailyMonitoringBLM(
        initial_capital=params.get('initial_capital', 52000),
        trigger_deviation=params.get('trigger_deviation', 0.20),
        signal_weight=params.get('signal_weight', 0.20),
        stop_loss_threshold=params.get('stop_loss_threshold', -0.18),
        lookback_period=params.get('lookback_period', 30),
        cooldown_days=params.get('cooldown_days', 20),
        top_n=params.get('top_n', 3),
        transaction_cost=params.get('transaction_cost', 0.0002),
        factor_weights=params.get('factor_weights'),
        style_factors=params.get('style_factors'),
    )
    merged_constraints = {
        'max_single_weight': 0.325,
        'min_holding': 1000,
    }
    if constraints:
        merged_constraints.update(constraints)
    strategy.constraints = merged_constraints
    return strategy


def load_shared_prices(base_params: dict, constraints: dict, start_date: str, end_date: str):
    strategy = build_strategy(base_params, constraints)
    return strategy.fetch_data(start_date, end_date)


def run_single(params: dict, constraints: dict, shared_prices=None, start_date=DEFAULT_START, end_date=DEFAULT_END):
    strategy = build_strategy(params, constraints)
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
        'annual_volatility': result.get('annual_volatility', 0),
        'sharpe_ratio': result.get('sharpe_ratio', 0),
        'calmar_ratio': result.get('calmar_ratio', 0),
        'rebalance_count': result.get('rebalance_count', 0),
        'backtest_days': result.get('backtest_days', 0),
        'data_start_date': result.get('data_start_date'),
        'data_end_date': result.get('data_end_date'),
        'requested_start_date': result.get('requested_start_date'),
        'requested_end_date': result.get('requested_end_date'),
    }


def build_combinations(base_params: dict, base_constraints: dict, param_grid: dict, constraint_grid: dict):
    items = []
    for k, vals in (param_grid or {}).items():
        items.append(('param', k, vals))
    for k, vals in (constraint_grid or {}).items():
        items.append(('constraint', k, vals))
    if not items:
        return [{'params': dict(base_params), 'constraints': dict(base_constraints)}]
    value_lists = [vals for _, _, vals in items]
    combos = []
    for values in product(*value_lists):
        params = dict(base_params)
        constraints = dict(base_constraints)
        for (kind, key, _), value in zip(items, values):
            if kind == 'param':
                params[key] = value
            else:
                constraints[key] = value
        combos.append({'params': params, 'constraints': constraints})
    return combos


def rank_results(results, sort_by='sharpe_ratio'):
    sorted_results = sorted(
        results,
        key=lambda x: (x.get(sort_by, 0), x.get('annual_return', 0), x.get('max_drawdown', -9999)),
        reverse=True,
    )
    ranked = []
    for i, item in enumerate(sorted_results, start=1):
        copied = dict(item)
        copied['rank'] = i
        ranked.append(copied)
    return ranked


def split_train_test_dates(shared_prices, train_ratio=0.7):
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


def evaluate_grid(combos, shared_prices, start_date, end_date, progress=False):
    results = []
    total = len(combos)
    for i, combo in enumerate(combos, start=1):
        if progress:
            print(f'[{i}/{total}] params={combo["params"]} constraints={combo["constraints"]}', flush=True)
        result = run_single(combo['params'], combo['constraints'], shared_prices, start_date, end_date)
        if result:
            result['params'] = combo['params']
            result['constraints'] = combo['constraints']
            results.append(result)
            if progress:
                print(f"  -> 年化={result['annual_return']:.2f}% 夏普={result['sharpe_ratio']:.2f} 回撤={result['max_drawdown']:.2f}%", flush=True)
    return rank_results(results)


def train_test_validation(combos, shared_prices, train_ratio=0.7, top_k=5):
    split = split_train_test_dates(shared_prices, train_ratio)
    train_results = evaluate_grid(combos, shared_prices, split['train_start'], split['train_end'], progress=False)
    best_train = train_results[0]
    test_result = run_single(best_train['params'], best_train['constraints'], shared_prices, split['test_start'], split['test_end'])
    return {
        'train_period': split,
        'best_train': best_train,
        'test_evaluation': {**test_result, 'params': best_train['params'], 'constraints': best_train['constraints']},
        'train_top_results': train_results[:top_k],
    }


def generate_walk_forward_windows(shared_prices, train_days=252*3, test_days=252, step_days=252):
    dates = pd.DatetimeIndex(shared_prices.index).sort_values()
    windows = []
    start_idx = 0
    while start_idx + train_days + test_days <= len(dates):
        windows.append({
            'train_start': dates[start_idx].strftime('%Y-%m-%d'),
            'train_end': dates[start_idx + train_days - 1].strftime('%Y-%m-%d'),
            'test_start': dates[start_idx + train_days].strftime('%Y-%m-%d'),
            'test_end': dates[start_idx + train_days + test_days - 1].strftime('%Y-%m-%d'),
            'train_days': train_days,
            'test_days': test_days,
        })
        start_idx += step_days
    return windows


def walk_forward_validation(combos, shared_prices, train_days=252*3, test_days=252, step_days=252, top_k=3):
    windows = generate_walk_forward_windows(shared_prices, train_days, test_days, step_days)
    selected = []
    all_windows = []
    sharpes, returns, drawdowns = [], [], []
    for idx, window in enumerate(windows, start=1):
        train_results = evaluate_grid(combos, shared_prices, window['train_start'], window['train_end'], progress=False)
        if not train_results:
            continue
        best_train = train_results[0]
        test_result = run_single(best_train['params'], best_train['constraints'], shared_prices, window['test_start'], window['test_end'])
        if not test_result:
            continue
        selected.append(json.dumps({'params': best_train['params'], 'constraints': best_train['constraints']}, sort_keys=True))
        sharpes.append(test_result['sharpe_ratio'])
        returns.append(test_result['annual_return'])
        drawdowns.append(test_result['max_drawdown'])
        all_windows.append({
            'window_index': idx,
            'train_period': window,
            'best_train': best_train,
            'test_result': {**test_result, 'params': best_train['params'], 'constraints': best_train['constraints']},
            'train_top_results': train_results[:top_k],
        })
    freq = []
    for raw, count in Counter(selected).most_common(10):
        parsed = json.loads(raw)
        freq.append({'params': parsed['params'], 'constraints': parsed['constraints'], 'count': count})
    return {
        'summary': {
            'window_count': len(all_windows),
            'avg_test_sharpe': round(sum(sharpes)/len(sharpes), 4) if sharpes else 0,
            'avg_test_annual_return': round(sum(returns)/len(returns), 4) if returns else 0,
            'avg_test_max_drawdown': round(sum(drawdowns)/len(drawdowns), 4) if drawdowns else 0,
            'best_params_frequency': freq,
        },
        'windows': all_windows,
    }


def main():
    if len(sys.argv) < 2:
        print('用法: python core/run_preset.py presets/xxx.json')
        raise SystemExit(1)
    preset_path = Path(sys.argv[1]).resolve()
    preset = load_json(preset_path)
    name = preset.get('name', preset_path.stem)
    mode = preset.get('mode', 'parameter_grid_scan')
    base_params = preset.get('base_params', {})
    base_constraints = preset.get('base_constraints', {})
    start_date = preset.get('start_date', DEFAULT_START)
    end_date = preset.get('end_date', DEFAULT_END)
    validation = preset.get('validation', {})
    combos = build_combinations(base_params, base_constraints, preset.get('param_grid', {}), preset.get('constraint_grid', {}))

    print(f'加载共享价格数据: {start_date} ~ {end_date}', flush=True)
    shared_prices = load_shared_prices(base_params, base_constraints, start_date, end_date)
    print(f'组合数量: {len(combos)}', flush=True)

    full_results = evaluate_grid(combos, shared_prices, start_date, end_date, progress=True)
    output = {
        'preset_name': name,
        'mode': mode,
        'start_date': start_date,
        'end_date': end_date,
        'base_params': base_params,
        'base_constraints': base_constraints,
        'param_grid': preset.get('param_grid', {}),
        'constraint_grid': preset.get('constraint_grid', {}),
        'full_sample_top10': full_results[:10],
        'full_sample_all_count': len(full_results),
    }

    if validation.get('train_test', True):
        output['train_test_validation'] = train_test_validation(
            combos,
            shared_prices,
            validation.get('train_ratio', 0.7),
            validation.get('train_top_k', 5),
        )

    if validation.get('walk_forward', True):
        output['walk_forward_validation'] = walk_forward_validation(
            combos,
            shared_prices,
            validation.get('train_days', 252*3),
            validation.get('test_days', 252),
            validation.get('step_days', 252),
            validation.get('wf_top_k', 3),
        )

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_path = PACKAGE_ROOT / 'results' / f'{preset_path.stem}_{timestamp}.json'
    save_json(out_path, output)
    latest_path = PACKAGE_ROOT / 'results' / f'{preset_path.stem}_latest.json'
    save_json(latest_path, output)
    print(f'结果已保存: {out_path}')
    print(f'最新副本: {latest_path}')


if __name__ == '__main__':
    main()
