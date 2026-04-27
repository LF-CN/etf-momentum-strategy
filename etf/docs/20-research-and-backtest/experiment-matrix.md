# 实验矩阵（V2 重跑主线）

状态：Active
更新日期：2026-04-16
适用范围：修复后回测引擎的正式重跑

## 1. 目的

本页用于固定“这一轮到底跑什么、按什么顺序跑、每阶段比较什么”，避免再次出现：
- 同名实验口径不一致
- 旧结论混入新结论
- 不知道某个结果文件属于哪一轮
- 结果摘要与 preset 对不上

本页只记录 V2 主线，不再承载历史结果。

## 2. 全局统一口径

### 2.1 数据区间
- 起始：`2016-01-01`
- 结束：`2026-04-14`

### 2.2 ETF 池
固定 5 只 ETF：
- 中证500ETF
- 纳指ETF
- 黄金ETF
- 国债ETF
- 消费ETF

### 2.3 全局固定参数
- `initial_capital = 52000`
- `signal_weight = 0.20`
- `stop_loss_threshold = -0.18`
- `lookback_period = 30`
- `transaction_cost = 0.0002`
- `min_holding = 1000`
- `max_single_weight = 0.35`

### 2.4 验证框架
所有主线实验都必须保留：
- Full Sample
- Train/Test（70/30）
- Walk-Forward（3年训练 + 1年测试 + 1年步长）

固定验证参数：
- `train_ratio = 0.7`
- `train_days = 756`
- `test_days = 252`
- `step_days = 252`

## 3. 阶段 1：六套因子模板对比

目标：只比较因子贡献，不比较风格偏置。

固定项：
1. `style_factors = 1.0`（全中性）
2. `top_n = 3`
3. `trigger_deviation = 0.20`
4. `lookback_period = 30`
5. `cooldown_days = 20`
6. `max_single_weight = 0.35`

### Stage1 预设清单

| 模板 | 定义 | preset 文件 | 说明 |
|------|------|-------------|------|
| F1 | 仅 20 日动量 | `presets/stage1_f1_momentum20_only.json` | 最简基线 |
| F2 | 20 日 + 60 日动量 | `presets/stage1_f2_momentum20_60.json` | 加入长期趋势确认 |
| F3 | 20 日 + 60 日 + 动量强度 | `presets/stage1_f3_add_strength.json` | 验证强度因子边际贡献 |
| F4 | 20 日 + 60 日 + 波动率奖励 | `presets/stage1_f4_add_volatility_reward.json` | 验证低波奖励 |
| F5 | 20 日 + 60 日 + R² | `presets/stage1_f5_add_r_squared.json` | 验证趋势稳定性 |
| F6 | 五因子全开 | `presets/stage1_f6_full_factor.json` | 当前最完整因子结构 |

### Stage1 执行顺序
1. F1
2. F2
3. F3
4. F4
5. F5
6. F6

### Stage1 输出要求
每个 preset 至少提取：
1. 全样本年化收益
2. 全样本夏普比率
3. 全样本最大回撤
4. 全样本调仓次数
5. Train/Test 的测试期表现
6. Walk-Forward 平均样本外夏普
7. 最近两个滚动窗口表现

### Stage1 晋级规则
建议晋级 2~3 套方案，标准：
1. 夏普更高
2. 最大回撤不明显恶化
3. 调仓次数不过度增加
4. 样本外表现不塌
5. 最近窗口不过度落后

## 4. 阶段 2：style on / off

目标：判断风格乘数是否提供稳定增益。

输入：Stage1 晋级模板（建议 2~3 套）

固定项：
- 因子结构沿用 Stage1 胜出方案
- `top_n = 3`
- `trigger_deviation = 0.20`
- `cooldown_days = 20`
- `max_single_weight = 0.35`

### 已准备的 Stage2 预设
- `presets/stage2_f4_style_on.json`
- `presets/stage2_f4_style_off.json`
- `presets/stage2_f5_style_on.json`
- `presets/stage2_f5_style_off.json`
- `presets/stage2_f6_style_on.json`
- `presets/stage2_f6_style_off.json`

### Stage2 输出要求
1. style_on vs style_off 横向对比
2. 样本外是否提升
3. 是否统一进入 style_off 主线

## 5. 阶段 3：top_n 持仓数

目标：确定组合集中度。

输入：Stage2 胜出方案

变化项：
- `top_n = 2 / 3 / 4`

### 已准备的 Stage3 预设
- `presets/stage3_f6_top2_style_off.json`
- `presets/stage3_f6_top3_style_off.json`
- `presets/stage3_f6_top4_style_off.json`

说明：
- 当前现成预设基于 F6 + style_off
- 若 Stage2 重跑后主方案变化，应按新胜出方案复制改写对应文件

## 6. 阶段 4：cooldown 冷却期

目标：平衡换手率与择时效率。

输入：Stage3 胜出方案

V2 正式比较组：
- `cooldown_days = 10 / 15 / 20`

### 已准备的 Stage4 预设
- `presets/stage4_cooldown10_style_off.json`
- `presets/stage4_cooldown15_style_off.json`
- `presets/stage4_cooldown20_style_off.json`

说明：
- 旧 `cooldown14` 系列不纳入 V2 主线
- `cooldown5` 保留在 preset 目录中，但不作为主比较组

## 7. 阶段 5：trigger_deviation 触发偏差

目标：确定信号灵敏度。

输入：Stage4 胜出方案

V2 正式比较组：
- `trigger_deviation = 0.15 / 0.20 / 0.25`

### Stage5 预设清单
- `presets/stage5_trigger015_style_off.json`
- `presets/stage5_trigger020_style_off.json`
- `presets/stage5_trigger025_style_off.json`

说明：
- 当前 Stage5 预设默认基于“F6 + style_off + top_n=3 + cooldown_days=20”主线候选
- 若 Stage1~Stage4 新结果改变主方案，应先复制并改写 Stage5 preset 再执行

## 8. 阶段 6：最终基线确认

目标：对最终胜出参数做一次完整复核。

要求：
1. 用最终参数重新跑 full sample + train/test + walk-forward
2. 生成最终基线文档
3. 给出实盘使用口径与风险提示

## 9. 本轮不纳入主线的内容

以下内容暂不混入本轮主线：
- `max_single_weight` 再优化（0.35 vs 0.325）
- ETF 池扩容
- 止损阈值重扫
- lookback period 再优化
- 旧 cooldown14 系列结果复用

这些内容如需研究，应在主线完成后另开支线。

## 10. 当前执行建议

建议立即按以下顺序推进：
1. Stage1 全量重跑
2. 生成 Stage1 V2 摘要与晋级裁决
3. 用晋级方案跑 Stage2
4. 再进入 Stage3 ~ Stage5
5. 最后执行 Stage6 最终基线确认

## 11. 一句话规则

从现在开始：
- `windows_backtest_package/results/` 中的新文件 = V2 有效结果
- `docs/20-research-and-backtest/results/` 中的新摘要 = V2 有效结论
- archive 目录中的旧结果与旧结论 = 历史参考，不参与当前裁决
