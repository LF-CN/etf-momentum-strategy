# DEC-0008 Stage3 V2 top_n 结论与主方案确认

状态：Accepted
日期：2026-04-16

## 背景

在 Stage2 已确认主方案 F6 + style_off 后，已按 V2 主线完成 top_n = 2 / 3 / 4 的对比回测。需要确认后续阶段应采用的正式持仓数量。

## 决策

1. Stage4 及后续主线统一使用 top_n = 3
2. 主方案更新为 F6 + style_off + top_n = 3
3. top_n = 4 作为观察方案保留，不进入主线但可用于复核滚动样本外稳定性
4. top_n = 2 退出后续主线

## 原因

1. top_n = 3 在全样本与测试期均为最佳，说明三持仓结构最能兼顾信号集中与基本分散。
2. top_n = 2 没有体现出高集中策略应有的收益增强，反而显著压低全样本与 Walk-Forward 夏普。
3. top_n = 4 虽在 Walk-Forward 上略优，但全样本收益和夏普显著退化，说明分散度过高会稀释主信号。
4. 为保持 V2 主线收敛，应优先选择“长期表现更强且样本外不过度失真”的方案，因此采用 top_n = 3 而不是继续并行保留多条持仓数量分支。

## 证据

- `../20-research-and-backtest/results/stage3-topn-comparison-summary-v2.md`
- `../../windows_backtest_package/results/stage3_f6_top2_style_off_latest.json`
- `../../windows_backtest_package/results/stage3_f6_top3_style_off_latest.json`
- `../../windows_backtest_package/results/stage3_f6_top4_style_off_latest.json`

## 后续动作

1. 以 F6 + style_off + top_n = 3 进入 Stage4
2. 执行 cooldown = 10 / 15 / 20 的对比回测
3. Stage4 跑完后再决定是否锁定冷却期参数
