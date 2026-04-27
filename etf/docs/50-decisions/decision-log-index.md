# 决策索引

状态：In Progress
更新日期：2026-04-15

## 目的

用于集中记录重要决策，确保后续能回答：
- 这个结论是什么时候做出的？
- 为什么这样决定？
- 证据在哪里？
- 是否仍然有效？

## 当前决策记录规则

每条决策建议单独成文，文件名格式：
- `DEC-0001-xxx.md`
- `DEC-0002-xxx.md`

每条记录至少包含：
1. 决策标题
2. 日期
3. 状态（Proposed / Accepted / Superseded / Rejected）
4. 背景
5. 决策内容
6. 原因与证据
7. 影响范围
8. 后续动作

## 当前已确认正式决策

- `DEC-0001-fixed-etf-pool-for-factor-test.md`：固定 5 只 ETF 作为当前因子测试边界
- `DEC-0002-docs-as-canonical-doc-library.md`：使用 docs/ 作为统一文档主库
- `DEC-0003-staged-factor-validation-first.md`：因子验证采用分阶段推进，不做大规模混合暴力扫参
- `DEC-0004-stage1-factor-template-winners.md`：阶段 1 晋级模板为 F4、F6，F5 作为备选

## 当前已确认方向

1. 冻结 ETF 池为原 5 只，先做因子测试
2. 因子研究优先于新增 ETF 扩池
3. 文档库采用 docs/ 结构统一沉淀，不移动旧资料，只纳入索引

## 模板

统一模板见：
- `../70-templates/template-decision.md`
