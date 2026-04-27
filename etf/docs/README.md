# ETF 项目文档库

状态：In Progress
更新日期：2026-04-15

## 文档库目标

本库用于支撑 ETF 动量轮动项目的：
1. 分步推进
2. 代码实施
3. 实验记录
4. 决策追溯
5. 阶段复盘

原则：
- 一页一主题
- 结论与过程分离
- 决策必须可追溯
- 回测与实盘分开记录
- 文档服务执行，而不是为了好看

## 阅读顺序

首次接手项目时，建议按以下顺序阅读：
1. `00-index/project-overview.md`
2. `00-index/current-status.md`
3. `10-strategy/strategy-overview.md`
4. `10-strategy/factor-definition.md`
5. `30-implementation/code-structure.md`
6. `40-operations/daily-runbook.md`
7. `50-decisions/decision-log-index.md`

## 目录说明

- `00-index/`：导航与当前状态
- `10-strategy/`：策略定义、因子、ETF池、回测/实盘一致性
- `20-research-and-backtest/`：测试计划、实验矩阵、结果摘要、分析结论
- `30-implementation/`：代码结构、数据流、文件职责
- `40-operations/`：日常运行、数据维护、故障排查
- `50-decisions/`：重要决策与决策索引
- `60-reviews/`：阶段复盘
- `70-templates/`：统一模板
- `80-archive/`：旧资料索引、失效方案、历史说明

## 当前重点文档

- 项目总览：`00-index/project-overview.md`
- 当前状态：`00-index/current-status.md`
- 因子定义：`10-strategy/factor-definition.md`
- 本轮因子测试计划：`20-research-and-backtest/plans/factor-test-plan-v1.md`
- 实验矩阵：`20-research-and-backtest/experiment-matrix.md`
- 阶段1结果摘要：`20-research-and-backtest/results/stage1-factor-comparison-summary.md`
- 代码结构：`30-implementation/code-structure.md`
- 因子模板映射：`30-implementation/factor-template-to-preset-mapping.md`
- 日常运行手册：`40-operations/daily-runbook.md`
- 决策索引：`50-decisions/decision-log-index.md`
- 历史资料索引：`80-archive/legacy-notes-index.md`

## 维护规则

- 每轮实验至少留下：计划、结果摘要、决策、复盘四类文档痕迹。
- 每次重要参数调整都必须补一条决策记录或参数变更记录。
- 若实盘逻辑与回测逻辑出现分叉，必须优先更新策略文档与决策索引。
