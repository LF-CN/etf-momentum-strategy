# DEC-0006 Stage1 V2 因子模板晋级结论

状态：Accepted
日期：2026-04-16

## 背景

在修复后的回测引擎上，已按 V2 主线重新完成 Stage1 六套因子模板比较。需要确认哪些模板进入 Stage2，避免继续在明显弱势模板上消耗实验资源。

## 决策

- 主晋级方案：F6（五因子全开）
- 稳健对照方案：F4（20日 + 60日 + 波动率奖励）
- 观察保留方案：F5（20日 + 60日 + R² 趋势稳定性）

淘汰方案：F1、F2、F3

## 原因

1. F6 全样本综合表现最优：年化 13.83%，夏普 0.92，最大回撤 -14.23%。
2. F4 在不引入全部复杂因子的情况下提供了稳定的正向改进，适合作为稳健对照。
3. F5 虽然全样本不如 F6，但 Walk-Forward 平均年化与平均夏普均为六套模板最高，具备继续观察价值。
4. F3 证明动量强度单独加入有负面效果，不适合保留。
5. F1/F2 更适合作为基础参照，不再进入下一阶段。

## 证据

- `../20-research-and-backtest/results/stage1-factor-comparison-summary-v2.md`
- `../../windows_backtest_package/results/stage1_f1_momentum20_only_latest.json`
- `../../windows_backtest_package/results/stage1_f2_momentum20_60_latest.json`
- `../../windows_backtest_package/results/stage1_f3_add_strength_latest.json`
- `../../windows_backtest_package/results/stage1_f4_add_volatility_reward_latest.json`
- `../../windows_backtest_package/results/stage1_f5_add_r_squared_latest.json`
- `../../windows_backtest_package/results/stage1_f6_full_factor_latest.json`

## 影响范围

- Stage2 style on/off 预设执行顺序
- 后续实验资源投入
- 主方案与对照方案设定

## 后续动作

1. 对 F4 / F5 / F6 执行 Stage2 style on/off 重跑
2. 形成新的 Stage2 V2 摘要文档
3. 再基于 Stage2 结果确定 Stage3 的唯一主方案
