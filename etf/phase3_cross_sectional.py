#!/usr/bin/env python3
"""
Phase 3: 截面动量测试
加入新因子：ETF自身动量 - 池子平均动量（相对强弱）。
测试不同权重和周期。
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

class CrossSectionalEngine(DailyMonitoringBLM):
    """加入截面动量因子"""
    def __init__(self, cs_period=20, cs_weight=150, **kw):
        super().__init__(**kw)
        self.cs_period = cs_period  # 截面动量周期
        self.cs_weight = cs_weight

    def _precompute_momentum_scores(self, prices):
        codes = list(prices.columns)
        p_arrays = {c: prices[c].values for c in codes}
        n_dates = len(prices)
        lookback = self.lookback_period
        fw = self.factor_weights
        result = {c: np.full(n_dates, 50.0) for c in codes}

        for i in range(lookback, n_dates):
            # ── 先计算所有 ETF 的原始动量（用于截面） ──
            raw_mom = {}
            for code in codes:
                w = p_arrays[code][i-lookback:i+1]
                if len(w) >= max(20, 60, self.cs_period):
                    raw_mom[code] = {
                        '20d': w[-1] / w[-20] - 1.0 if len(w) >= 20 else w[-1] / w[0] - 1.0,
                        '60d': w[-1] / w[-60] - 1.0 if len(w) >= 60 else w[-1] / w[0] - 1.0,
                    }
                else:
                    raw_mom[code] = {'20d': w[-1] / w[0] - 1.0, '60d': w[-1] / w[0] - 1.0}

            # ── 计算截面动量（用 20日或60日） ──
            if self.cs_period == 20:
                pool_avg = np.mean([v['20d'] for v in raw_mom.values()])
                cs_mom = {c: raw_mom[c]['20d'] - pool_avg for c in codes}
            else:
                pool_avg = np.mean([v['60d'] for v in raw_mom.values()])
                cs_mom = {c: raw_mom[c]['60d'] - pool_avg for c in codes}

            # ── 逐 ETF 计算最终得分 ──
            for code in codes:
                w = p_arrays[code][i-lookback:i+1]
                rets = w[1:] / w[:-1] - 1.0
                if len(rets) < 6:
                    continue

                mom_20d = raw_mom[code]['20d']
                mom_60d = raw_mom[code]['60d']

                # 动量强度
                if len(rets) > 10:
                    hist_mean = rets.mean()
                    momentum_strength = (mom_20d / 20.0 - hist_mean) if hist_mean != 0 else 0.0
                else:
                    momentum_strength = 0.0

                # 波动率
                volatility = float(rets.std(ddof=1))
                vol_score = np.clip((0.03 - volatility) / 0.03, 0.0, 1.0) if volatility > 0 else 0.5

                # R²
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

                base_score = (
                    mom_20d * fw.get('momentum_20d', 0) +
                    mom_60d * fw.get('momentum_60d', 0) +
                    momentum_strength * fw.get('momentum_strength', 0) +
                    vol_score * fw.get('volatility_reward', 0) +
                    r_squared * fw.get('r_squared', 0) +
                    cs_mom[code] * self.cs_weight  # ★ 截面动量
                )
                result[code][i] = float(np.clip(base_score, 0.0, 100.0))

        return result


# ── 测试配置 ──
CS_TESTS = [
    ('0_基线', None),
    ('截面20日_w=100', (20, 100)),
    ('截面20日_w=150', (20, 150)),
    ('截面20日_w=200', (20, 200)),
    ('截面60日_w=100', (60, 100)),
    ('截面60日_w=150', (60, 150)),
]

print('=' * 75)
print('Phase 3: 截面动量测试')
print('=' * 75)

print('\n[1/2] 加载数据...')
loader = DailyMonitoringBLM(**SHARED_KWARGS, factor_weights=BASELINE_FW)
prices = loader.fetch_data(START, END)
print(f'      维度: {prices.shape}')

print(f'\n[2/2] 运行 {len(CS_TESTS)} 组回测...\n')
results = []

for name, cs_params in CS_TESTS:
    if cs_params is None:
        bt = DailyMonitoringBLM(**SHARED_KWARGS, factor_weights=BASELINE_FW)
    else:
        period, weight = cs_params
        bt = CrossSectionalEngine(cs_period=period, cs_weight=weight,
                                  **SHARED_KWARGS, factor_weights=BASELINE_FW)
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
    marker = ' ★' if delta > 0.003 else (' ✓' if delta >= -0.005 else ' ✗')
    print(f'{r["name"]:<22} {r["annual"]:>7.2f}% {r["sharpe"]:>6.3f} {delta:>+6.3f} {r["drawdown"]:>7.2f}% {r["total_ret"]:>7.1f}% {r["trades"]:>5} {r["vol"]:>7.2f}% {r["time"]:>5.1f}s{marker}')

print('-' * 87)
best = max(results[1:], key=lambda x: x['sharpe'])
print(f'最佳截面动量: {best["name"]}  夏普={best["sharpe"]:.3f}  年化={best["annual"]:.2f}%')
print(f'基线夏普: {baseline["sharpe"]:.3f}')
