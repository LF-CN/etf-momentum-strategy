#!/usr/bin/env python3
"""
Phase 1: 因子消融测试（使用 Windows 引擎 + 正确数据源）
逐个删除1个因子（权重=0），其余保持原始值，看夏普变化。
"""
import sys, os, time
sys.path.insert(0, '/opt/data/scripts/etf/windows_backtest_package/core')
from momentum_backtest import DailyMonitoringBLM

SHARED_KWARGS = dict(
    initial_capital=52000, trigger_deviation=0.24,
    signal_weight=0.20, stop_loss_threshold=-0.18,
    lookback_period=30, cooldown_days=20,
    top_n=3, transaction_cost=0.0002,
)

BASELINE_FW = {
    'momentum_20d': 425, 'momentum_60d': 175,
    'momentum_strength': 200, 'volatility_reward': 75,
    'r_squared': 30,
}

START, END = '2016-01-01', '2026-04-27'

# ── 测试配置 ──
TESTS = [
    ('0_基线',           BASELINE_FW),
    ('1_删20日动量',      {**BASELINE_FW, 'momentum_20d': 0}),
    ('2_删60日动量',      {**BASELINE_FW, 'momentum_60d': 0}),
    ('3_删动量强度',      {**BASELINE_FW, 'momentum_strength': 0}),
    ('4_删波动率',        {**BASELINE_FW, 'volatility_reward': 0}),
    ('5_删R²',           {**BASELINE_FW, 'r_squared': 0}),
]

print('=' * 75)
print('Phase 1: 因子消融测试（Windows引擎）')
print('=' * 75)

# ── 加载共享价格 ──
print('\n[1/2] 加载历史价格数据...')
t0 = time.time()
loader = DailyMonitoringBLM(**SHARED_KWARGS, factor_weights=BASELINE_FW)
prices = loader.fetch_data(START, END)
print(f'      数据维度: {prices.shape}，耗时 {time.time()-t0:.1f}s')

# ── 逐组回测 ──
print(f'\n[2/2] 运行 {len(TESTS)} 组回测...\n')
results = []

for name, fw in TESTS:
    bt = DailyMonitoringBLM(**SHARED_KWARGS, factor_weights=fw)
    bt.constraints = {'max_single_weight': 0.325, 'min_holding': 1000}
    t1 = time.time()
    r = bt.backtest(START, END, verbose=False, prices=prices.copy(),
                    return_details=False, record_signals=False)
    results.append({
        'name': name,
        'annual': r.get('annual_return', 0),
        'sharpe': r.get('sharpe_ratio', 0),
        'drawdown': r.get('max_drawdown', 0),
        'trades': r.get('rebalance_count', 0),
        'vol': r.get('annual_volatility', 0),
        'total_ret': r.get('total_return', 0),
        'time': time.time() - t1,
    })

# ── 输出对比表 ──
print(f'{"配置":<20} {"年化%":>8} {"夏普":>7} {"Δ夏普":>7} {"回撤%":>8} {"总收益%":>8} {"调仓":>5} {"波动%":>8} {"耗时":>6}')
print('-' * 85)
baseline = results[0]
for r in results:
    delta = r['sharpe'] - baseline['sharpe']
    marker = ' ✓' if delta >= -0.005 else ' ✗'
    print(f'{r["name"]:<20} {r["annual"]:>7.2f}% {r["sharpe"]:>6.3f} {delta:>+6.3f} {r["drawdown"]:>7.2f}% {r["total_ret"]:>7.1f}% {r["trades"]:>5} {r["vol"]:>7.2f}% {r["time"]:>5.1f}s{marker}')

print('-' * 85)
print(f'基线年化: {baseline["annual"]:.2f}%  基线夏普: {baseline["sharpe"]:.3f}')
print()
print('结论:')
for r in results[1:]:
    delta = r['sharpe'] - baseline['sharpe']
    direction = '↑' if delta > 0.003 else ('↓' if delta < -0.003 else '→')
    pct = abs(delta) / baseline['sharpe'] * 100
    print(f'  {r["name"]}: 夏普 {direction} {abs(delta):.3f} ({pct:.1f}%)', end='')
    if delta > 0.003:
        print(' ★ 可考虑删除')
    elif delta < -0.003:
        print(' ✗ 不应删除')
    else:
        print(' → 影响不大')
