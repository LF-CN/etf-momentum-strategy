# Stage7 策略基线参数

## 当前基线（2026-04-27 P1-P5 全阶段验证通过）

| 参数 | 值 |
|------|-----|
| initial_capital | 52000 |
| trigger_deviation | **0.24** |
| signal_weight | 0.2 |
| stop_loss_threshold | -0.18 |
| lookback_period | 30 |
| cooldown_days | 20 |
| top_n | 3 |
| transaction_cost | 0.0002 |
| max_single_weight | 0.325 |
| min_holding | 1000 |

### factor_weights
| 因子 | 权重 |
|------|------|
| momentum_20d | **425** |
| momentum_60d | **175** |
| momentum_strength | 200 |
| volatility_reward | **75** |
| r_squared | 30 |

### style_factors
全1.0（small_cap/growth/mid_cap/large_cap/tech/cyclical/defensive/gov_bond/convertible/commodity/a_share/us_tech）

### 性能指标
| 指标 | 值 |
|------|-----|
| 年化收益 | 16.45% |
| 夏普比率 | 1.197 |
| 最大回撤 | -12.79% |
| 调仓次数 | 108 |

### P4 Walk-Forward 验证（8窗口样本外）
| 指标 | 值 |
|------|-----|
| 均年化 | 16.98% |
| 最差年化 | -4.12% (2022) |
| 均夏普 | 1.10 |
| 正/负年 | 6/2 |

### P5 压力测试
| 测试 | 年化 | 夏普 | 回撤 |
|------|------|------|------|
| T+1延迟(3x cost) | 16.06% | 1.164 | -12.93% |
| 前半(16-20) | 17.91% | 1.274 | -12.79% |
| 后半(21-26) | 14.49% | 1.036 | -10.93% |
| trigger微扰(±0.02)年化波动 | 1.70% | | |

---

## 旧基线（存档参考）

| 参数 | 值 |
|------|-----|
| trigger_deviation | 0.25 |
| factor_weights | m20d=400, m60d=150, mstr=200, vol=50, rsq=30 |

### 旧基线性能
- 年化 15.27%，夏普 1.064，回撤 -14.07%，调仓 114 次
- 历年最大亏损 -7.07% (2022)

---

## 敏感度教训（P1-P5 关键发现）

1. **r_squared 极敏感**：30→55 回撤 -36%；rsq=15 虽回撤小但后半段失效（夏普降至0.847）
2. **trigger=0.24 是新最优点**：比 0.25 多捕获一次调仓机会，且不增加回撤
3. **volatility_reward 75 > 50**：更好地区分波动率奖励，改善回撤 1.28%
4. **momentum_20d 425 > 400**：对短期动量更敏感，提升年化
5. **momentum_60d 175 > 150**：与 m20d 协同优化，但不宜过高
6. **trigger 放宽到 0.26 以上会显著变差**（D-trg0.24 trg=0.26 降至 13.82%/0.942）
