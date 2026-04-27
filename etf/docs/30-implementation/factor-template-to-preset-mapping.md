# 阶段 1 因子模板到 preset 的映射

状态：Validated
更新日期：2026-04-15

## 1. 目的

本页说明阶段 1 的“因子模板”如何映射到可执行 preset。

## 2. 当前代码可配置能力

已确认以下参数可通过 `run_preset.py` 传入：
- `trigger_deviation`
- `signal_weight`
- `stop_loss_threshold`
- `lookback_period`
- `cooldown_days`
- `top_n`
- `transaction_cost`
- `factor_weights`
- `style_factors`
- `constraints.max_single_weight`
- `constraints.min_holding`

## 3. 本次新增的执行映射能力

本次已把因子权重和风格乘数从代码硬编码改为可配置：

### factor_weights
支持键：
- `momentum_20d`
- `momentum_60d`
- `momentum_strength`
- `volatility_reward`
- `r_squared`

### style_factors
支持覆盖各 style 对应乘数。

当前 ETF 池中实际用到的 style 包括：
- `a_share`
- `us_tech`
- `commodity`
- `gov_bond`
- `defensive`

## 4. 重要说明

### 4.1 阶段 1 为什么不用单一网格 preset
因为 `run_preset.py` 当前的参数网格更适合标量组合扫描，不适合直接对嵌套 dict 做模板切换。

因此阶段 1 采用：
- 6 个独立 preset
- 每个 preset 固定一套 `factor_weights`
- 统一把 `style_factors` 中性化为 1.0

这种方式更清晰，也更利于结果归档。

### 4.2 当前 style 名称存在口径差异
代码中历史 style 因子字典原本以：
- `small_cap`
- `growth`
- `tech`
等命名。

但当前 ETF 池实际 style 值是：
- `a_share`
- `us_tech`
- `commodity`
- `gov_bond`
- `defensive`

其中：
- `commodity`
- `gov_bond`
- `defensive` 原本就能命中风格乘数
- `a_share`
- `us_tech` 原本会默认落到 1.0

因此后续做 stage2 style 测试时，必须明确写清楚：
- 哪些 style 真正被调了
- 哪些 style 实际仍是 1.0

## 5. 六套模板映射

### F1：仅 20 日动量
- `momentum_20d = 400`
- 其他因子 = 0

### F2：20 日 + 60 日动量
- `momentum_20d = 400`
- `momentum_60d = 150`
- 其他因子 = 0

### F3：20 日 + 60 日 + 动量强度
- `momentum_20d = 400`
- `momentum_60d = 150`
- `momentum_strength = 200`
- 其他因子 = 0

### F4：20 日 + 60 日 + 波动率奖励
- `momentum_20d = 400`
- `momentum_60d = 150`
- `volatility_reward = 50`
- 其他因子 = 0

### F5：20 日 + 60 日 + 趋势稳定性 R²
- `momentum_20d = 400`
- `momentum_60d = 150`
- `r_squared = 30`
- 其他因子 = 0

### F6：全因子
- `momentum_20d = 400`
- `momentum_60d = 150`
- `momentum_strength = 200`
- `volatility_reward = 50`
- `r_squared = 30`

## 6. 后续建议

阶段 2 进入 style 测试时，建议：
1. 直接基于阶段 1 优胜 preset 复制出 on/off 两版
2. off：所有 style = 1.0
3. on：只对当前 ETF 池实际使用到的 style 显式给值
