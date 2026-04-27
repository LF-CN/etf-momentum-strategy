# DEC-0007 Stage2 V2 style on/off 结论与主方案确认

状态：Accepted
日期：2026-04-16

## 背景

在 Stage1 晋级的 F4 / F5 / F6 三套因子模板上，已按 V2 主线重新完成 style on / style off 比较。需要确认后续阶段是否继续保留 style_factor。

## 决策

1. 后续主线统一使用 style_off（全部 = 1.0）
2. Stage3 主方案确认为 F6 + style_off
3. F4 + style_off 作为稳健对照方案保留
4. F5 + style_off 作为观察方案保留，不进入主线但可用于复核

## 原因

1. F4 上 style_on 明显降低收益与夏普，说明风格乘数对波动率奖励模板有直接负面作用。
2. F5 上 style_on/off 差异很小，保留 style_factor 没有明确必要。
3. F6 上 style_on 显著恶化收益、夏普与回撤，说明在主方案上 style_factor 是明确拖累项。
4. 统一 style_off 后，策略结构更简洁，可解释性更强，且避免错误压制 defensive / gov_bond 等资产。

## 证据

- `../20-research-and-backtest/results/stage2-style-on-off-summary-v2.md`
- `../../windows_backtest_package/results/stage2_f4_style_on_latest.json`
- `../../windows_backtest_package/results/stage2_f4_style_off_latest.json`
- `../../windows_backtest_package/results/stage2_f5_style_on_latest.json`
- `../../windows_backtest_package/results/stage2_f5_style_off_latest.json`
- `../../windows_backtest_package/results/stage2_f6_style_on_latest.json`
- `../../windows_backtest_package/results/stage2_f6_style_off_latest.json`

## 后续动作

1. 以 F6 + style_off 进入 Stage3
2. 执行 top_n = 2 / 3 / 4 的对比回测
3. Stage3 跑完后再决定是否只保留单一主方案
