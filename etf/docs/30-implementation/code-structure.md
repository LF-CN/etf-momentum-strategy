# 代码结构

状态：In Progress
更新日期：2026-04-15

## 1. 目的

本页用于说明当前 ETF 项目的主要代码文件、职责边界与数据流位置，帮助后续实施、重构与多智能体接手。

## 2. 核心文件概览

### 每日与实盘侧
- `../daily_task_full.py`
  - 每日任务主入口
  - 负责读取数据、补当日价格、生成信号
  - 当前已包含今日价格 fallback 与 CSV 写回逻辑

- `../strategy_full.py`
  - 实盘策略侧核心逻辑
  - 需要与回测 ETF 池和关键规则保持可对照

- `../generate_daily_signal_message.py`
  - 将信号结果格式化成对用户友好的消息

- `../config.py`
  - 项目配置入口之一

### 回测侧
- `../windows_backtest_package/core/momentum_backtest.py`
  - 回测主引擎
  - 包含打分、目标权重、触发条件、调仓执行、回测指标统计

- `../windows_backtest_package/core/run_preset.py`
  - 预设驱动入口
  - 从 preset 读取参数并执行回测

- `../windows_backtest_package/presets/`
  - 各类回测预设文件

- `../windows_backtest_package/results/`
  - 回测结果 JSON 输出目录

### 数据侧
- `../windows_backtest_package/etf_data/`
  - ETF 历史 CSV 数据

- `../data/signal.json`
  - 每日信号输出

## 3. 当前结构关系

当前项目可粗略分为三层：

1. 数据层
   - ETF 历史 CSV
   - 每日信号 JSON

2. 逻辑层
   - 回测引擎
   - 实盘策略
   - 每日消息生成

3. 执行层
   - daily_task_full.py
   - run_preset.py
   - bat / preset 文件

## 4. 当前已知需要持续关注的边界

### 回测与实盘一致性边界
需持续对照：
- ETF 池
- 目标权重逻辑
- 关键阈值
- 调仓触发逻辑

### 数据维护边界
需持续对照：
- 历史 CSV 来源与补齐逻辑
- 当日价格 fallback
- 写回 CSV 的规则

## 5. 建议后续补充的实现文档

建议后续继续补：
- `data-flow.md`
- `file-responsibilities.md`
- `config-reference.md`
- `live-vs-backtest-consistency.md`

## 6. 旧资料索引

历史说明可参考：
- `../../PLAN.md`
- `../../strategy_parameter_inventory.md`
- `../../validation_framework_notes.md`
- `../../backtest_engine_upgrade_notes.md`
