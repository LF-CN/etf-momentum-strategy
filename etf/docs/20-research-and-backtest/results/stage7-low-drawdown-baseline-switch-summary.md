# Stage7 低回撤正式基线切换摘要

## 新正式基线
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

## 与旧正式基线的唯一区别
- 旧正式基线：max_single_weight = 0.35
- 新正式基线：max_single_weight = 0.325

## 切换依据
### Stage7A
- 0.30：全样本年化 14.88%，夏普 1.04，回撤 -13.90%；测试期 26.00%，WF 年化 13.04%
- 0.325：全样本年化 15.10%，夏普 1.05，回撤 -14.07%；测试期 26.42%，WF 年化 13.02%
- 0.35：全样本年化 14.47%，夏普 0.99，回撤 -15.42%；测试期 26.67%，WF 年化 13.95%

阶段结论：0.325 是低回撤支线中最平衡的候选值。

### Stage7B
固定 0.325 后比较 cooldown 15 / 20 / 25：
- 15：全样本回撤略浅，但调仓明显增加且 WF 明显变差
- 20：全样本、测试期、WF 综合最优
- 25：过度保守，收益与回撤都恶化

阶段结论：cooldown = 20 保持不变。

### Stage7C
固定 0.325 + 20 后比较 stop_loss -0.15 / -0.18 / -0.20：
- -0.18 与 -0.20 结果等效
- -0.15 略弱且未改善回撤

阶段结论：stop_loss_threshold = -0.18 保持不变。

## 最终结论
用户已明确采用方案 B：以更低回撤为优先目标，将 max_single_weight=0.325 切换为新的正式基线。

## 工程同步与验证结果
切换正式基线后，已完成以下实测验证：
1. `python3 /opt/data/scripts/etf/daily_task.py`：执行成功，兼容入口已落到正式链路
2. `ETFService().calculate_signals()`：执行成功
3. `python3 /opt/data/scripts/etf/generate_daily_signal_message.py`：执行成功，提醒文案已更新
4. `signal.json` / `ETFService().calculate_signals()` / `daily_task_full.run_daily_task()`：关键字段逐项比对 `all_equal = true`

本轮 Stage7 正式基线下的实测信号为：
- 日期：2026-04-16
- 是否调仓：否
- 原因类型：`no_trigger`
- 原因：偏离度 `9.78%` 小于阈值，无强信号
- 目标权重：
  - 510500：27.6%
  - 159941：34.3%
  - 511010：38.1%
  - 518880：0.0%
  - 159928：0.0%
- 策略参数已确认：`max_single_weight = 0.325`

此外，新的正式基线 preset 已实际跑通：
- preset：`stage7_final_low_drawdown_baseline_v3.json`
- Full sample：年化 `15.10%`，夏普 `1.05`，最大回撤 `-14.07%`，调仓 `114` 次
- Test：年化 `26.42%`，夏普 `1.93`，最大回撤 `-10.83%`
- Walk-forward：平均年化 `13.02%`，平均夏普 `0.94`，平均最大回撤 `-7.39%`
- 参数稳定性：`best_params_frequency = 6/6`
