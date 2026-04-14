#!/usr/bin/env python3
"""
ETF 策略参数优化
测试不同参数组合，找出最优配置
"""
import pandas as pd
import numpy as np
import sys
from datetime import datetime
from itertools import product
import json

sys.path.insert(0, '/opt/data/scripts/AkShare/策略执行')
from momentum_backtest import DailyMonitoringBLM

# 参数范围
PARAM_GRID = {
    'trigger_deviation': [0.10, 0.15, 0.20, 0.25],  # 偏离度阈值
    'lookback_period': [20, 30, 45, 60],            # 回看周期
    'cooldown_days': [5, 10, 15, 20],               # 冷却期
    'top_n': [2, 3, 4],                             # 最大持仓数
}

# 固定参数
FIXED_PARAMS = {
    'initial_capital': 52000,
    'signal_weight': 0.2,
    'stop_loss_threshold': -0.18,
    'transaction_cost': 0.0002,
}

def run_backtest(params):
    """运行单次回测"""
    try:
        strategy = DailyMonitoringBLM(
            initial_capital=FIXED_PARAMS['initial_capital'],
            trigger_deviation=params['trigger_deviation'],
            signal_weight=FIXED_PARAMS['signal_weight'],
            stop_loss_threshold=FIXED_PARAMS['stop_loss_threshold'],
            lookback_period=params['lookback_period'],
            cooldown_days=params['cooldown_days'],
            top_n=params['top_n'],
            transaction_cost=FIXED_PARAMS['transaction_cost']
        )
        
        # 运行回测（silent模式）
        result = strategy.backtest('2016-01-01', '2026-04-14', verbose=False)
        
        if not result:
            return None
        
        return {
            'total_return': result.get('total_return', 0),
            'annual_return': result.get('annual_return', 0),
            'max_drawdown': result.get('max_drawdown', 0),
            'sharpe_ratio': result.get('sharpe_ratio', 0),
            'rebalance_count': result.get('rebalance_count', 0),
            'data_start_date': result.get('data_start_date'),
            'data_end_date': result.get('data_end_date'),
            'requested_start_date': result.get('requested_start_date'),
            'requested_end_date': result.get('requested_end_date'),
        }
    except Exception as e:
        print(f"Error: {e}")
        return None

def main():
    print("=" * 70)
    print("ETF 策略参数优化")
    print("=" * 70)
    
    # 生成参数组合
    param_combinations = list(product(
        PARAM_GRID['trigger_deviation'],
        PARAM_GRID['lookback_period'],
        PARAM_GRID['cooldown_days'],
        PARAM_GRID['top_n']
    ))
    
    print(f"\n共 {len(param_combinations)} 种参数组合")
    print(f"回测区间: 2016-01-01 到 2026-04-14 (约10年)")
    print("-" * 70)
    
    results = []
    
    for i, (trigger_dev, lookback, cooldown, top_n) in enumerate(param_combinations):
        params = {
            'trigger_deviation': trigger_dev,
            'lookback_period': lookback,
            'cooldown_days': cooldown,
            'top_n': top_n,
        }
        
        print(f"[{i+1}/{len(param_combinations)}] 偏离度={trigger_dev:.0%}, 回看={lookback}天, 冷却={cooldown}天, 持仓={top_n}只", end=" ... ")
        
        result = run_backtest(params)
        
        if result:
            result['params'] = params
            results.append(result)
            print(f"年化={result['annual_return']:.1f}%, 夏普={result['sharpe_ratio']:.2f}, 回撤={result['max_drawdown']:.1f}%")
        else:
            print("失败")
    
    # 排序结果
    print("\n" + "=" * 70)
    print("优化结果（按夏普比率排序）")
    print("=" * 70)
    
    results_sorted = sorted(results, key=lambda x: x['sharpe_ratio'], reverse=True)
    
    print(f"\n{'排名':<4} {'偏离度':<8} {'回看':<6} {'冷却':<6} {'持仓':<6} {'年化收益':<10} {'最大回撤':<10} {'夏普比率':<8} {'调仓次数':<8}")
    print("-" * 70)
    
    for i, r in enumerate(results_sorted[:20]):  # 显示前20名
        p = r['params']
        print(f"{i+1:<4} {p['trigger_deviation']:.0%:<8} {p['lookback_period']:<6} {p['cooldown_days']:<6} {p['top_n']:<6} "
              f"{r['annual_return']:>8.1f}% {r['max_drawdown']:>8.1f}% {r['sharpe_ratio']:>8.2f} {r['rebalance_count']:>8}")
    
    # 最优参数
    best = results_sorted[0]
    print("\n" + "=" * 70)
    print("最优参数组合")
    print("=" * 70)
    print(f"偏离度阈值: {best['params']['trigger_deviation']:.0%}")
    print(f"回看周期: {best['params']['lookback_period']} 天")
    print(f"冷却期: {best['params']['cooldown_days']} 天")
    print(f"最大持仓数: {best['params']['top_n']} 只")
    print()
    print(f"年化收益: {best['annual_return']:.2f}%")
    print(f"最大回撤: {best['max_drawdown']:.2f}%")
    print(f"夏普比率: {best['sharpe_ratio']:.2f}")
    print(f"调仓次数: {best['rebalance_count']}")
    
    # 保存结果
    output_file = '/opt/data/scripts/etf/param_optimization_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'best_params': best['params'],
            'best_performance': {k: v for k, v in best.items() if k != 'params'},
            'all_results': results_sorted[:50]
        }, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存到: {output_file}")

if __name__ == '__main__':
    main()
