#!/usr/bin/env python3
"""
ETF 实盘策略服务（与回测策略完全一致）
使用 uv run 调用完整版策略代码
"""
import subprocess
import json
import sys
from pathlib import Path

# 项目路径
ETF_PROJECT = Path('/opt/data/scripts/etf')
BACKTEST_PROJECT = Path('/opt/data/scripts/etf/windows_backtest_package/core')
sys.path.insert(0, str(ETF_PROJECT))

from config import ETF_POOL, STRATEGY_PARAMS, RISK_PARAMS


def run_strategy_with_data(prices_df, current_weights, current_shares=None, entry_prices=None):
    """
    使用完整版策略代码计算信号
    
    Args:
        prices_df: pandas DataFrame，价格为列，日期为索引
        current_weights: 当前权重字典
        current_shares: 当前持仓股数
        entry_prices: 入场价格
    
    Returns:
        dict: 策略分析结果
    """
    import pandas as pd
    import numpy as np
    import sys
    sys.path.insert(0, str(BACKTEST_PROJECT))
    
    # 导入回测策略类
    from momentum_backtest import DailyMonitoringBLM
    
    # 创建策略实例（使用相同参数）
    strategy = DailyMonitoringBLM(
        initial_capital=STRATEGY_PARAMS.get('initial_capital', 49197.60),
        trigger_deviation=STRATEGY_PARAMS['trigger_deviation'],
        signal_weight=STRATEGY_PARAMS['signal_weight'],
        stop_loss_threshold=STRATEGY_PARAMS['stop_loss_threshold'],
        lookback_period=STRATEGY_PARAMS['lookback_period'],
        cooldown_days=STRATEGY_PARAMS['cooldown_days'],
        top_n=STRATEGY_PARAMS['top_n'],
        transaction_cost=STRATEGY_PARAMS['transaction_cost'],
        factor_weights=STRATEGY_PARAMS.get('factor_weights'),
    )
    strategy.constraints = {
        'max_single_weight': RISK_PARAMS['max_single_weight'],
        'min_holding': STRATEGY_PARAMS['min_trade_amount'],
    }
    
    # 使用最新的日期进行分析
    latest_date = prices_df.index[-1]
    
    # 计算目标权重
    target_weights = strategy.calculate_BLM_weights(prices_df, latest_date)
    
    # 获取动量得分
    momentum_scores = strategy.calculate_momentum_score(prices_df, latest_date)
    
    # 检查是否需要调仓
    total_value = 0.0
    latest_prices = prices_df.iloc[-1]
    current_shares = current_shares or {}
    for code, shares in current_shares.items():
        total_value += float(shares or 0) * float(latest_prices.get(code, 0) or 0)

    rebalance_check = strategy.check_trigger_conditions(
        prices_df,
        latest_date,
        pd.Series(current_weights),
        target_weights,
        current_shares,
        total_value,
        entry_prices or {},
        rows_since_rebalance=999,
    )
    
    return {
        'date': latest_date.strftime('%Y-%m-%d'),
        'momentum_scores': momentum_scores.to_dict(),
        'target_weights': target_weights.to_dict(),
        'current_weights': current_weights,
        'rebalance_check': rebalance_check,
        'has_signal': rebalance_check.get('rebalance', False)
    }


def get_historical_klines(days=100):
    """
    获取历史K线数据
    
    Returns:
        pandas DataFrame
    """
    import urllib.request
    import json
    from datetime import datetime, timedelta
    import pandas as pd
    
    all_data = {}
    
    for code in ETF_POOL.keys():
        # 使用新浪财经历史数据API
        # 根据代码判断市场
        if code.startswith('51') or code.startswith('58') or code.startswith('511'):
            secid = f'sh{code}'
        else:
            secid = f'sz{code}'
        
        url = f'https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketDataService.getKLineData?symbol={secid}&scale=240&datalen={days}'
        
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0',
                'Referer': 'https://finance.sina.com.cn'
            })
            with urllib.request.urlopen(req, timeout=15) as response:
                text = response.read().decode('gbk')
                # 解析JSON
                if text and text != 'null':
                    data = json.loads(text)
                    if data:
                        dates = []
                        closes = []
                        for item in data:
                            dates.append(datetime.strptime(item['day'], '%Y-%m-%d'))
                            closes.append(float(item['close']))
                        
                        if dates:
                            all_data[code] = pd.Series(closes, index=dates)
                            print(f"  ✓ {ETF_POOL[code]['name']}: {len(dates)}天数据")
        except Exception as e:
            print(f"  ✗ {ETF_POOL[code]['name']}: 获取失败 - {e}")
    
    if all_data:
        return pd.DataFrame(all_data).sort_index()
    return None


if __name__ == '__main__':
    print('使用完整版策略计算实盘信号...')
    print('（与回测策略完全一致）')
