# 低回撤专项验证方案（V1）

状态：Draft
更新日期：2026-04-16
目的：在不重开 V2 正式主线的前提下，为“尽量降低回撤、保持策略骨架不变”设计一条稳健验证支线。

## 1. 当前正式基线

当前正式基线：
- 因子模板：F6
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
- initial_capital：52000

当前正式基线表现：
- Full sample：年化 14.47%，夏普 0.99，最大回撤 -15.42%，调仓 112 次
- Test：年化 26.67%，夏普 2.02，最大回撤 -8.45%
- Walk-forward：平均年化 13.95%，平均夏普 1.01，平均最大回撤 -8.04%
- 参数稳定性：best_params_frequency = 6/6

## 2. 本轮专项目标

本轮不是重新寻找“收益更高的主线”，而是验证：
1. 能否把全样本最大回撤从 -15.42% 再往下压
2. 同时不明显破坏测试期表现与 walk-forward 稳健性
3. 不让策略从“主线收敛”重新发散成大范围扫参

## 3. 研究原则

1. 只动边缘风险参数，不重开因子模板 / style / top_n / lookback 主逻辑
2. 先做单变量，再做小范围组合
3. 先验证“集中度约束”，再验证“节奏控制”，最后才考虑止损微调
4. 是否替代正式主线，不只看回撤最低，而看风险收益比是否更稳健

## 4. 验证顺序

### Phase A：max_single_weight 微调（最高优先级）

目标：验证降低组合集中度，是否能最干净地压低回撤。

固定参数：
- F6 + style_off + top_n=3 + cooldown=20 + trigger=0.25
- signal_weight=0.20
- stop_loss_threshold=-0.18
- lookback_period=30

扫描组：
- max_single_weight = 0.30
- max_single_weight = 0.325
- max_single_weight = 0.35（当前基线对照组）

重点观察：
- Full sample 最大回撤能否明显低于 -15.42%
- Test 最大回撤能否继续维持在 -10% 附近或更低
- Walk-forward 平均回撤是否进一步改善
- 年化 / 夏普 / 调仓次数是否仅温和退让

### Phase B：cooldown 微调（第二优先级）

目标：验证更平滑的调仓节奏，是否能进一步压低回撤。

固定参数：
- 使用 Phase A 胜出方案作为新基线；若 Phase A 不替代，则继续用 max_single_weight=0.35
- 其余参数维持正式主线不动

扫描组：
- cooldown_days = 15
- cooldown_days = 20（当前主线对照组）
- cooldown_days = 25

说明：
- 15：已有历史证据显示全样本回撤略低于 20，值得纳入
- 25：验证“更克制是否进一步压回撤”，但不扩到更大范围

重点观察：
- 是否出现“全样本回撤下降 + 调仓次数下降/持平”的组合
- 是否牺牲测试期收益过多
- Walk-forward 是否比 cooldown=20 更平滑

### Phase C：stop_loss_threshold 微调（第三优先级，可选）

只有当前两轮都不能得到足够满意的低回撤版本时，才进入本阶段。

固定参数：
- 使用 Phase B 胜出方案作为输入基线

扫描组：
- stop_loss_threshold = -0.15
- stop_loss_threshold = -0.18（当前对照组）
- stop_loss_threshold = -0.20

说明：
- 这一步风险较高，因为止损更敏感容易降低回撤，也容易伤害收益恢复
- 因此只作为第三顺位，不提前大规模展开

## 5. 每一阶段的输出格式

每个阶段必须固定输出以下内容：

### 结果表
至少包含：
- Full sample：年化 / 夏普 / 最大回撤 / 调仓次数
- Test：年化 / 夏普 / 最大回撤
- Walk-forward：平均年化 / 平均夏普 / 平均最大回撤 / 窗口数

### 阶段结论
只回答三件事：
1. 本阶段谁胜出
2. 是否替代当前正式主线
3. 是否进入下一阶段

### 阶段性反馈
说明：
- 回撤改善是否真实
- 改善代价是什么
- 是“更稳健”还是只是“更保守”

## 6. 新方案替代正式主线的接受标准

候选低回撤方案若要替代当前正式主线，建议满足以下至少 4 条：

1. Full sample 最大回撤改善 ≥ 1.0 个百分点
2. Walk-forward 平均最大回撤不劣于当前基线
3. Test 夏普不低于当前基线 0.15 以上
4. Full sample 年化降幅不超过 1.0 个百分点
5. 调仓次数不显著恶化（增加不超过 15%）
6. Walk-forward 中参数表现没有明显漂移

若只满足“回撤更低”但收益、样本外或稳定性明显变差，则只作为“低回撤观察分支”，不替代正式主线。

## 7. 推荐的执行节奏

推荐按以下顺序推进：
1. Stage7A：max_single_weight 3组
2. Stage7B：cooldown 3组
3. Stage7C：stop_loss_threshold 3组（仅必要时）

命名建议：
- stage7a-max-single-weight-low-drawdown.md
- stage7b-cooldown-low-drawdown.md
- stage7c-stop-loss-low-drawdown.md

preset 建议命名：
- stage7a_max_single_weight_030.json
- stage7a_max_single_weight_0325.json
- stage7a_max_single_weight_0350.json
- stage7b_cooldown15_on_lowdd.json
- stage7b_cooldown20_on_lowdd.json
- stage7b_cooldown25_on_lowdd.json

## 8. 当前建议结论

若目标是“尽量不动主线骨架，只尝试把回撤再压低一点”，推荐优先级如下：

1. 首先验证 max_single_weight = 0.30 / 0.325 / 0.35
2. 其次验证 cooldown_days = 15 / 20 / 25
3. 最后才考虑 stop_loss_threshold 微调

一句话判断：
- 最有希望的低回撤杠杆是“集中度约束优化”
- 最值得重点观察的候选值是 max_single_weight = 0.325
- 若要做更平滑版本，cooldown = 15 是自然候选分支
