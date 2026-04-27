# DEC-0011 Stage6 V2 final baseline confirmed

状态：Accepted
日期：2026-04-16

## 背景

Stage1~Stage5 已分别完成因子模板、style、top_n、cooldown 与 trigger_deviation 的逐阶段收敛验证。现需对最终主线参数做一次完整的 full sample + train/test + walk-forward 定稿复核，避免最终结论只是分阶段选择后的拼接结果。

## 决策

1. V2 正式基线参数确认如下：
   - 因子模板：F6
   - style：off
   - top_n：3
   - cooldown_days：20
   - trigger_deviation：0.25
   - signal_weight：0.20
   - stop_loss_threshold：-0.18
   - lookback_period：30
   - max_single_weight：0.35
   - min_holding：1000
   - transaction_cost：0.0002
2. 将该参数组合作为后续默认基线方案
3. 后续如再做优化，应视为“边缘参数优化支线”，不得覆盖本次 V2 正式基线

## 原因

1. 最终基线在 full sample、test、walk-forward 三层验证中同时成立。
2. Walk-Forward 6/6 窗口均选择同一参数组合，说明稳定性高。
3. 该方案不是靠增加换手获得成绩，调仓次数控制在 112 次，具有较好的工程可落地性。
4. 至此，V2 主线已经完成闭环验证，可以结束“重新回测主线”阶段，进入“正式基线使用与后续观察”阶段。

## 证据

- `../20-research-and-backtest/results/stage6-final-baseline-confirmation-v2.md`
- `../../windows_backtest_package/results/stage6_final_baseline_v2_latest.json`
- `DEC-0006-stage1-v2-winners.md`
- `DEC-0007-stage2-v2-style-verdict.md`
- `DEC-0008-stage3-v2-topn-verdict.md`
- `DEC-0009-stage4-v2-cooldown-verdict.md`
- `DEC-0010-stage5-v2-trigger-verdict.md`

## 后续动作

1. 将该基线用于后续信号计算与日常跟踪
2. 若要继续优化，请单开支线（如 max_single_weight 或风险约束优化），不要与 V2 主线混写
3. 需要时可补写一份“V2 主线总总结文档”，用于对外或对后续自己快速回顾
