# Stage6 最终基线确认报告（V2 重跑）

状态：Accepted
更新日期：2026-04-16
说明：本报告用于确认 V2 主线从 Stage1 至 Stage5 收敛出的最终参数，是否能在 full sample、train/test 与 walk-forward 三层验证中同时成立。

## 1. 最终确认参数

- 因子模板：F6（五因子全开）
- style：off（全部 = 1.0）
- top_n：3
- cooldown_days：20
- trigger_deviation：0.25
- signal_weight：0.20
- stop_loss_threshold：-0.18
- lookback_period：30
- max_single_weight：0.35
- min_holding：1000
- transaction_cost：0.0002

## 2. Full Sample 结果

| 指标 | 数值 |
|------|------|
| 年化收益 | 14.47% |
| 夏普 | 0.99 |
| 最大回撤 | -15.42% |
| 调仓次数 | 112 |

## 3. Train/Test 测试期结果

| 指标 | 数值 |
|------|------|
| 测试期年化 | 26.67% |
| 测试期夏普 | 2.02 |
| 测试期最大回撤 | -8.45% |

## 4. Walk-Forward 汇总（6窗口）

| 指标 | 数值 |
|------|------|
| 窗口数 | 6 |
| WF平均年化 | 13.95% |
| WF平均夏普 | 1.01 |
| WF平均回撤 | -8.04% |

## 5. 参数稳定性验证

Walk-Forward 的 `best_params_frequency` 显示，当前这套参数在 6 / 6 个滚动窗口中都被选中。

这意味着：
1. 该参数组合不是只在单一历史区间偶然占优
2. 它在滚动样本外环境中具有重复稳定性
3. V2 主线不是“分阶段拼接出的脆弱最优解”，而是经过最终复核后仍成立的正式基线

## 6. 最终结论

- Stage6 最终基线确认：**通过**
- V2 正式基线参数定稿为：
  - **F6 + style_off + top_n = 3 + cooldown = 20 + trigger_deviation = 0.25**
- 对应约束：
  - `max_single_weight = 0.35`
  - `min_holding = 1000`

## 7. 工程判断

1. 这套参数在 full sample、test、walk-forward 三层验证中同时成立。
2. 测试期表现显著强于全样本，说明该主线并未在近阶段失效。
3. Walk-Forward 平均夏普达到 1.01，且参数频率为 6/6，说明结构稳定性较强。
4. 因此，这套参数可以作为 V2 重跑后的正式默认基线，供后续监控、信号输出与实盘观察使用。

## 8. 一句话结论

V2 主线从 Stage1 到 Stage6 已完成完整闭环验证，最终确认：**F6 + style_off + top_n = 3 + cooldown = 20 + trigger_deviation = 0.25** 是当前 ETF 动量轮动策略的正式基线方案。
