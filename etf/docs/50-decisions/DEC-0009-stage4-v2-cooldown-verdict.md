# DEC-0009 Stage4 V2 cooldown 结论与主方案确认

状态：Accepted
日期：2026-04-16

## 背景

在 Stage3 已确认主方案 F6 + style_off + top_n = 3 后，已按 V2 主线完成 cooldown = 10 / 15 / 20 的对比回测。需要确认后续阶段应采用的正式冷却期参数。

## 决策

1. Stage5 及后续主线统一使用 cooldown = 20
2. 主方案更新为 F6 + style_off + top_n = 3 + cooldown = 20
3. cooldown = 15 作为观察方案保留，不进入主线但可用于复核样本外平滑性
4. cooldown = 10 退出后续主线

## 原因

1. cooldown = 20 在全样本与测试期均为最佳，说明较长冷却期更能抑制无效调仓并保留主信号。
2. cooldown = 10 虽提高换手，但没有换来更强收益或更高夏普，属于“忙但不优”。
3. cooldown = 15 虽在 Walk-Forward 上略优，但不足以抵消其在长期收益和测试期表现上的劣势。
4. 为保持 V2 主线收敛，应优先选择“整体最强且换手更克制”的方案，因此采用 cooldown = 20。

## 证据

- `../20-research-and-backtest/results/stage4-cooldown-comparison-summary-v2.md`
- `../../windows_backtest_package/results/stage4_cooldown10_style_off_latest.json`
- `../../windows_backtest_package/results/stage4_cooldown15_style_off_latest.json`
- `../../windows_backtest_package/results/stage4_cooldown20_style_off_latest.json`

## 后续动作

1. 以 F6 + style_off + top_n = 3 + cooldown = 20 进入 Stage5
2. 执行 trigger_deviation = 0.15 / 0.20 / 0.25 的对比回测
3. Stage5 跑完后再决定是否锁定触发偏离参数
