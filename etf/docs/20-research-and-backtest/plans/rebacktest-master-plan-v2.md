# ETF 动量轮动策略重新回测总计划 V2

状态：Draft
更新日期：2026-04-16
适用范围：修复后回测引擎的全量重跑
执行原则：本轮以本文件为唯一执行口径；旧文档保留，仅作历史参考

## 1. 为什么要重写这份计划

本轮不是普通复跑，而是“修复关键问题后的重新验证”。旧研究结论中有一部分建立在错误或不完整的执行口径上，因此需要形成新的执行主线。

本轮重写计划的主要原因：
1. `factor_weights` 曾未正确接入，导致不同因子模板可能没有按预期生效
2. `style_factors` 曾未正确接入，style on/off 结果的可信度曾受影响
3. `cooldown_days` 历史上存在“自然日 vs 开盘日”口径偏差，旧结果不能直接与新结果横向比较
4. 当前项目内同时存在多套历史结论（F4 优先 / F6 优先 / F5 样本外更强），需要新的统一裁决流程

结论：
- 旧文档不删除
- 旧结果不再作为当前轮次的直接决策依据
- 本轮从 Stage1 开始，按统一口径重新形成完整结果链

## 2. 本轮总目标

在修复后的回测引擎上，重新完成 Stage1 ~ Stage5 的全链路验证，最终锁定一套“可解释、可复现、不过拟合”的 ETF 动量轮动基线配置。

最终输出至少包括：
1. 每阶段结果摘要文档
2. 每阶段晋级/淘汰决策文档
3. 最终基线参数文档
4. 一份明确说明旧结果失效原因的记录文档

## 3. 本轮统一冻结口径

除非在阶段评审中明确批准，不得中途修改以下口径：

### 3.1 数据区间
- 起始：`2016-01-01`
- 结束：优先与当前 preset 保持一致，即 `2026-04-14`
- 如需统一更新到更新日期，必须在正式开跑前一次性更新所有 preset，不能只改部分阶段

### 3.2 ETF 池
固定为当前 5 只 ETF，不在本轮阶段中途换池：
- 中证500ETF
- 纳指ETF
- 黄金ETF
- 国债ETF
- 消费ETF

### 3.3 基础参数
- `initial_capital = 52000`
- `signal_weight = 0.20`
- `stop_loss_threshold = -0.18`
- `lookback_period = 30`
- `transaction_cost = 0.0002`
- `min_holding = 1000`

### 3.4 基础约束
- 当前 preset 统一使用：`max_single_weight = 0.35`
- 由于你已决定“从 Stage1 全量跑”，本轮建议先保持 `0.35` 不变，完成整套阶段验证后，再判断是否单独开启“max_single_weight 再优化支线”
- 原因：若现在把 `0.35` 与 `0.325` 混入主线，会导致主线与旧 preset 大面积不一致，增加解释成本

### 3.5 三层验证框架
所有正式阶段 preset 都必须保留：
- Full Sample
- Train/Test（70/30）
- Walk-Forward（3年训练 + 1年测试 + 1年步长）

固定验证参数：
- `train_ratio = 0.7`
- `train_days = 756`
- `test_days = 252`
- `step_days = 252`

## 4. 阶段总览

### Stage1：因子模板对比
目标：确定哪类因子结构真正提供边际贡献

变化项：
- 6 套因子模板（F1~F6）

固定项：
- `style_factors = 1.0` 全中性化
- `top_n = 3`
- `trigger_deviation = 0.20`
- `lookback_period = 30`
- `cooldown_days = 20`
- `max_single_weight = 0.35`

候选模板：
- F1：仅 20 日动量
- F2：20 日 + 60 日动量
- F3：20 日 + 60 日 + 动量强度
- F4：20 日 + 60 日 + 波动率奖励
- F5：20 日 + 60 日 + R² 趋势稳定性
- F6：五因子全开

输出：
1. 因子对比表
2. 边际贡献分析
3. 样本内/样本外对比
4. 晋级名单（建议 2~3 套）

晋级规则：
1. 夏普优先
2. 最大回撤不能显著恶化
3. 调仓次数不应明显膨胀
4. Walk-Forward 样本外不能塌陷
5. 最近两个滚动窗口不应显著落后

### Stage2：style on / off
目标：判断风格乘数是否值得继续保留

输入：
- Stage1 晋级模板（建议 2~3 套）

变化项：
- `style_on`
- `style_off`

固定项：
- 保持 Stage1 晋级模板其它参数不变
- `top_n = 3`
- `cooldown_days = 20`
- `trigger_deviation = 0.20`

输出：
1. 各模板 style on/off 对比
2. 是否统一进入 style_off 的结论
3. 主方案与稳健对照方案

判定重点：
- style 是否在样本外稳定提升 Sharpe
- style 是否改善回撤而非单纯提高收益波动
- style 是否只在单一阶段或单一窗口有效

### Stage3：top_n 持仓数
目标：确定组合集中度

输入：
- Stage2 胜出方案

变化项：
- `top_n = 2 / 3 / 4`

固定项：
- 使用 Stage2 胜出的因子结构与 style 配置
- `cooldown_days = 20`
- `trigger_deviation = 0.20`

输出：
1. 集中度对比表
2. 风险收益与换手解释
3. 最终持仓数结论

### Stage4：cooldown 冷却期
目标：确定换手率与择时效率的平衡点

输入：
- Stage3 胜出方案

变化项：
- 当前建议统一测试：`10 / 15 / 20`

说明：
- 历史 preset 中存在 `5 / 10 / 14 / 15 / 20` 多套口径
- V2 主线建议只保留一套正式比较口径，优先采用 `10 / 15 / 20`
- `14` 可保留为历史参考，不再纳入本轮正式主比较组

输出：
1. 冷却期对比表
2. 调仓频次变化
3. 最终冷却期结论

### Stage5：trigger_deviation 触发偏差
目标：确定信号灵敏度

输入：
- Stage4 胜出方案

变化项：
- `trigger_deviation = 0.15 / 0.20 / 0.25`

固定项：
- 其它参数全部沿用 Stage4 胜出方案

输出：
1. 触发偏差对比表
2. 最近窗口表现对比
3. 最终信号阈值结论

### Stage6：最终基线确认（新增收尾阶段）
目标：避免最终参数来自“分阶段拼接但未全局复核”

输入：
- Stage5 胜出方案

动作：
- 使用最终参数重新完整跑一次 full sample + train/test + walk-forward
- 输出正式基线文档

输出：
1. `final-baseline-v2.md`
2. 最终推荐参数
3. 风险提示
4. 实盘使用建议

## 5. 文档与结果产出清单

### 5.1 总计划与实验矩阵
- 新增：`/opt/data/scripts/etf/docs/20-research-and-backtest/plans/rebacktest-master-plan-v2.md`
- 更新：`/opt/data/scripts/etf/docs/20-research-and-backtest/experiment-matrix.md`

### 5.2 每阶段结果摘要（建议文件名）
- `results/stage1-factor-comparison-summary-v2.md`
- `results/stage2-style-on-off-summary-v2.md`
- `results/stage3-topn-summary-v2.md`
- `results/stage4-cooldown-summary-v2.md`
- `results/stage5-trigger-deviation-summary-v2.md`
- `results/final-baseline-v2.md`

### 5.3 决策记录（建议文件名）
- `50-decisions/DEC-0006-stage1-v2-winners.md`
- `50-decisions/DEC-0007-stage2-v2-style-verdict.md`
- `50-decisions/DEC-0008-stage3-v2-topn-verdict.md`
- `50-decisions/DEC-0009-stage4-v2-cooldown-verdict.md`
- `50-decisions/DEC-0010-stage5-v2-trigger-verdict.md`

### 5.4 旧结果失效说明
建议新增：
- `20-research-and-backtest/results/historical-results-invalidity-note.md`

用于说明：
- 哪些旧结果受旧 bug 影响
- 哪些旧 cooldown 结果口径不同
- 为什么新旧结果不能直接比较

## 6. 当前 preset 审核结论

### 6.1 可直接用于 V2 主线的 preset
Stage1：
- `stage1_f1_momentum20_only.json`
- `stage1_f2_momentum20_60.json`
- `stage1_f3_add_strength.json`
- `stage1_f4_add_volatility_reward.json`
- `stage1_f5_add_r_squared.json`
- `stage1_f6_full_factor.json`

Stage2：
- `stage2_f4_style_on.json`
- `stage2_f4_style_off.json`
- `stage2_f5_style_on.json`
- `stage2_f5_style_off.json`
- `stage2_f6_style_on.json`
- `stage2_f6_style_off.json`

Stage3：
- `stage3_f6_top2_style_off.json`
- `stage3_f6_top3_style_off.json`
- `stage3_f6_top4_style_off.json`

Stage4：
- `stage4_cooldown10_style_off.json`
- `stage4_cooldown15_style_off.json`
- `stage4_cooldown20_style_off.json`

### 6.2 应视为历史参考、不纳入本轮主线的 preset
主要是旧 `cooldown14` 系列：
- `stage1_f*_cooldown14.json`
- `stage2_f*_cooldown14.json`
- `stage3_top*_cooldown14.json`
- `stage4_cooldown14_style_off.json`

原因：
1. 命名和主线口径混杂
2. 与本轮建议的 `cooldown=20` 主线不一致
3. 容易在结果整理阶段造成误引用

### 6.3 当前缺口
Stage5 的正式 preset 当前未看到成体系文件，需要补齐：
- `stage5_trigger015_*.json`
- `stage5_trigger020_*.json`
- `stage5_trigger025_*.json`

说明：
- 是否生成 3 个固定 preset，还是 1 个带 `param_grid` 的 Stage5 preset，可在执行前决定
- 若以“可追溯和清晰归档”为优先，建议采用 3 个独立 preset

## 7. 本轮执行顺序

### 步骤 1：冻结 V2 主线口径
确认本文件内容后，不再随意插入新参数维度

### 步骤 2：清点并必要时补齐 preset
重点处理：
1. Stage5 preset 缺口
2. 是否需要新增 Stage6 final baseline preset
3. 是否要把结果文件名统一升级为 `-v2` 口径文档引用

### 步骤 3：正式启动 Stage1 全量回测
执行顺序：F1 → F2 → F3 → F4 → F5 → F6

### 步骤 4：根据 Stage1 结果形成晋级决策
建议保留 2~3 套方案进入 Stage2

### 步骤 5：依次推进 Stage2 → Stage5
每阶段完成后先出摘要，再决定下一阶段，不跳步

### 步骤 6：执行 Stage6 最终基线确认
形成本轮唯一的最终策略文档

## 8. 结果解释优先级

每阶段出结果后，统一按以下顺序解释：
1. 先看样本外稳定性（Train/Test + Walk-Forward）
2. 再看全样本收益与夏普
3. 再看回撤与调仓次数
4. 最近两个滚动窗口表现作为辅助证据，不单独决定晋级

## 9. 暂定执行建议

本轮先不要把以下问题混进主线：
- `max_single_weight` 再优化（0.35 vs 0.325）
- ETF 池扩容
- 止损阈值重扫
- lookback period 再优化

这些都属于“第二条研究支线”，不应打断本轮从 Stage1 开始的主验证链路。

## 10. 下一步

执行优先级建议：
1. 依据本计划补齐 Stage5 preset
2. 更新实验矩阵，明确 V2 主线与历史参考 preset 的边界
3. 正式启动 Stage1 全量回测
4. 生成 Stage1 V2 摘要与晋级决策

---

备注：
- 本文件是“重新回测主线计划”，不是最终策略结论
- 最终结论必须以 Stage6 文档为准
