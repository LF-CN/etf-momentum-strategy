# 原始策略可调参数清单

来源文件：`/opt/data/scripts/AkShare/策略执行/momentum_backtest.py`

说明：以下按“可调程度”分层整理：
1. 直接构造参数（`DailyMonitoringBLM.__init__`）
2. 运行时约束参数（`strategy.constraints`）
3. ETF 池配置参数（`self.etf_pool`）
4. 策略内部写死但可改的阈值/系数

---

## 一、直接构造参数（`__init__`）

### 1) initial_capital
- 含义：初始资金
- 类默认值：`52000`
- main 实跑值：`52000`

### 2) trigger_deviation
- 含义：触发调仓的偏离度阈值
- 类默认值：`0.15`
- main 实跑值：`0.20`

### 3) signal_weight
- 含义：强信号在综合触发中的权重
- 类默认值：`0.2`
- main 实跑值：`0.2`

### 4) stop_loss_threshold
- 含义：单资产止损阈值
- 类默认值：`-0.18`
- main 实跑值：`-0.18`

### 5) lookback_period
- 含义：动量回看周期
- 类默认值：`60`
- main 实跑值：`30`

### 6) cooldown_days
- 含义：调仓冷却期
- 类默认值：`10`
- main 实跑值：`20`

### 7) top_n
- 含义：最多持有 ETF 数量
- 类默认值：`3`
- main 实跑值：`3`

### 8) transaction_cost
- 含义：单边交易成本
- 类默认值：`0.0003`
- main 实跑值：`0.0002`

---

## 二、运行时约束参数（`strategy.constraints`）

### 9) max_single_weight
- 含义：单一资产最大权重
- 类默认值：`0.40`
- main 实跑值：`0.35`

### 10) min_holding
- 含义：最小持仓金额（元）
- 类默认值：`1000`
- main 实跑值：`1000`

### 11) max_stock_weight
- 含义：股票类资产总权重上限
- 代码支持：是
- 当前默认：未设置

### 12) min_stock_weight
- 含义：股票类资产总权重下限
- 代码支持：是
- 当前默认：未设置

### 13) max_sector_weight
- 含义：行业类 ETF 权重上限
- 代码支持：是
- 当前默认：未设置

---

## 三、ETF 池配置参数（`self.etf_pool`）

每个 ETF 的可配字段：

### 14) code
- 含义：ETF 代码
- 当前：`510500` `159941` `518880` `511010` `159928`

### 15) name
- 含义：ETF 名称

### 16) base_weight
- 含义：基础权重
- 当前：
  - `510500`: `0.25`
  - `159941`: `0.25`
  - `518880`: `0.20`
  - `511010`: `0.20`
  - `159928`: `0.10`

### 17) style
- 含义：风格标签
- 当前：
  - `510500`: `a_share`
  - `159941`: `us_tech`
  - `518880`: `commodity`
  - `511010`: `gov_bond`
  - `159928`: `defensive`

### 18) category
- 含义：分类标签（供约束逻辑使用）
- 代码支持：是
- 当前 ETF 池：未实际设置

---

## 四、策略内部写死但可修改的逻辑参数

### A. 动量评分权重

### 19) momentum_20d_weight
- 当前值：`400`
- 含义：20日动量权重

### 20) momentum_60d_weight
- 当前值：`150`
- 含义：60日动量权重

### 21) momentum_strength_weight
- 当前值：`200`
- 含义：近期动量相对历史均值的强度权重

### 22) vol_score_weight
- 当前值：`50`
- 含义：低波动奖励权重

### 23) r_squared_weight
- 当前值：`30`
- 含义：趋势稳定性权重

### B. 波动率评分参数

### 24) volatility_baseline
- 当前值：`0.03`
- 含义：波动率评分基准线

### C. 动量排名分段阈值

### 25) high_rank_threshold_1
- 当前值：`0.75`
- 含义：前25%大幅加配起点

### 26) high_rank_threshold_2
- 当前值：`0.60`
- 含义：前40%小幅加配起点

### 27) low_rank_threshold_1
- 当前值：`0.25`
- 含义：后25%大幅减配起点

### 28) low_rank_threshold_2
- 当前值：`0.40`
- 含义：后40%小幅减配起点

### D. 权重调整幅度

### 29) top_rank_max_adjustment
- 当前值：`+0.30`
- 含义：高排名资产最多加配30%

### 30) mid_high_rank_max_adjustment
- 当前值：`+0.15`
- 含义：中高排名资产最多加配15%

### 31) bottom_rank_max_adjustment
- 当前值：`-0.20`
- 含义：低排名资产最多减配20%

### 32) mid_low_rank_max_adjustment
- 当前值：`-0.10`
- 含义：中低排名资产最多减配10%

### 33) min_target_weight
- 当前值：`0.02`
- 含义：调整后单资产最低目标权重 2%

### E. 强信号判定参数

### 34) strong_signal_consecutive_up_days
- 当前值：`10`
- 含义：连续上涨多少天算强上涨信号

### 35) strong_signal_consecutive_down_days
- 当前值：`10`
- 含义：连续下跌多少天算强下跌信号

### 36) strong_signal_5d_up
- 当前值：`0.08`
- 含义：5日涨超8%视为强上涨

### 37) strong_signal_10d_up
- 当前值：`0.12`
- 含义：10日涨超12%视为强上涨

### 38) strong_signal_5d_down
- 当前值：`-0.08`
- 含义：5日跌超8%视为强下跌

### 39) strong_signal_10d_down
- 当前值：`-0.12`
- 含义：10日跌超12%视为强下跌

### F. 调仓触发逻辑参数

### 40) trigger_score_threshold
- 当前值：`0.5`
- 含义：综合得分超过该值触发调仓

### 41) severe_deviation_multiplier
- 当前值：`2`
- 含义：严重偏离阈值 = `trigger_deviation × 2`

### G. 交易执行参数

### 42) min_trade_diff
- 当前值：`500`
- 含义：目标市值差异超过500元才执行交易

### 43) lot_size
- 当前值：`100`
- 含义：按100份一手交易

---

## 五、风格修正系数（style factor）

### 44) small_cap_factor
- 当前值：`1.25`

### 45) growth_factor
- 当前值：`1.20`

### 46) mid_cap_factor
- 当前值：`1.10`

### 47) large_cap_factor
- 当前值：`1.00`

### 48) tech_factor
- 当前值：`1.15`

### 49) cyclical_factor
- 当前值：`1.10`

### 50) defensive_factor
- 当前值：`0.70`

### 51) gov_bond_factor
- 当前值：`0.60`

### 52) convertible_factor
- 当前值：`0.85`

### 53) commodity_factor
- 当前值：`0.95`

---

## 六、当前脚本 main 实际使用的一套参数

`if __name__ == "__main__":` 中实际跑的是：

- `initial_capital = 52000`
- `trigger_deviation = 0.20`
- `signal_weight = 0.2`
- `stop_loss_threshold = -0.18`
- `lookback_period = 30`
- `cooldown_days = 20`
- `top_n = 3`
- `transaction_cost = 0.0002`
- `max_single_weight = 0.35`
- `min_holding = 1000`

---

## 七、最值得优化的主参数

如果要做参数优化，优先关注：

1. `trigger_deviation`
2. `signal_weight`
3. `stop_loss_threshold`
4. `lookback_period`
5. `cooldown_days`
6. `top_n`
7. `transaction_cost`
8. `max_single_weight`
9. `base_weight`
10. ETF 池标的组成
