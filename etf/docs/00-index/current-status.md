# 当前状态

状态：In Progress
更新日期：2026-04-15

## 当前主线

固定原 5 只 ETF，不新增标的。阶段 1 因子模板对比已完成，当前主线切换为：对 F4 / F6 / F5 进入阶段 2 的 style on / off 验证。

## 当前已确认事项

1. ETF 池暂时冻结为 5 只，不引入新 ETF
2. 阶段 1 已完成 6 套因子模板回测
3. 阶段 1 晋级模板已确认：F4、F6，F5 作为备选
4. 文档库已建立并开始承接实验结果与正式决策

## 当前关键进展

1. 回测引擎已支持 `factor_weights` 与 `style_factors` 配置
2. 阶段 1 六套 preset 已全部落地并完成回测
3. 阶段 1 结果摘要页已完成
4. 已新增 DEC-0004 记录阶段 1 晋级结论

## 当前关键文件

- 回测引擎：`../windows_backtest_package/core/momentum_backtest.py`
- 预设入口：`../windows_backtest_package/core/run_preset.py`
- 阶段 1 结果摘要：`../20-research-and-backtest/results/stage1-factor-comparison-summary.md`
- 阶段 1 实验矩阵：`../20-research-and-backtest/experiment-matrix.md`
- 阶段 1 晋级决策：`../50-decisions/DEC-0004-stage1-factor-template-winners.md`

## 当前已知约束

1. 历史 CSV 不重建、不随意删除
2. 回测逻辑与实盘逻辑必须保持可对照
3. 参数比较必须尽量使用统一数据区间
4. 当前重点是“风格偏置贡献识别”，不是“组合扩张”

## 当前阻塞点

无硬阻塞。
当前下一步主要是把阶段 2 的 style on / off 口径定义清楚，尤其要明确哪些 style 键在当前 ETF 池中真正生效。

## 建议下一步

1. 为 F4 / F6 / F5 生成阶段 2 的 style on / off preset
2. 明确 style on 版本只覆盖当前 ETF 池实际使用到的 style
3. 运行阶段 2 回测
4. 更新阶段 2 结果摘要页
5. 根据结果决定是否淘汰 F5，并进入 top_n 微调阶段

## 更新规则

此页用于记录“当前项目现场”。每次阶段切换时应更新：
- 当前主线
- 关键进展
- 阻塞点
- 下一步
