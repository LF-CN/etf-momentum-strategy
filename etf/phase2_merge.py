#!/usr/bin/env python3
"""
Phase 2: 动量合并测试
在 _precompute_momentum_scores 层面合并 20日+60日动量。
"""
import sys, os, time
import numpy as np
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

class MergedEngine(DailyMonitoringBLM):
    """覆盖 _precompute_momentum_scores，将 20日+60日合并为单一因子"""
    def __init__(self, merge_ratio=0.6, merge_weight=500, **kw):
        super().__init__(**kw)
        self.merge_ratio = merge_ratio  # 短期权重占比
        self.merge_weight = merge_weight  # 合并后的因子权重

    def _precompute_momentum_scores(self, prices):
        codes = list(prices.columns)
        p_arrays = {c: prices[c].values for c in codes}
        n_dates = len(prices)
        lookback = self.lookback_period
        fw = self.factor_weights
        result = {c: np.full(n_dates, 50.0) for c in codes}

        for code in codes:
            p = p_arrays[code]
            for i in range(lookback, n_dates):
                start = i - lookback
                w = p[start:i+1]
                rets = w[1:] / w[:-1] - 1.0
                if len(rets) < 6:
                    result[code][i] = 50.0
                    continue

                # 短期动量（20日）
                if len(w) >= 20:
                    mom_20d = w[-1] / w[-20] - 1.0
                else:
                    mom_20d = w[-1] / w[0] - 1.0

                # 长期动量（60日）
                if len(w) >= 60:
                    mom_60d = w[-1] / w[-60] - 1.0
                else:
                    mom_60d = w[-1] / w[0] - 1.0

                # ★ 合并为加权动量
                merged_mom = (self.merge_ratio * mom_20d +
                              (1 - self.merge_ratio) * mom_60d)

                # 动量强度
                if len(rets) > 10:
                    hist_mean = rets.mean()
                    recent_mom = mom_20d / 20.0
                    momentum_strength = (recent_mom - hist_mean) if hist_mean != 0 else 0.0
                else:
                    momentum_strength = 0.0

                # 波动率
                volatility = float(rets.std(ddof=1))
                if volatility > 0:
                    vol_score = np.clip((0.03 - volatility) / 0.03, 0.0, 1.0)
                else:
                    vol_score = 0.5

                # R² 趋势稳定性
                if len(w) > 10:
                    x = np.arange(len(w), dtype=np.float64)
                    y = w.astype(np.float64)
                    slope, intercept = np.polyfit(x, y, 1)
                    y_pred = slope * x + intercept
                    ss_res = np.sum((y - y_pred) ** 2)
                    ss_tot = np.sum((y - y.mean()) ** 2)
                    r_squared = float(1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0)
                else:
                    r_squared = 0.0

                # ★ 用合并动量替换 20日动量，60日权重已设为0
                base_score = (
                    merged_mom * fw.get('momentum_20d', 0) +
                    # momentum_60d 权重=0，跳过
                    momentum_strength * fw.get('momentum_strength', 0) +
                    vol_score * fw.get('volatility_reward', 0) +
                    r_squared * fw.get('r_squared', 0)
                )
                result[code][i] = float(np.clip(base_score, 0.0, 100.0))

        return result

# ── 测试配置 ──
MERGE_TESTS = [
    ('0_基线(5因子)',       None),
    ('合并50:50_w=500',     (0.50, 500)),
    ('合并60:40_w=500',     (0.60, 500)),
    ('合并70:30_w=500',     (0.70, 500)),
    ('合并60:40_w=420',     (0.60, 420)),
    ('合并70:30_w=420',     (0.70, 420)),
]

print('=' * 75)
print('Phase 2: 动量合并测试')
print('=' * 75)

print('\n[1/2] 加载数据...')
loader = DailyMonitoringBLM(**SHARED_KWARGS, factor_weights=BASELINE_FW)
prices = loader.fetch_data(START, END)
print(f'      维度: {prices.shape}')

print(f'\n[2/2] 运行 {len(MERGE_TESTS)} 组回测...\n')
results = []

for name, merge_params in MERGE_TESTS:
    if merge_params is None:
        bt = DailyMonitoringBLM(**SHARED_KWARGS, factor_weights=BASELINE_FW)
        bt.constraints = {'max_single_weight': 0.325, 'min_holding': 1000}
    else:
        ratio, mw = merge_params
        fw = {**BASELINE_FW, 'momentum_20d': mw, 'momentum_60d': 0}
        bt = MergedEngine(merge_ratio=ratio, merge_weight=mw,
                          **SHARED_KWARGS, factor_weights=fw)
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

print(f'{"配置":<22} {"年化%":>8} {"夏普":>7} {"Δ夏普":>7} {"回撤%":>8} {"总收益%":>8} {"调仓":>5} {"波动%":>8} {"耗时":>6}')
print('-' * 87)
baseline = results[0]
for r in results:
    delta = r['sharpe'] - baseline['sharpe']
    marker = ' ✓' if delta >= -0.005 else ' ✗'
    print(f'{r["name"]:<22} {r["annual"]:>7.2f}% {r["sharpe"]:>6.3f} {delta:>+6.3f} {r["drawdown"]:>7.2f}% {r["total_ret"]:>7.1f}% {r["trades"]:>5} {r["vol"]:>7.2f}% {r["time"]:>5.1f}s{marker}')

print('-' * 87)
best = max(results[1:], key=lambda x: x['sharpe'])
print(f'最佳合并: {best["name"]}  夏普={best["sharpe"]:.3f}  年化={best["annual"]:.2f}%')
print(f'基线夏普: {baseline["sharpe"]:.3f}')
