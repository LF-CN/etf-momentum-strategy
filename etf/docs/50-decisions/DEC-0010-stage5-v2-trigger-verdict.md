# DEC-0010 Stage5 V2 trigger_deviation 结论与主方案确认

状态：Accepted
日期：2026-04-16

## 背景

在 Stage4 已确认主方案 F6 + style_off + top_n = 3 + cooldown = 20 后，已按 V2 主线完成 trigger_deviation = 0.15 / 0.20 / 0.25 的对比回测。需要确认后续最终定稿阶段应采用的正式触发偏离参数。

## 决策

1. Stage6 最终基线确认统一使用 trigger_deviation = 0.25
2. 主方案更新为 F6 + style_off + top_n = 3 + cooldown = 20 + trigger_deviation = 0.25
3. trigger_deviation = 0.20 作为次优对照保留，不进入主线但可用于复核
4. trigger_deviation = 0.15 退出后续主线

## 原因

1. trigger = 0.25 在全样本、测试期与 Walk-Forward 三层验证中均为最佳。
2. trigger = 0.25 的调仓次数最少，说明它不是靠更高换手换来成绩，而是在更严格过滤噪音后保留了更高质量信号。
3. trigger = 0.20 虽稳健，但已被 0.25 全面超越，因此不应继续作为默认主线参数。
4. 为保持 V2 主线收敛并进入最终定稿阶段，应采用“结果最完整、证据最一致”的 0.25。

## 证据

- `../20-research-and-backtest/results/stage5-trigger-comparison-summary-v2.md`
- `../../windows_backtest_package/results/stage5_trigger015_style_off_latest.json`
- `../../windows_backtest_package/results/stage5_trigger020_style_off_latest.json`
- `../../windows_backtest_package/results/stage5_trigger025_style_off_latest.json`

## 后续动作

1. 使用 F6 + style_off + top_n = 3 + cooldown = 20 + trigger_deviation = 0.25 进入 Stage6
2. 执行最终 full sample + train/test + walk-forward 定稿验证
3. 输出最终基线确认文档与参数定稿记录
