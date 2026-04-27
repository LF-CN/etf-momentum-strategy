# 参数优化验证框架说明

时间：2026-04-15

本次在 `param_optimization.py` 中新增了“防过拟合验证层”，目标不是只找全样本最优参数，而是判断参数是否具有样本外稳定性。

## 新增能力

### 1. 全样本网格优化
函数：`evaluate_param_grid()`

用途：
- 在给定参数网格内跑完整批量回测
- 返回按夏普排序的排名结果

特点：
- 复用共享价格数据
- 返回轻量摘要结果
- 适合做初筛

### 2. 样本内 / 样本外验证
函数：`optimize_train_then_evaluate_test()`

流程：
1. 用训练集做参数优化
2. 选出训练集最优参数
3. 固定该参数到测试集评估
4. 对比样本外表现

意义：
- 避免只看全样本最优
- 判断参数是否“过拟合训练期”

默认切分：
- `train_ratio=0.7`

辅助函数：
- `split_train_test_dates()`

### 3. Walk-forward 滚动验证
函数：`walk_forward_validation()`

流程：
1. 生成多个滚动窗口
2. 每个窗口内：
   - 训练段选参数
   - 测试段验证该参数
3. 汇总各窗口样本外表现
4. 统计“哪些参数组合反复出现”

辅助函数：
- `generate_walk_forward_windows()`

默认建议：
- 训练期：3年
- 测试期：1年
- 步长：半年

意义：
- 比单次 train/test 切分更稳
- 能观察参数在不同时期是否一致有效

## 新增输出文件

### 1. 全样本优化结果
`/opt/data/scripts/etf/param_optimization_results.json`

### 2. 验证结果
`/opt/data/scripts/etf/validation_results.json`

### 3. 本次窄范围演示结果
`/opt/data/scripts/etf/validation_demo_results.json`

## 主要新增函数

- `build_param_combinations(param_grid=None)`
- `rank_results(results, sort_by='sharpe_ratio')`
- `evaluate_param_grid(shared_prices, start_date, end_date, param_grid=None, progress=False)`
- `split_train_test_dates(shared_prices, train_ratio=0.7)`
- `optimize_train_then_evaluate_test(shared_prices, param_grid=None, train_ratio=0.7, top_k=10)`
- `generate_walk_forward_windows(shared_prices, train_days=252*3, test_days=252, step_days=252)`
- `walk_forward_validation(shared_prices, param_grid=None, train_days=252*3, test_days=252, step_days=252, top_k=5)`

## 已验证

测试文件：
`/opt/data/scripts/etf/tests/test_backtest_engine.py`

当前覆盖：
1. 共享价格数据复用
2. 多次回测状态重置
3. 参数优化接受 shared_prices
4. train/test 区间切分正确
5. train→test 验证结果结构正确
6. walk-forward 窗口生成正确
7. walk-forward 汇总结构正确

结果：
- `7 passed`

## 如何使用

### 方式1：直接运行主脚本
```bash
cd /opt/data/scripts/etf
uv run --index-url https://pypi.tuna.tsinghua.edu.cn/simple \
  --with akshare --with pandas --with numpy --with matplotlib --with seaborn \
  python3 param_optimization.py
```

它会依次输出：
1. 全样本优化
2. 样本内 / 样本外验证
3. walk-forward 汇总

### 方式2：在 Python 中调用
```python
import param_optimization as po
shared = po.load_shared_prices(po.BACKTEST_START, po.BACKTEST_END)

validation = po.optimize_train_then_evaluate_test(shared, train_ratio=0.7)
walk = po.walk_forward_validation(shared, train_days=252*3, test_days=252, step_days=126)
```

## 下一步建议

### 建议 1：先做“窄范围验证”
不要一开始就扩大到很大的参数网格。
先围绕当前较优参数附近验证，例如：
- trigger_deviation: 0.15 / 0.20 / 0.25
- lookback_period: 30 / 45
- cooldown_days: 10 / 20
- top_n: 3

原因：
- 成本低
- 更容易看出稳定性
- 适合先判断原始策略是否已经足够稳

### 建议 2：验证排序指标不要只看夏普
后面可扩展成多目标排序：
- 夏普
- 年化
- 最大回撤
- 卡玛比率
- 调仓次数惩罚

### 建议 3：加入稳定性筛选规则
后面可以增加：
- 样本外夏普下限
- 样本外最大回撤上限
- walk-forward 平均夏普下限
- 参数出现频率阈值

这样选出来的参数更适合实盘。
