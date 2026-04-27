# 项目总览

状态：Validated
更新日期：2026-04-16

## 1. 项目目标

构建一个围绕 5 只 ETF 的动量轮动研究与实盘辅助系统，当前重点是：
1. 保持回测逻辑与实盘逻辑一致
2. 稳定生成每日信号
3. 系统化验证因子与参数
4. 为后续长期迭代建立可回看的知识库

## 2. 当前项目范围

当前 ETF 池固定为 5 只：
- 510500 中证500ETF
- 159941 纳指ETF
- 518880 黄金ETF
- 511010 国债ETF
- 159928 消费ETF

当前研究边界：
- 先不新增 ETF
- 先研究原 5 只 ETF 下的因子贡献、风格偏置、持仓规则与调仓参数

## 3. 当前主线任务

当前主线：固定 5 只 ETF，建立因子测试框架，识别：
1. 哪些因子真正提供增益
2. style_factor 是否是必要设计
3. top_n、lookback、trigger_deviation、cooldown 的稳健组合

对应计划文档：
- `../20-research-and-backtest/plans/factor-test-plan-v1.md`

## 4. 当前系统组成

核心代码：
- `../daily_task_full.py`：每日信号主流程，含今日价格 fallback 与 CSV 写回
- `../strategy_full.py`：实盘侧策略逻辑
- `../generate_daily_signal_message.py`：消息生成
- `../windows_backtest_package/core/momentum_backtest.py`：回测引擎
- `../windows_backtest_package/core/run_preset.py`：预设回测入口

关键数据：
- `../windows_backtest_package/etf_data/`：历史 CSV 数据
- `../data/signal.json`：每日信号输出
- `../windows_backtest_package/results/`：回测结果 JSON

## 5. 当前基线认知

已知当前程序不是单一动量模型，而是：
- 多因子打分
- 风格乘数修正
- 基础权重加减仓
- 触发型调仓
- 止损与冷却期约束

详见：
- `../10-strategy/factor-definition.md`
- `../10-strategy/strategy-overview.md`

## 6. 当前风险点

1. 因子、风格偏置、调仓规则混在一起，容易误判真正有效来源
2. 回测结论较多，若不系统记录，后续容易失去决策依据
3. 实盘与回测若发生分叉，后续所有结论都会失真
4. 当前已有说明文档较分散，需要纳入统一索引

## 7. 推荐阅读顺序

1. 当前状态：`current-status.md`
2. 策略概览：`../10-strategy/strategy-overview.md`
3. 因子定义：`../10-strategy/factor-definition.md`
4. 代码结构：`../30-implementation/code-structure.md`
5. 测试计划：`../20-research-and-backtest/plans/factor-test-plan-v1.md`
6. 决策索引：`../50-decisions/decision-log-index.md`
7. 历史资料：`../80-archive/legacy-notes-index.md`

## 8. 下一里程碑

里程碑：完成第一轮因子拆解测试

完成标准：
1. 固定 5 只 ETF
2. 跑完第一轮 6 套因子模板对比
3. 形成结果摘要页
4. 形成至少一条正式决策记录（例如：保留/弱化/移除某类因子或是否继续保留 style_factor）
