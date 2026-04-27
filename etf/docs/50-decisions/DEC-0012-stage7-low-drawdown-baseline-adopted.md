# DEC-0012 Stage7 低回撤正式基线采用决策

## 决策结论
自本决策起，ETF 动量轮动策略正式基线由 Stage6 版本切换为 Stage7 低回撤版本。

新正式基线：
- F6
- style_off
- top_n = 3
- cooldown_days = 20
- trigger_deviation = 0.25
- stop_loss_threshold = -0.18
- signal_weight = 0.20
- transaction_cost = 0.0002
- max_single_weight = 0.325
- min_holding = 1000

## 决策来源
用户明确选择方案 B：将低回撤候选方案作为正式基线，并同步修改实盘提醒程序。

## 采用理由
1. Stage7A 证明 max_single_weight 从 0.35 下调到 0.325 后，全样本回撤从 -15.42% 改善到 -14.07%。
2. Stage7B 证明在 0.325 候选下，cooldown_days 仍以 20 最优，无需改动。
3. Stage7C 证明 stop_loss_threshold 保持 -0.18 即可，收紧到 -0.15 无改善，放宽到 -0.20 与 -0.18 等效。
4. 用户当前优先目标是降低回撤，因此采用方案 B，以 0.325 作为正式基线。

## 影响范围
已同步到以下正式链路并完成验证：
- /opt/data/scripts/etf/config.py
- /opt/data/scripts/etf/daily_task_full.py
- /opt/data/scripts/etf/daily_task.py
- /opt/data/scripts/etf/etf_service.py
- /opt/data/scripts/etf/generate_daily_signal_message.py
- /opt/data/scripts/etf/windows_backtest_package/core/run_preset.py
- /opt/data/scripts/etf/windows_backtest_package/presets/stage7_final_low_drawdown_baseline_v3.json

验证结果：
- `daily_task.py` 执行成功
- `generate_daily_signal_message.py` 执行成功
- `ETFService().calculate_signals()` 执行成功
- `signal.json` / `ETFService().calculate_signals()` / `daily_task_full.run_daily_task()` 关键字段比对 `all_equal = true`
- 新 preset `stage7_final_low_drawdown_baseline_v3.json` 已实际跑通，结果与 Stage7A/B/C 收敛结论一致

## 历史口径说明
- Stage6 正式基线（max_single_weight = 0.35）保留为历史阶段结论，不覆盖其原始文档。
- Stage7 低回撤正式基线从本决策起生效，作为新的正式实盘与后续回测口径。
