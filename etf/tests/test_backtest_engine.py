import sys

import numpy as np
import pandas as pd

sys.path.insert(0, '/opt/data/scripts/etf/windows_backtest_package/core')
sys.path.insert(0, '/opt/data/scripts/etf')

from momentum_backtest import DailyMonitoringBLM
import param_optimization


def make_prices(periods=1400):
    dates = pd.bdate_range('2020-01-01', periods=periods)
    x = np.linspace(0, 1, periods)
    data = {
        '510500': 100 * (1 + 0.18 * x),
        '159941': 100 * (1 + 0.32 * x + 0.02 * np.sin(np.linspace(0, 8, periods))),
        '518880': 100 * (1 + 0.10 * x + 0.01 * np.cos(np.linspace(0, 6, periods))),
        '511010': 100 * (1 + 0.05 * x),
        '159928': 100 * (1 + 0.12 * x + 0.015 * np.sin(np.linspace(0, 10, periods))),
    }
    df = pd.DataFrame(data, index=dates)
    df.index.name = 'date'
    return df


def build_strategy():
    strategy = DailyMonitoringBLM(
        initial_capital=52000,
        trigger_deviation=0.20,
        signal_weight=0.20,
        stop_loss_threshold=-0.18,
        lookback_period=30,
        cooldown_days=20,
        top_n=3,
        transaction_cost=0.0002,
    )
    strategy.constraints = {
        'max_single_weight': 0.35,
        'min_holding': 1000,
    }
    return strategy


def test_backtest_uses_supplied_prices_without_fetching():
    prices = make_prices(periods=180)
    strategy = build_strategy()

    def fail_fetch(*args, **kwargs):
        raise AssertionError('fetch_data should not be called when prices are supplied')

    strategy.fetch_data = fail_fetch

    result = strategy.backtest(
        '2020-01-01',
        '2020-07-31',
        verbose=False,
        prices=prices,
        return_details=False,
        record_signals=False,
    )

    assert result['requested_start_date'] == '2020-01-01'
    assert result['requested_end_date'] == '2020-07-31'
    assert result['rebalance_count'] >= 1
    assert 'trades' not in result
    assert 'nav_history' not in result
    assert strategy.signals_log == []


def test_backtest_resets_internal_state_between_runs():
    prices = make_prices(periods=180)
    strategy = build_strategy()

    first = strategy.backtest(
        '2020-01-01',
        '2020-07-31',
        verbose=False,
        prices=prices,
        return_details=False,
        record_signals=False,
    )
    first_rebalance_count = first['rebalance_count']

    strategy.rebalance_history.append({'date': pd.Timestamp('2024-12-31'), 'reason': '污染'})
    strategy.signals_log.append({'date': pd.Timestamp('2024-12-31')})

    second = strategy.backtest(
        '2020-01-01',
        '2020-07-31',
        verbose=False,
        prices=prices,
        return_details=False,
        record_signals=False,
    )

    assert second['rebalance_count'] == first_rebalance_count
    assert len(strategy.rebalance_history) == second['rebalance_count']
    assert strategy.signals_log == []



def test_param_optimization_run_backtest_accepts_shared_prices():
    prices = make_prices(periods=260)
    params = {
        'trigger_deviation': 0.20,
        'lookback_period': 30,
        'cooldown_days': 20,
        'top_n': 3,
    }

    original_build_strategy = param_optimization.build_strategy

    def wrapped_build_strategy(local_params):
        strategy = original_build_strategy(local_params)

        def fail_fetch(*args, **kwargs):
            raise AssertionError('run_backtest should reuse shared_prices and skip fetch_data')

        strategy.fetch_data = fail_fetch
        return strategy

    param_optimization.build_strategy = wrapped_build_strategy
    try:
        result = param_optimization.run_backtest(
            params,
            shared_prices=prices,
            start_date='2020-01-01',
            end_date='2020-11-30',
        )
    finally:
        param_optimization.build_strategy = original_build_strategy

    assert result is not None
    assert result['rebalance_count'] >= 1
    assert 'trades' not in result
    assert 'nav_history' not in result


def test_split_dates_produces_contiguous_is_oos_ranges():
    prices = make_prices(periods=900)
    split = param_optimization.split_train_test_dates(prices, train_ratio=0.7)

    assert split['train_start'] < split['train_end'] < split['test_start'] <= split['test_end']
    assert split['train_days'] + split['test_days'] == len(prices)



def test_optimize_train_then_evaluate_test_returns_ranked_results():
    prices = make_prices(periods=900)
    grid = {
        'trigger_deviation': [0.15, 0.20],
        'lookback_period': [30],
        'cooldown_days': [10, 20],
        'top_n': [3],
    }

    result = param_optimization.optimize_train_then_evaluate_test(prices, param_grid=grid, train_ratio=0.7)

    assert result['best_train']['rank'] == 1
    assert result['train_period']['train_days'] > result['train_period']['test_days']
    assert len(result['train_top_results']) >= 1
    assert result['test_evaluation']['params'] == result['best_train']['params']
    assert 'annual_return' in result['test_evaluation']



def test_generate_walk_forward_windows_returns_multiple_windows():
    prices = make_prices(periods=1400)
    windows = param_optimization.generate_walk_forward_windows(
        prices,
        train_days=252 * 2,
        test_days=126,
        step_days=126,
    )

    assert len(windows) >= 2
    for window in windows:
        assert window['train_start'] < window['train_end'] < window['test_start'] <= window['test_end']



def test_walk_forward_validation_summarizes_windows():
    prices = make_prices(periods=1400)
    grid = {
        'trigger_deviation': [0.15, 0.20],
        'lookback_period': [30],
        'cooldown_days': [10],
        'top_n': [3],
    }

    result = param_optimization.walk_forward_validation(
        prices,
        param_grid=grid,
        train_days=252 * 2,
        test_days=126,
        step_days=126,
        top_k=2,
    )

    assert result['summary']['window_count'] >= 2
    assert len(result['windows']) == result['summary']['window_count']
    assert 'avg_test_sharpe' in result['summary']
    assert 'best_params_frequency' in result['summary']
