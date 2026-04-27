# 当前状态说明（V2 重跑前）

状态：Active
更新日期：2026-04-16
适用范围：ETF 动量轮动策略重新回测主线

## 1. 当前结论状态

旧回测结果与旧阶段结论，已不再作为本轮主线决策依据。

原因：
1. 历史上存在 `factor_weights` 未完整生效的问题
2. 历史上存在 `style_factors` 未完整生效的问题
3. `cooldown_days` 曾出现自然日 / 开盘日口径偏差
4. 旧结果与新结果之间不具备严格可比性

因此：
- 旧结果：仅作历史参考
- 新一轮结果：从 Stage1 开始重新建立
- 本轮唯一执行主线：`rebacktest-master-plan-v2.md`

## 2. 已执行的清理动作

本次未删除历史文件，而是执行了“归档隔离”。

归档目录：
`/opt/data/scripts/etf/archive/invalidated_2026-04-16`

已归档内容：
1. 旧回测结果目录 `windows_backtest_package/results`
2. 旧结果摘要目录 `docs/20-research-and-backtest/results`
3. 旧实验矩阵 `experiment-matrix.md`
4. 旧计划文档 `factor-test-plan-v1.md`
5. 旧阶段决策文档：
   - `DEC-0003-staged-factor-validation-first.md`
   - `DEC-0004-stage1-factor-template-winners.md`
   - `DEC-0005-stage2-style-verdict.md`

归档清单文件：
`/opt/data/scripts/etf/archive/invalidated_2026-04-16/archive_manifest.json`

## 3. 当前保留内容

以下内容保留为本轮可继续使用的主线资产：

1. V2 总计划：
`/opt/data/scripts/etf/docs/20-research-and-backtest/plans/rebacktest-master-plan-v2.md`

2. 全部 preset 模板：
`/opt/data/scripts/etf/windows_backtest_package/presets/`

3. 新建的空结果目录：
- `windows_backtest_package/results/`
- `docs/20-research-and-backtest/results/`

## 4. 当前项目状态

当前状态可概括为：

- 旧数据：已归档，不再混入主线
- 旧结论：已归档，不再作为当前裁决依据
- 主计划：已重建为 V2
- 主线结果目录：已清空，可直接承接新一轮回测
- preset：大部分可复用
- 缺口：Stage5 preset 仍需补齐

## 5. 接下来应执行的步骤

建议顺序：
1. 补齐 Stage5 trigger_deviation 的正式 preset
2. 重建新的 experiment-matrix（V2 口径）
3. 启动 Stage1 全量回测
4. 产出新的 Stage1 结果摘要与晋级裁决

## 6. 一句话结论

当前环境已完成“历史结果隔离 + 主线清场”。

从现在开始，凡是进入 `windows_backtest_package/results/` 和 `docs/20-research-and-backtest/results/` 的文件，都视为新一轮 V2 回测结果。
