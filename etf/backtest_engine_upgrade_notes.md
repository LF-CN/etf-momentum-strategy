# 回测引擎优化说明

时间：2026-04-15

## 目标

在不改变原始策略逻辑的前提下，优化回测引擎，使其更适合：

1. 参数优化（批量回测）
2. 回测复核（同一组参数反复验证）
3. 与实盘脚本保持一致的核心逻辑

## 发现的问题

### 1. 参数优化重复读取历史数据
`param_optimization.py` 中每个参数组合都会新建策略并调用 `backtest()`，而 `backtest()` 默认会再次 `fetch_data()`。

结果：
- 重复读取 CSV / 检查覆盖范围
- 批量优化时存在不必要的 I/O 开销

### 2. 回测对象存在运行态污染风险
`DailyMonitoringBLM.backtest()` 开始前没有显式重置：
- `rebalance_history`
- `signals_log`

这意味着：
- 如果同一个 strategy 实例被重复用于多次回测
- 会发生历史状态串联
- 不利于共享数据后的批量回测与重复验证

### 3. 参数优化只要摘要指标，却返回完整明细
原逻辑每次回测都会返回：
- `trades`
- `nav_history`
- `rebalance_history`
- `final_positions`

但参数优化只需要：
- 年化收益
- 最大回撤
- 夏普
- 调仓次数
- 数据区间

结果：
- 额外对象构造与内存占用
- 批量优化效率不高

## 已完成的改造

## A. 回测引擎支持注入共享价格数据
文件：`/opt/data/scripts/AkShare/策略执行/momentum_backtest.py`

新增：
- `prices` 参数
- `_slice_prices_for_backtest()`

现在可以：
- 先一次性加载历史价格
- 多组参数复用同一份数据
- 避免每轮参数组合都重新取数

新接口：
```python
backtest(start_date, end_date, verbose=True, prices=None, return_details=True, record_signals=True)
```

## B. 每次回测前重置运行态
新增：
- `_reset_run_state()`

在 `backtest()` 开头执行：
- 清空 `rebalance_history`
- 清空 `signals_log`

作用：
- 同一个 strategy 对象可以安全重复回测
- 为后续做并行/复用优化打基础

## C. 支持轻量返回模式
新增参数：
- `return_details=False`

关闭后不再把以下大对象放入结果：
- `trades`
- `nav_history`
- `rebalance_history`
- `final_positions`

适用场景：
- 参数优化
- 批量扫描
- 快速摘要比较

默认仍然是 `True`，兼容原来详细回测用途。

## D. 支持关闭逐日信号日志
新增参数：
- `record_signals=False`

并在 `calculate_BLM_weights()` 中受控记录 `signals_log`。

适用场景：
- 参数优化
- 大批量回测

## E. 参数优化脚本改为共享数据模式
文件：`/opt/data/scripts/etf/param_optimization.py`

新增：
- `build_strategy(params)`
- `load_shared_prices(start_date, end_date)`

改造后流程：
1. 启动时一次性加载共享价格数据
2. 每组参数只做策略计算
3. 不重复读取历史数据
4. 使用 `return_details=False, record_signals=False`

## 验证结果

### 1. 自动化测试
测试文件：
`/opt/data/scripts/etf/tests/test_backtest_engine.py`

已通过 3 个测试：

1. 传入共享价格时，不会调用 `fetch_data()`
2. 同一 strategy 多次回测不会串状态
3. `param_optimization.run_backtest()` 可直接复用共享价格

执行命令：
```bash
cd /opt/data/scripts/etf && uv run --index-url https://pypi.tuna.tsinghua.edu.cn/simple --with pytest --with pandas --with numpy --with akshare --with matplotlib --with seaborn pytest -q tests/test_backtest_engine.py
```

结果：`3 passed`

### 2. 真实历史数据小样本验证
验证了：
- `load_shared_prices()` 能正常加载 2016-01-04 ~ 2026-04-14 的共享价格
- `run_backtest(..., shared_prices=shared)` 能正常产出摘要指标
- 返回结果不含大对象（适合参数优化）

示例结果：
- 参数 `(0.20, 30, 20, 3)`
  - 年化 15.48%
  - 最大回撤 -16.47%
  - 夏普 1.022
  - 调仓 164 次
- 参数 `(0.15, 45, 10, 3)`
  - 年化 11.02%
  - 最大回撤 -20.66%
  - 夏普 0.612
  - 调仓 272 次

### 3. 兼容性验证
默认 `backtest()` 仍返回：
- `trades`
- `nav_history`
- `rebalance_history`

说明原有“详细回测”用法未被破坏。

## 当前收益

这次改造后，参数优化具备以下特性：

1. 同一批历史数据只加载一次
2. 多轮回测不串状态
3. 批量优化只返回摘要，减轻对象构造与结果搬运
4. 原有详细回测、报告输出能力仍保留

## 下一步建议

如果继续优化，我建议按优先级做：

### 优先级 P1
1. 把 `PARAM_GRID` 扩展成可配置文件
2. 增加多目标排序（夏普 / 年化 / 回撤 / 卡玛）
3. 输出 top-N 参数对比表和稳定性报告

### 优先级 P2
4. 增加 walk-forward / 滚动窗口验证
5. 增加样本内/样本外拆分，避免过拟合
6. 记录每轮优化耗时，输出性能统计

### 优先级 P3
7. 支持并行参数搜索
8. 支持随机搜索 / 贝叶斯优化
9. 将回测结果落库，便于历史比较
