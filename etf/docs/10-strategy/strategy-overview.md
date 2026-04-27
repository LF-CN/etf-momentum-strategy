# ETF 动量轮动策略正式文档

状态：Formal / Active
更新日期：2026-04-16
版本：Stage7 低回撤正式基线

## 1. 文档目的

本文档用于定义 ETF 动量轮动策略的正式口径，作为：
1. 实盘执行依据
2. 回测复核依据
3. 参数变更的对照基线
4. 后续文档、提醒脚本、服务接口的统一参考

原则：
- 实盘逻辑必须与回测逻辑同源
- 正式参数必须以最新定稿决策为准
- 历史阶段结论可保留，但不得覆盖当前正式基线

## 2. 策略定位

这是一个围绕 5 只 ETF 的中频动量轮动与调仓辅助系统。

目标不是追求极端收益，而是：
- 在可接受回撤下获取长期正收益
- 尽量跑赢中国通胀
- 用较稳定的风险收益比实现可执行、可坚持的实盘策略

它不是“分数最高就满仓买入”的简单轮动，而是由以下几层组成：
1. 多因子动量打分
2. 基础权重上的加减仓分配
3. top_n 持仓截断
4. 单资产上限与最小持仓约束
5. 偏离度阈值 + 强信号触发调仓
6. 冷却期与止损机制

## 3. ETF 池

正式 ETF 池固定为 5 只：
- 510500 中证500ETF
- 159941 纳指ETF
- 518880 黄金ETF
- 511010 国债ETF
- 159928 消费ETF

基础权重结构：
- 中证500ETF：25%
- 纳指ETF：25%
- 黄金ETF：20%
- 国债ETF：20%
- 消费ETF：10%

说明：
- 消费ETF保留在正式池中，原因是其对组合有防御补充作用。
- 当前主线不新增 ETF，也不缩减 ETF 池。

## 4. 正式基线版本

当前正式基线为：Stage7 低回撤正式基线。

主线定义：
- F6 因子模板
- style_off
- top_n = 3
- cooldown_days = 20
- trigger_deviation = 0.25
- stop_loss_threshold = -0.18
- max_single_weight = 0.325

与上一版正式基线（Stage6）的唯一区别：
- Stage6：max_single_weight = 0.35
- Stage7：max_single_weight = 0.325

本次切换理由：
- 在不破坏主线结构的前提下，降低了全样本最大回撤
- 保留了较好的收益能力与样本外稳健性
- 更符合“先控制回撤，再追求长期稳健增值”的实盘目标

## 5. 正式参数

### 5.1 策略参数
- trigger_deviation = 0.25
- signal_weight = 0.20
- stop_loss_threshold = -0.18
- lookback_period = 30
- cooldown_days = 20
- top_n = 3
- transaction_cost = 0.0002
- max_single_weight = 0.325
- min_holding = 1000
- initial_capital = 52000

### 5.2 因子模板（F6）
- momentum_20d = 400
- momentum_60d = 150
- momentum_strength = 200
- volatility_reward = 50
- r_squared = 30

### 5.3 style 口径
当前正式主线采用 style_off，即风格因子统一中性化处理：
- small_cap = 1.0
- growth = 1.0
- mid_cap = 1.0
- large_cap = 1.0
- tech = 1.0
- cyclical = 1.0
- defensive = 1.0
- gov_bond = 1.0
- convertible = 1.0
- commodity = 1.0
- a_share = 1.0
- us_tech = 1.0

## 6. 策略逻辑总流程

1. 获取 ETF 历史价格数据
2. 计算每只 ETF 的多因子动量得分
3. 按得分排序
4. 在基础权重框架上进行动量加减仓
5. 只保留前 top_n 个标的
6. 应用单资产上限、最小持仓等约束
7. 生成目标权重
8. 将当前权重与目标权重进行比较
9. 判断是否满足调仓条件：
   - 偏离度是否超过阈值
   - 是否存在强信号
   - 是否触发止损
   - 是否满足冷却期要求
10. 若满足条件则给出调仓建议，否则维持当前仓位

## 7. 调仓与风控原则

### 7.1 调仓触发
策略不是每天都调仓，而是触发型调仓。

核心判断包括：
- 偏离度是否超过 trigger_deviation
- 是否出现强信号
- 是否处于 cooldown_days 冷却期内

### 7.2 风控约束
- 单资产上限：32.5%
- 最大持仓数：3
- 止损阈值：-18%
- 最小持仓单位：1000
- 交易成本：0.02% 单边

### 7.3 设计目的
这些约束的目标不是“降低交易频率本身”，而是：
- 避免单一资产过度集中
- 避免轻微信号反复触发无效换手
- 在组合失衡时优先回到可控区间
- 让策略更适合长期执行而非高频博弈

## 8. 回测验证结论

### 8.1 当前正式基线结果（Stage7）
回测区间：2016-01-01 ~ 2026-04-14

- Full sample：年化 15.10%，夏普 1.05，最大回撤 -14.07%，调仓 114 次
- Test：年化 26.42%，夏普 1.93，最大回撤 -10.83%
- Walk-forward：平均年化 13.02%，平均夏普 0.94，平均最大回撤 -7.39%
- 参数稳定性：best_params_frequency = 6/6

### 8.2 结果解释
这组结果说明：
- 策略已不只是“避免亏钱”
- 在风险调整后收益层面达到可正式执行标准
- 长期目标上，具备跑赢中国通胀的能力
- 同时回撤水平较 Stage6 更友好

### 8.3 与 Stage6 历史基线对比
- Stage6：年化 14.47%，夏普 0.99，最大回撤 -15.42%
- Stage7：年化 15.10%，夏普 1.05，最大回撤 -14.07%

结论：
Stage7 在保持主线结构稳定的前提下，实现了“收益不降、回撤更低”的正式升级。

## 9. 实盘提醒链路

正式提醒链路：
- `/opt/data/scripts/etf/generate_daily_signal_message.py`
  -> `/opt/data/scripts/etf/daily_task_full.py`

兼容入口：
- `/opt/data/scripts/etf/daily_task.py`

服务层：
- `/opt/data/scripts/etf/etf_service.py`

正式配置入口：
- `/opt/data/scripts/etf/config.py`

回测 preset 入口：
- `/opt/data/scripts/etf/windows_backtest_package/core/run_preset.py`
- `/opt/data/scripts/etf/windows_backtest_package/presets/stage7_final_low_drawdown_baseline_v3.json`

原则：
- 不能只改 config.py 就视为完成
- 每次参数更新后，都必须验证提醒主链路、兼容入口和服务层输出一致

## 10. 已完成的一致性验证

在 Stage7 正式基线切换后，已实际验证：
- `python3 /opt/data/scripts/etf/daily_task.py`：成功
- `python3 /opt/data/scripts/etf/generate_daily_signal_message.py`：成功
- `ETFService().calculate_signals()`：成功
- `signal.json` / `ETFService().calculate_signals()` / `daily_task_full.run_daily_task()`：关键字段比对 all_equal = true

本轮验证下的实测信号：
- 日期：2026-04-16
- 结论：暂不调仓
- 原因类型：no_trigger
- 原因：偏离度 9.78% < 阈值，无强信号
- 目标权重：
  - 510500：27.6%
  - 159941：34.3%
  - 511010：38.1%
  - 518880：0.0%
  - 159928：0.0%

## 11. 正式执行口径

后续凡涉及以下事项，均以本文档为正式口径：
- 实盘每日提醒
- 回测结果引用
- 参数是否一致的核查
- 策略对外说明
- 后续优化是否偏离主线的判断

若后续再调整参数，必须同时补：
1. 结果摘要文档
2. 决策文档
3. 本正式文档更新

## 12. 相关文档

- 决策文档：`../50-decisions/DEC-0012-stage7-low-drawdown-baseline-adopted.md`
- 结果摘要：`../20-research-and-backtest/results/stage7-low-drawdown-baseline-switch-summary.md`
- 低回撤专项计划：`../20-research-and-backtest/plans/low-drawdown-validation-plan-v1.md`
- 历史正式基线：`../20-research-and-backtest/results/stage6-final-baseline-confirmation-v2.md`

## 13. 一句话总结

当前正式策略是一套以“控制回撤、长期跑赢通胀、保持实盘可执行性”为核心目标的 5ETF 多因子动量轮动系统；其当前正式版本为 Stage7 低回撤基线，参数口径已经完成回测与实盘提醒链路统一。 
