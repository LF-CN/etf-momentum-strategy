#!/usr/bin/env python3
"""双引擎一致性验证：用完全相同的价格数据和参数，对比 AkShare vs Windows 引擎输出"""
import sys, os, time

# ── 导入双引擎 ──
sys.path.insert(0, '/opt/data/scripts/AkShare/策略执行')
from momentum_backtest import DailyMonitoringBLM as AkEngine

sys.path.insert(0, '/opt/data/scripts/etf/windows_backtest_package/core')
from momentum_backtest import DailyMonitoringBLM as WinEngine

# ── 共用参数 ──
KW = dict(
    initial_capital=52000, trigger_deviation=0.24,
    signal_weight=0.20, stop_loss_threshold=-0.18,
    lookback_period=30, cooldown_days=20,
    top_n=3, transaction_cost=0.0002,
    factor_weights={'momentum_20d': 425, 'momentum_60d': 175,
                    'momentum_strength': 200, 'volatility_reward': 75, 'r_squared': 30}
)
START, END = '2016-01-01', '2026-04-27'

# ── 加载价格（用 AkEngine 取数，两个引擎用同一份） ──
print("加载价格数据...")
loader = AkEngine(**KW)
prices = loader.fetch_data(START, END)
print(f"  维度: {prices.shape}, 范围: {prices.index[0].date()} ~ {prices.index[-1].date()}")

# ── AkShare 引擎 ──
t0 = time.time()
ak = AkEngine(**KW)
ak.constraints['max_single_weight'] = 0.325
r_ak = ak.backtest(START, END, verbose=False, prices=prices.copy(),
                   return_details=False, record_signals=False)
t_ak = time.time() - t0

# ── Windows 引擎 ──
t0 = time.time()
win = WinEngine(**KW)
win.constraints['max_single_weight'] = 0.325
r_win = win.backtest(START, END, verbose=False, prices=prices.copy(),
                     return_details=False, record_signals=False)
t_win = time.time() - t0

# ── 对比 ──
print(f"\n{'指标':<20} {'AkShare':>10} {'Windows':>10} {'差异':>10}")
print("-" * 55)
for k in ['annual_return', 'sharpe_ratio', 'max_drawdown', 'rebalance_count', 'total_return']:
    v1 = r_ak.get(k, 0)
    v2 = r_win.get(k, 0)
    diff = v1 - v2
    print(f"{k:<20} {v1:>9.3f} {v2:>9.3f} {diff:>9.3f}")

print(f"\n耗时: AkShare={t_ak:.1f}s  Windows={t_win:.1f}s")
print(f"结论: {'✓ 一致' if abs(r_ak.get('sharpe_ratio',0)-r_win.get('sharpe_ratio',0))<0.001 else '✗ 不一致!'}")
