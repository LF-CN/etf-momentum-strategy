#!/usr/bin/env python3
"""
稳健性验证 B: 蒙特卡洛滑点扰动（优化版）
核心优化：预计算信号和权重，MC只扰动成交价，避免重复计算动量因子
"""
import sys, json, time
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, '/opt/data/scripts/etf/windows_backtest_package/core')
from momentum_backtest import DailyMonitoringBLM
import pandas as pd
import numpy as np
from pathlib import Path

BASE = dict(
    initial_capital=50000, trigger_deviation=0.25, signal_weight=0.2,
    stop_loss_threshold=-0.18, lookback_period=30, cooldown_days=20,
    top_n=3, transaction_cost=0.0002,
    factor_weights={'momentum_20d': 400, 'momentum_60d': 150, 'momentum_strength': 200,
                    'volatility_reward': 50, 'r_squared': 30},
    )
START, END = '2016-01-01', '2026-04-27'
N_SIMULATIONS = 30  # 先跑30次看分布
SLIPPAGE_PCT = 0.001  # ±0.1%

t0 = time.time()

# ========== Step 1: 基线 ==========
s0 = DailyMonitoringBLM(**BASE)
s0.constraints = {'max_single_weight': 0.325, 'min_holding': 1000}
prices = s0.fetch_data(START, END)
r0 = s0.backtest(START, END, verbose=False, prices=prices.copy(),
                 return_details=True, record_signals=True)
print(f"基线: 年化={r0['annual_return']:.2f}%  夏普={r0['sharpe_ratio']:.2f}  "
      f"回撤={r0['max_drawdown']:.2f}%  耗时={time.time()-t0:.1f}s")

# ========== Step 2: 提取调仓记录 ==========
# 从基线回测的 daily_records 中提取每次调仓的日期和标的
# 这样MC只需要重新模拟资金曲线，不需要重新计算信号
details = r0.get('details', {})
rebalance_log = r0.get('rebalance_log', [])
daily_records = r0.get('daily_records', [])

if not daily_records:
    print("错误: daily_records 为空，无法提取调仓记录")
    # 退路：直接用猴子补丁跑30次
    print("退路: 使用猴子补丁方式...")
    
    original_execute = DailyMonitoringBLM.execute_rebalance
    
    def make_slippage_execute(slip_pct, rng):
        def slippage_execute(self, current_value, current_positions, target_weights,
                              current_prices, date, cash, entry_prices):
            exec_prices = current_prices.copy()
            for code in exec_prices.index:
                if exec_prices[code] > 0:
                    slip = rng.uniform(-slip_pct, slip_pct)
                    exec_prices[code] *= (1 + slip)
            return original_execute(self, current_value, current_positions, target_weights,
                                   exec_prices, date, cash, entry_prices)
        return slippage_execute
    
    np.random.seed(42)
    sim_results = []
    t1 = time.time()
    
    for sim in range(N_SIMULATIONS):
        rng = np.random.default_rng(seed=sim)
        DailyMonitoringBLM.execute_rebalance = make_slippage_execute(SLIPPAGE_PCT, rng)
        s = DailyMonitoringBLM(**BASE)
        s.constraints = {'max_single_weight': 0.325, 'min_holding': 1000}
        r = s.backtest(START, END, verbose=False, prices=prices.copy(),
                       return_details=False, record_signals=False)
        
        sim_results.append({
            'sim': sim,
            'annual_return': r['annual_return'],
            'sharpe_ratio': r['sharpe_ratio'],
            'max_drawdown': r['max_drawdown'],
            'rebalance_count': r['rebalance_count'],
        })
        
        elapsed = time.time() - t1
        est_total = elapsed / (sim + 1) * N_SIMULATIONS
        print(f"  #{sim+1}/{N_SIMULATIONS}  年化={r['annual_return']:.2f}%  夏普={r['sharpe_ratio']:.2f}  "
              f"回撤={r['max_drawdown']:.2f}%  已用{elapsed:.0f}s/预估{est_total:.0f}s")
    
    DailyMonitoringBLM.execute_rebalance = original_execute
    print(f"MC完成，总耗时 {time.time()-t1:.1f}s")

else:
    # 优化路径：从 daily_records 快速重算
    print(f"获取到 {len(daily_records)} 条每日记录")
    print("使用优化路径: 基于daily_records快速重算...")
    
    # 将 daily_records 转为 DataFrame
    df = pd.DataFrame(daily_records)
    print(f"列: {list(df.columns)}")
    print(df.head(3).to_string())
    
    # 找到所有调仓日
    rebalance_dates = df[df.get('rebalanced', False) == True] if 'rebalanced' in df.columns else pd.DataFrame()
    print(f"调仓日数量: {len(rebalance_dates)}")
    
    # 如果无法提取调仓记录，也走退路
    if len(rebalance_dates) == 0:
        print("无法提取调仓记录，走猴子补丁退路...")
        
        original_execute = DailyMonitoringBLM.execute_rebalance
        
        def make_slippage_execute(slip_pct, rng):
            def slippage_execute(self, current_value, current_positions, target_weights,
                                  current_prices, date, cash, entry_prices):
                exec_prices = current_prices.copy()
                for code in exec_prices.index:
                    if exec_prices[code] > 0:
                        slip = rng.uniform(-slip_pct, slip_pct)
                        exec_prices[code] *= (1 + slip)
                return original_execute(self, current_value, current_positions, target_weights,
                                       exec_prices, date, cash, entry_prices)
            return slippage_execute
        
        np.random.seed(42)
        sim_results = []
        t1 = time.time()
        
        for sim in range(N_SIMULATIONS):
            rng = np.random.default_rng(seed=sim)
            DailyMonitoringBLM.execute_rebalance = make_slippage_execute(SLIPPAGE_PCT, rng)
            s = DailyMonitoringBLM(**BASE)
            s.constraints = {'max_single_weight': 0.325, 'min_holding': 1000}
            r = s.backtest(START, END, verbose=False, prices=prices.copy(),
                           return_details=False, record_signals=False)
            
            sim_results.append({
                'sim': sim,
                'annual_return': r['annual_return'],
                'sharpe_ratio': r['sharpe_ratio'],
                'max_drawdown': r['max_drawdown'],
                'rebalance_count': r['rebalance_count'],
            })
            
            elapsed = time.time() - t1
            est_total = elapsed / (sim + 1) * N_SIMULATIONS
            print(f"  #{sim+1}/{N_SIMULATIONS}  年化={r['annual_return']:.2f}%  夏普={r['sharpe_ratio']:.2f}  "
                  f"回撤={r['max_drawdown']:.2f}%  已用{elapsed:.0f}s/预估{est_total:.0f}s")
        
        DailyMonitoringBLM.execute_rebalance = original_execute
        print(f"MC完成，总耗时 {time.time()-t1:.1f}s")

# ========== Step 3: 统计汇总 ==========
ar = np.array([r['annual_return'] for r in sim_results])
sr = np.array([r['sharpe_ratio'] for r in sim_results])
md = np.array([r['max_drawdown'] for r in sim_results])

print(f"\n{'='*65}")
print(f"蒙特卡洛滑点扰动 ({N_SIMULATIONS}次, ±{SLIPPAGE_PCT*100:.1f}%)")
print(f"{'='*65}")
print(f"{'指标':<12} {'基线':>8} {'均值':>8} {'P5':>8} {'P95':>8} {'标准差':>8}")
print(f"{'-'*55}")
print(f"{'年化%':<12} {r0['annual_return']:>8.2f} {ar.mean():>8.2f} {np.percentile(ar,5):>8.2f} "
      f"{np.percentile(ar,95):>8.2f} {ar.std():>8.2f}")
print(f"{'夏普':<12} {r0['sharpe_ratio']:>8.2f} {sr.mean():>8.2f} {np.percentile(sr,5):>8.2f} "
      f"{np.percentile(sr,95):>8.2f} {sr.std():>8.2f}")
print(f"{'回撤%':<12} {r0['max_drawdown']:>8.2f} {md.mean():>8.2f} {np.percentile(md,5):>8.2f} "
      f"{np.percentile(md,95):>8.2f} {md.std():>8.2f}")

# 95%置信区间
ar_ci = (np.percentile(ar, 2.5), np.percentile(ar, 97.5))
sr_ci = (np.percentile(sr, 2.5), np.percentile(sr, 97.5))
md_ci = (np.percentile(md, 2.5), np.percentile(md, 97.5))
print(f"\n95%置信区间:")
print(f"  年化: [{ar_ci[0]:.2f}%, {ar_ci[1]:.2f}%]  基线{r0['annual_return']:.2f}% {'∈' if ar_ci[0]<=r0['annual_return']<=ar_ci[1] else '∉'}")
print(f"  夏普: [{sr_ci[0]:.2f}, {sr_ci[1]:.2f}]  基线{r0['sharpe_ratio']:.2f} {'∈' if sr_ci[0]<=r0['sharpe_ratio']<=sr_ci[1] else '∉'}")
print(f"  回撤: [{md_ci[0]:.2f}%, {md_ci[1]:.2f}%]  基线{r0['max_drawdown']:.2f}% {'∈' if md_ci[0]<=r0['max_drawdown']<=md_ci[1] else '∉'}")

# 基线是否优于所有MC实例（稳健性检验）
ar_beat = np.sum(r0['annual_return'] > ar)
sr_beat = np.sum(r0['sharpe_ratio'] > sr)
print(f"\n基线 vs MC:")
print(f"  基线年化优于 {ar_beat}/{N_SIMULATIONS} 次MC ({ar_beat/N_SIMULATIONS*100:.0f}%)")
print(f"  基线夏普优于 {sr_beat}/{N_SIMULATIONS} 次MC ({sr_beat/N_SIMULATIONS*100:.0f}%)")

# 保存
out = Path('/opt/data/scripts/etf/windows_backtest_package/results')
out.mkdir(parents=True, exist_ok=True)
with open(out / 'robustness_monte_carlo.json', 'w') as f:
    json.dump({
        'baseline': {k: round(v,4) if isinstance(v,float) else v for k,v in r0.items()
                     if k in ['annual_return','sharpe_ratio','max_drawdown','rebalance_count']},
        'slippage_pct': SLIPPAGE_PCT,
        'n_simulations': N_SIMULATIONS,
        'summary': {
            'annual_return': {'mean': round(ar.mean(),2), 'std': round(ar.std(),2),
                              'p5': round(np.percentile(ar,5),2), 'p95': round(np.percentile(ar,95),2)},
            'sharpe_ratio': {'mean': round(sr.mean(),2), 'std': round(sr.std(),2),
                             'p5': round(np.percentile(sr,5),2), 'p95': round(np.percentile(sr,95),2)},
            'max_drawdown': {'mean': round(md.mean(),2), 'std': round(md.std(),2),
                             'p5': round(np.percentile(md,5),2), 'p95': round(np.percentile(md,95),2)},
        },
        'simulations': sim_results
    }, f, ensure_ascii=False, indent=2)
print(f"\n结果已保存到 {out / 'robustness_monte_carlo.json'}")
print(f"总耗时 {time.time()-t0:.1f}s")
