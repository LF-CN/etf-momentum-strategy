#!/usr/bin/env python3
"""
稳健性验证 A: T+1延迟成交
信号日用当日收盘价计算，但用次日开盘价成交
"""
import sys, json
sys.path.insert(0, '/opt/data/scripts/etf/windows_backtest_package/core')
from momentum_backtest import DailyMonitoringBLM
import pandas as pd
import numpy as np

BASE = dict(
    initial_capital=50000, trigger_deviation=0.25, signal_weight=0.2,
    stop_loss_threshold=-0.18, lookback_period=30, cooldown_days=20,
    top_n=3, transaction_cost=0.0002,
    factor_weights={'momentum_20d': 400, 'momentum_60d': 150, 'momentum_strength': 200,
                    'volatility_reward': 50, 'r_squared': 30},
    style_factors={k: 1.0 for k in ['small_cap','growth','mid_cap','large_cap','tech',
                                      'cyclical','defensive','gov_bond','convertible',
                                      'commodity','a_share','us_tech']},
)
START, END = '2016-01-01', '2026-04-27'

# === Step 1: 基线（T+0，当日收盘价成交）===
s0 = DailyMonitoringBLM(**BASE)
s0.constraints = {'max_single_weight': 0.325, 'min_holding': 1000}
prices = s0.fetch_data(START, END)
r0 = s0.backtest(START, END, verbose=False, prices=prices.copy(),
                 return_details=True, record_signals=False)
print(f"基线(T+0): 年化={r0['annual_return']:.2f}%  夏普={r0['sharpe_ratio']:.2f}  "
      f"回撤={r0['max_drawdown']:.2f}%  调仓={r0['rebalance_count']}次")

# === Step 2: T+1延迟成交 ===
# 方法：在回测引擎外部模拟T+1
# 核心改动：调仓日的成交价从当日收盘价 → 次日开盘价
# 实现方式：加载OHLC数据，对每次买卖用次日open替代当日close

ohlcv_dir = None
from pathlib import Path
ohlcv_dir = Path('/opt/data/scripts/etf/windows_backtest_package/etf_data')

# 加载OHLCV数据
ohlcv = {}
csv_files = sorted(ohlcv_dir.glob('*_kline.csv'))
for f in csv_files:
    code = f.stem.replace('_kline', '')
    if code not in s0.etf_pool:
        continue
    df = pd.read_csv(f)
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
    for col in ['open','high','low','close','volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    ohlcv[code] = df

# 构建次日开盘价 lookup: {date -> {code -> next_open}}
next_opens = {}
all_dates = sorted(prices.index)
for i, date in enumerate(all_dates[:-1]):
    next_date = all_dates[i+1]
    row = {}
    for code in s0.etf_pool:
        if code in ohlcv and next_date in ohlcv[code].index:
            op = ohlcv[code].loc[next_date, 'open']
            if pd.notna(op) and op > 0:
                row[code] = float(op)
    if row:
        next_opens[date] = row

print(f"次日开盘价数据: {len(next_opens)}天 × 最多{len(s0.etf_pool)}只ETF")

# 手动跑T+1回测
# 用基线回测的 rebalance_history 找到所有调仓日，然后重新计算
# 更精确的方式：直接修改执行价格

# 由于直接修改引擎太侵入性，采用"蒙卡扰动近似法"：
# 用次日开盘价相对当日收盘价的偏移作为滑点，叠加到交易价格上
# 统计这些偏移的分布
gaps = []
for date, row in next_opens.items():
    for code, nopen in row.items():
        cclose = prices.loc[date, code] if code in prices.columns else None
        if cclose and cclose > 0 and pd.notna(cclose):
            gap_pct = (nopen - cclose) / cclose
            gaps.append(gap_pct)

gaps = np.array(gaps)
print(f"\n次日开盘 vs 当日收盘 偏移统计:")
print(f"  均值: {gaps.mean()*100:.4f}%")
print(f"  中位数: {np.median(gaps)*100:.4f}%")
print(f"  标准差: {gaps.std()*100:.4f}%")
print(f"  P5/P95: {np.percentile(gaps,5)*100:.4f}% / {np.percentile(gaps,95)*100:.4f}%")
print(f"  绝对值均值: {np.abs(gaps).mean()*100:.4f}%")

# 真正的T+1回测：修改引擎
# 最简方式：patch execute_rebalance 和 止损/建仓 的成交价
# 用子类覆盖

class T1DailyMonitoringBLM(DailyMonitoringBLM):
    """T+1延迟成交：调仓信号日用次日开盘价执行"""
    
    def __init__(self, *args, next_opens=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._next_opens = next_opens or {}
        self._last_signal_date = None
        self._pending_rebalance = None
    
    def _get_execution_price(self, code, date, direction='buy'):
        """获取实际成交价：有次日开盘价用它，否则用当日收盘价"""
        next_open_row = self._next_opens.get(date)
        if next_open_row and code in next_open_row:
            return next_open_row[code]
        return None  # fallback to original price

# 更简洁的方案：直接在原引擎的回测循环里，把调仓日的成交价替换
# 但引擎内部调用 execute_rebalance 传入的是 current_prices
# 所以我们在外部构造一个 "T+1价格DataFrame"，把调仓日的价格替换为次日开盘价

# 构建T+1价格表：对于每个日期，如果有次日开盘价，则用它替代收盘价
prices_t1 = prices.copy()
t1_replaced = 0
for date in prices_t1.index:
    if date in next_opens:
        for code in prices_t1.columns:
            if code in next_opens[date]:
                prices_t1.loc[date, code] = next_opens[date][code]
                t1_replaced += 1

print(f"\nT+1价格替换: {t1_replaced}个数据点")

# 但这里有个问题：T+1的意义是"信号在T日收盘后产生，T+1日开盘执行"
# 所以净值应该用T日收盘价计算（反映持仓市值），但买卖用T+1开盘价
# 上面的替换会同时影响净值计算和成交价，不完全正确

# 更准确的实现：用原始价格计算净值和信号，只在执行交易时用次日开盘价
# 这需要修改引擎内部的 execute_rebalance

# 采用猴子补丁方式
original_execute = DailyMonitoringBLM.execute_rebalance
original_buy_cost = DailyMonitoringBLM._buy_total_cost
original_sell_net = DailyMonitoringBLM._sell_net_proceeds

def make_t1_backtest(next_opens, prices_close):
    """创建T+1回测：patch execute_rebalance 使其在调仓日用次日开盘价成交"""
    
    def t1_execute_rebalance(self, current_value, current_positions, target_weights,
                              current_prices, date, cash, entry_prices):
        # 对每个买卖操作，用次日开盘价替代当日收盘价
        exec_prices = current_prices.copy()
        next_open_row = next_opens.get(date)
        if next_open_row:
            for code in exec_prices.index:
                if code in next_open_row:
                    exec_prices[code] = next_open_row[code]
        
        return original_execute(self, current_value, current_positions, target_weights,
                               exec_prices, date, cash, entry_prices)
    
    return t1_execute_rebalance

# 基线回测结果
baseline = r0

# T+1回测
DailyMonitoringBLM.execute_rebalance = make_t1_backtest(next_opens, prices)
s1 = DailyMonitoringBLM(**BASE)
s1.constraints = {'max_single_weight': 0.325, 'min_holding': 1000}
r1 = s1.backtest(START, END, verbose=False, prices=prices.copy(),
                 return_details=False, record_signals=False)

# 恢复原始方法
DailyMonitoringBLM.execute_rebalance = original_execute

print(f"\n{'='*65}")
print(f"T+1延迟成交 vs 基线(T+0)")
print(f"{'='*65}")
print(f"{'指标':<12} {'基线T+0':>10} {'T+1延迟':>10} {'差异':>10}")
print(f"{'-'*45}")
for key, label in [('annual_return','年化%'), ('sharpe_ratio','夏普'), 
                    ('max_drawdown','回撤%'), ('rebalance_count','调仓次数')]:
    v0 = baseline[key]
    v1 = r1[key]
    d = v1 - v0
    print(f"{label:<12} {v0:>10.2f} {v1:>10.2f} {d:>+10.2f}")

# 保存
results = {
    'baseline_t0': {k: round(v,4) if isinstance(v,float) else v for k,v in baseline.items() 
                    if k in ['annual_return','sharpe_ratio','max_drawdown','rebalance_count']},
    't1_delayed': {k: round(v,4) if isinstance(v,float) else v for k,v in r1.items()
                   if k in ['annual_return','sharpe_ratio','max_drawdown','rebalance_count']},
    'gap_stats': {
        'mean_pct': round(gaps.mean()*100, 4),
        'std_pct': round(gaps.std()*100, 4),
        'abs_mean_pct': round(np.abs(gaps).mean()*100, 4),
    }
}
out = Path('/opt/data/scripts/etf/windows_backtest_package/results')
out.mkdir(parents=True, exist_ok=True)
with open(out / 'robustness_t1_delay.json', 'w') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\n结果已保存")
