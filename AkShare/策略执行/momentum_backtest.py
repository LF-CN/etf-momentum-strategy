# ================================
# 每日监测+触发调仓BLM策略（10只ETF版）
# 适合：稳健型投资者，5万资金，A股ETF
# ================================

import pandas as pd
import numpy as np
import akshare as ak
from datetime import datetime, timedelta
from pathlib import Path
import warnings
import matplotlib.pyplot as plt
import seaborn as sns
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

class DailyMonitoringBLM:
    """
    每日监测+触发调仓的BLM策略（10只ETF）
    
    核心特点：
    1. 每日计算目标权重
    2. 偏离度>5%或强信号时触发调仓
    3. 多维度动量评分
    4. 严格风控约束
    """
    
    def __init__(self, initial_capital=52000, 
                 trigger_deviation=0.15,
                 signal_weight=0.2,
                 stop_loss_threshold=-0.18,
                 lookback_period=60,
                 cooldown_days=10,
                 top_n=3,
                 transaction_cost=0.0003):
        
        self.initial_capital = initial_capital
        self.trigger_deviation = trigger_deviation
        self.signal_weight = signal_weight
        self.stop_loss_threshold = stop_loss_threshold
        self.lookback_period = lookback_period
        self.cooldown_days = cooldown_days
        self.top_n = top_n
        self.transaction_cost = transaction_cost
        
        self.etf_pool = {
            '510500': {'name': '中证500ETF', 'base_weight': 0.25, 'style': 'a_share'},
            '159941': {'name': '纳指ETF', 'base_weight': 0.25, 'style': 'us_tech'},
            '518880': {'name': '黄金ETF', 'base_weight': 0.20, 'style': 'commodity'},
            '511010': {'name': '国债ETF', 'base_weight': 0.20, 'style': 'gov_bond'},
            '159928': {'name': '消费ETF', 'base_weight': 0.10, 'style': 'defensive'},
        }
        
        self.constraints = {
            'max_single_weight': 0.40,
            'min_holding': 1000  # 最小持仓金额1000元
        }
        
        # 记录变量
        self.rebalance_history = []
        self.signals_log = []

    def _load_csv_data(self, csv_path):
        """读取单个ETF CSV数据并标准化字段"""
        df = pd.read_csv(csv_path, encoding='utf-8')
        df.columns = [str(c).lower() for c in df.columns]

        required_columns = {'date', 'close'}
        missing_columns = required_columns - set(df.columns)
        if missing_columns:
            raise ValueError(f"缺少必要列: {', '.join(sorted(missing_columns))}")

        df['date'] = pd.to_datetime(df['date'])
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df = df.dropna(subset=['date', 'close'])
        df = df.sort_values('date').drop_duplicates(subset=['date'], keep='last')
        return df

    def _ensure_history_coverage(self, code, csv_dir, start_date, end_date):
        """确保本地CSV至少覆盖所需回测区间"""
        csv_path = csv_dir / f'{code}_kline.csv'
        requested_start = pd.to_datetime(start_date)
        requested_end = pd.to_datetime(end_date)

        need_refresh = not csv_path.exists()
        existing_df = None

        if not need_refresh:
            try:
                existing_df = self._load_csv_data(csv_path)
                if existing_df.empty:
                    need_refresh = True
                else:
                    existing_start = existing_df['date'].min()
                    existing_end = existing_df['date'].max()
                    if existing_start > requested_start or existing_end < requested_end:
                        need_refresh = True
                        print(
                            f"  CSV {self.etf_pool[code]['name']} ({code}): "
                            f"覆盖 {existing_start.strftime('%Y-%m-%d')} ~ {existing_end.strftime('%Y-%m-%d')}，"
                            f"不足以覆盖 {start_date} ~ {end_date}，补齐全量历史..."
                        )
                    else:
                        print(
                            f"  CSV {self.etf_pool[code]['name']} ({code}): "
                            f"覆盖完整 {existing_start.strftime('%Y-%m-%d')} ~ {existing_end.strftime('%Y-%m-%d')}"
                        )
            except Exception as e:
                need_refresh = True
                print(f"  CSV {self.etf_pool[code]['name']} ({code}): 读取失败 - {str(e)[:60]}，重新拉取全量数据")

        if need_refresh:
            # 优先使用稳定返回全量历史的新浪接口，失败再试东方财富
            fetched_df = pd.DataFrame()
            sina_sym = self._to_sina_symbol(code)

            # 策略：Sina 稳定返回 3000+ 行；Eastmoney 在此环境会报 ConnectionError
            try:
                fetched_df = ak.fund_etf_hist_sina(symbol=sina_sym)
            except Exception as e:
                print(f"    Sina 获取失败: {type(e).__name__}: {str(e)[:60]}")

            if fetched_df is None or fetched_df.empty or len(fetched_df) < 1000:
                try:
                    fetched_df = ak.fund_etf_hist_em(
                        symbol=code,
                        period='daily',
                        start_date='19700101',
                        end_date='20500101',
                        adjust=''
                    )
                except Exception as e:
                    print(f"    Eastmoney 获取失败: {type(e).__name__}: {str(e)[:60]}")

            if fetched_df is None or fetched_df.empty:
                raise ValueError(f'AkShare 未返回 {code} 的历史数据')

            fetched_df.columns = [str(c).lower() for c in fetched_df.columns]
            fetched_df['date'] = pd.to_datetime(fetched_df['date'])
            fetched_df['close'] = pd.to_numeric(fetched_df['close'], errors='coerce')
            fetched_df = fetched_df.dropna(subset=['date', 'close'])
            fetched_df = fetched_df.sort_values('date').drop_duplicates(subset=['date'], keep='last')
            fetched_df.to_csv(csv_path, index=False, encoding='utf-8')

        df = self._load_csv_data(csv_path)
        covered_df = df[(df['date'] >= requested_start) & (df['date'] <= requested_end)]
        return df, covered_df

    def _buy_total_cost(self, trade_value):
        """买入总成本（含手续费）"""
        return trade_value * (1 + self.transaction_cost)

    def _to_sina_symbol(self, code):
        """将ETF代码转换为新浪格式代码"""
        return f"sh{code}" if str(code).startswith('5') else f"sz{code}"

    def _sell_net_proceeds(self, trade_value):
        """卖出净回款（扣除手续费）"""
        return trade_value * (1 - self.transaction_cost)
        
    def fetch_data(self, start_date, end_date):
        """
        获取ETF历史数据（支持增量更新）
        - 优先从CSV读取
        - CSV存在时自动增量更新最新数据
        - CSV不存在则从akshare获取
        
        Args:
            start_date: 开始日期 'YYYY-MM-DD'
            end_date: 结束日期 'YYYY-MM-DD'
        
        Returns:
            DataFrame: 各ETF的收盘价数据
        """
        print(f"正在获取{len(self.etf_pool)}只ETF的历史数据...")
        print("-" * 60)
        
        price_data = {}
        success_count = 0
        csv_dir = Path(__file__).parent.parent / 'etf_data'
        csv_dir.mkdir(parents=True, exist_ok=True)

        for code in self.etf_pool.keys():
            try:
                full_df, range_df = self._ensure_history_coverage(code, csv_dir, start_date, end_date)

                if range_df.empty:
                    available_start = full_df['date'].min().strftime('%Y-%m-%d') if not full_df.empty else '无'
                    available_end = full_df['date'].max().strftime('%Y-%m-%d') if not full_df.empty else '无'
                    print(
                        f"  CSV {self.etf_pool[code]['name']} ({code}): "
                        f"请求区间内仍无数据，可用范围 {available_start} ~ {available_end}"
                    )
                    continue

                price_data[code] = range_df.set_index('date')['close']
                print(
                    f"    最终: {len(range_df)}条数据，"
                    f"覆盖 {range_df['date'].min().strftime('%Y-%m-%d')} ~ {range_df['date'].max().strftime('%Y-%m-%d')}"
                )
                success_count += 1
            except Exception as e:
                print(f"  X  {self.etf_pool[code]['name']} ({code}): {str(e)[:60]}...")
        
        print(f"\n成功获取{success_count}/{len(self.etf_pool)}只ETF数据")
        print("-" * 60)
        
        if success_count < len(self.etf_pool) * 0.8:
            print("警告：部分ETF数据获取失败，可能影响回测结果")
        
        return pd.DataFrame(price_data)
    
    def calculate_momentum_score(self, prices, date):
        """
        计算动量得分（多因子综合）
        
        考虑因素：
        1. 短期动量（20日）
        2. 长期动量（60日）
        3. 动量强度（近期vs历史）
        4. 波动率（低波动奖励）
        5. 趋势稳定性
        
        Args:
            prices: 价格DataFrame
            date: 计算日期
        
        Returns:
            Series: 各ETF的动量得分（0-100）
        """
        end_idx = prices.index.get_loc(date)
        start_idx = max(0, end_idx - self.lookback_period)
        period_prices = prices.iloc[start_idx:end_idx+1]
        
        momentum_scores = {}
        
        for code in prices.columns:
            try:
                returns = period_prices[code].pct_change().dropna()
                
                if len(returns) > 5:
                    # 1. 短期动量（20日收益率）
                    if len(period_prices[code]) >= 20:
                        momentum_20d = (period_prices[code].iloc[-1] / period_prices[code].iloc[-20] - 1)
                    else:
                        momentum_20d = (period_prices[code].iloc[-1] / period_prices[code].iloc[0] - 1)
                    
                    # 2. 长期动量（60日收益率）
                    if len(period_prices[code]) >= 60:
                        momentum_60d = (period_prices[code].iloc[-1] / period_prices[code].iloc[-60] - 1)
                    else:
                        momentum_60d = (period_prices[code].iloc[-1] / period_prices[code].iloc[0] - 1)
                    
                    # 3. 动量强度（近期动量vs历史平均）
                    if len(returns) > 10:
                        hist_mean = returns.mean()
                        recent_mom = momentum_20d / 20  # 日化
                        momentum_strength = (recent_mom - hist_mean) if hist_mean != 0 else 0
                    else:
                        momentum_strength = 0
                    
                    # 4. 波动率惩罚（波动率越低得分越高）
                    volatility = returns.std()
                    if volatility > 0:
                        vol_score = (0.03 - volatility) / 0.03  # 以3%为基准
                        vol_score = np.clip(vol_score, 0, 1)
                    else:
                        vol_score = 0.5
                    
                    # 5. 趋势稳定性
                    if len(period_prices[code]) > 10:
                        # 计算R²（回归拟合度）
                        x = np.arange(len(period_prices[code]))
                        y = period_prices[code].values
                        slope, intercept = np.polyfit(x, y, 1)
                        y_pred = slope * x + intercept
                        ss_res = np.sum((y - y_pred) ** 2)
                        ss_tot = np.sum((y - y.mean()) ** 2)
                        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
                    else:
                        r_squared = 0
                    
                    # 综合得分计算
                    base_score = (
                        momentum_20d * 400 +      # 短期动量权重高
                        momentum_60d * 150 +      # 长期动量权重适中
                        momentum_strength * 200 +  # 动量强度
                        vol_score * 50 +          # 波动率奖励
                        r_squared * 30            # 趋势稳定性
                    )
                    
                    # 根据ETF风格调整权重
                    etf_style = self.etf_pool[code]['style']
                    style_factor = {
                        'small_cap': 1.25,      # 小盘股给予更高动量权重
                        'growth': 1.20,         # 成长股
                        'mid_cap': 1.10,
                        'large_cap': 1.00,
                        'tech': 1.15,           # 科技股
                        'cyclical': 1.10,       # 周期股
                        'defensive': 0.70,      # 防御股降低动量权重
                        'gov_bond': 0.60,       # 国债
                        'convertible': 0.85,    # 可转债
                        'commodity': 0.95       # 商品
                    }.get(etf_style, 1.0)
                    
                    momentum_score = base_score * style_factor
                    
                    # 限制在0-100区间
                    momentum_scores[code] = np.clip(momentum_score, 0, 100)
                    
                else:
                    momentum_scores[code] = 50  # 数据不足给中性分
                    
            except Exception as e:
                momentum_scores[code] = 50
                print(f"计算{code}动量得分时出错: {e}")
        
        return pd.Series(momentum_scores)
    
    def calculate_BLM_weights(self, prices, date):
        """
        使用简化版BLM模型计算目标权重
        
       逻辑：
        1. 基础权重 + 动量调整
        2. 多层约束优化
        3. 满足各类风险限制
        
        Args:
            prices: 价格DataFrame
            date: 计算日期
        
        Returns:
            Series: 各ETF的目标权重
        """
        # 计算动量得分
        momentum_scores = self.calculate_momentum_score(prices, date)
        
        # 获取当前日期有有效价格的ETF列表
        current_prices = prices.loc[date]
        valid_codes = [code for code in momentum_scores.index 
                      if pd.notna(current_prices.get(code)) and current_prices.get(code, 0) > 0]
        
        if len(valid_codes) == 0:
            return pd.Series(0.0, index=self.etf_pool.keys())
        
        momentum_scores = momentum_scores[valid_codes]
        momentum_rank = momentum_scores.rank(pct=True)
        
        # 记录信号日志（只记录有效的ETF）
        self.signals_log.append({
            'date': date,
            'momentum_scores': {k: v for k, v in momentum_scores.to_dict().items() if pd.notna(v)},
            'momentum_ranks': {k: v for k, v in momentum_rank.to_dict().items() if pd.notna(v)}
        })
        
        # 初始化目标权重
        target_weights = {}
        
        # 第一步：基于动量排名调整基础权重
        for code in self.etf_pool.keys():
            base_weight = self.etf_pool[code]['base_weight']
            
            # 如果ETF没有数据，跳过或给默认权重
            if code not in momentum_rank:
                target_weights[code] = 0
                continue
                
            rank = momentum_rank[code]
            
            # 跳过无效rank
            if pd.isna(rank):
                target_weights[code] = 0
                continue
            
            # 动量调整规则
            if rank > 0.75:  # 前25%：大幅加配
                adjustment_factor = (rank - 0.75) / 0.25
                adjustment = adjustment_factor * 0.30  # 最多加30%
            elif rank > 0.60:  # 前25%-40%：小幅加配
                adjustment_factor = (rank - 0.60) / 0.15
                adjustment = adjustment_factor * 0.15
            elif rank < 0.25:  # 后25%：大幅减配
                adjustment_factor = (0.25 - rank) / 0.25
                adjustment = -adjustment_factor * 0.20  # 最多减20%
            elif rank < 0.40:  # 后25%-40%：小幅减配
                adjustment_factor = (0.40 - rank) / 0.15
                adjustment = -adjustment_factor * 0.10
            else:
                adjustment = 0  # 中间40%不调整
            
            # 确保调整后权重不低于2%
            target_weights[code] = max(0.02, base_weight + adjustment)
        
        # 检查是否有正的动量（避免在所有ETF都下跌时强行持仓）
        momentum_array = momentum_scores.values
        if hasattr(momentum_array, '__iter__'):
            positive_momentum_count = sum(1 for v in momentum_array if v > 0)
        else:
            positive_momentum_count = 1 if momentum_array > 0 else 0
        
        # 如果没有正动量的ETF，选择空仓
        if positive_momentum_count == 0:
            # 所有权重设为0（空仓）
            target_weights = pd.Series({code: 0 for code in self.etf_pool.keys()})
            return target_weights
        
        # 转换为Series
        target_weights = pd.Series(target_weights)
        
        # 只保留动量排名前top_n的ETF
        if self.top_n < len(target_weights):
            # 按动量得分排序，取前top_n
            top_codes = momentum_scores.nlargest(self.top_n).index
            # 其他ETF权重设为0
            target_weights = target_weights.reindex(target_weights.index, fill_value=0)
            target_weights[~target_weights.index.isin(top_codes)] = 0
        
        # 归一化（确保总和为1）
        target_weights = target_weights / target_weights.sum()
        
        # 约束优化（多层约束）
        target_weights = self._apply_constraints(target_weights, prices, date)
        
        # 重新归一化
        target_weights = target_weights / target_weights.sum()
        
        return target_weights
    
    def _apply_constraints(self, weights, prices, date):
        """
        应用多层约束
        
        Args:
            weights: 待约束的权重Series
            prices: 价格数据
            date: 当前日期
        
        Returns:
            Series: 约束后的权重
        """
        weights = weights.copy()
        c = self.constraints
        
        # 归一化
        weights = weights / weights.sum()
        
        # 约束1: 单一资产上限
        if 'max_single_weight' in c:
            weights = weights.clip(upper=c['max_single_weight'])
            weights = weights / weights.sum()
        
        # 约束2: 股票类权重范围
        if 'max_stock_weight' in c or 'min_stock_weight' in c:
            stock_codes = [co for co, info in self.etf_pool.items() if info.get('category') == 'stock']
            sector_codes = [co for co, info in self.etf_pool.items() if info.get('category') == 'sector']
            equity_codes = stock_codes + sector_codes
            
            equity_weight = weights[equity_codes].sum() if equity_codes else 0
            
            if 'max_stock_weight' in c and equity_weight > c['max_stock_weight']:
                weights[equity_codes] = weights[equity_codes] * (c['max_stock_weight'] / equity_weight)
                weights = weights / weights.sum()
            
            if 'min_stock_weight' in c and equity_weight < c['min_stock_weight']:
                non_equity_codes = [co for co in weights.index if co not in equity_codes]
                deficit = c['min_stock_weight'] - equity_weight
                if len(non_equity_codes) > 0:
                    weights[non_equity_codes] *= (1 - c['min_stock_weight']) / weights[non_equity_codes].sum()
                weights[equity_codes] += deficit
                weights = weights / weights.sum()
        
        # 约束3: 行业上限
        if 'max_sector_weight' in c:
            sector_codes = [co for co, info in self.etf_pool.items() if info.get('category') == 'sector']
            for code in sector_codes:
                if weights.get(code, 0) > c['max_sector_weight']:
                    excess = weights[code] - c['max_sector_weight']
                    weights[code] = c['max_sector_weight']
                    other_codes = [co for co in weights.index if co != code]
                    if other_codes:
                        weights[other_codes] += weights[other_codes] * (excess / weights[other_codes].sum())
                    weights = weights / weights.sum()
        
        return weights
    
    def calculate_deviation(self, current_weights, target_weights):
        """
        计算权重偏离度
        
        Args:
            current_weights: 当前持仓权重
            target_weights: 目标权重
        
        Returns:
            Series: 各ETF的偏离度
        """
        # 确保索引一致
        all_codes = sorted(list(set(current_weights.index) | set(target_weights.index)))
        
        current_aligned = current_weights.reindex(all_codes, fill_value=0)
        target_aligned = target_weights.reindex(all_codes, fill_value=0)
        
        return (current_aligned - target_aligned).abs()
    
    def check_strong_signal(self, prices, date):
        """
        检查强信号（趋势翻转/加速/反转）
        
        检测内容：
        1. 连续上涨/下跌天数
        2. 单日大幅波动
        3. 突破/跌破关键技术位
        
        Args:
            prices: 价格DataFrame
            date: 检查日期
        
        Returns:
            dict: {'signal': True/False, 'detail': {...}}
        """
        try:
            end_idx = prices.index.get_loc(date)
        except:
            return {'signal': False, 'detail': {}}
        
        detail = {}
        
        for code in prices.columns:
            try:
                recent_prices = prices[code].iloc[max(0, end_idx-14):end_idx+1]
                
                if len(recent_prices) >= 5:
                    # 计算1日、3日、5日、10日收益率
                    periods = [1, 3, 5, 10]
                    period_returns = {}
                    for p in periods:
                        if len(recent_prices) >= p:
                            period_returns[f'{p}d'] = (recent_prices.iloc[-1] / recent_prices.iloc[-p] - 1)
                    
                    # 检测连续涨跌
                    returns = recent_prices.pct_change().dropna()
                    consecutive_up = 0
                    consecutive_down = 0
                    
                    for r in reversed(returns):
                        if r > 0:
                            consecutive_up += 1
                            consecutive_down = 0
                        elif r < 0:
                            consecutive_down += 1
                            consecutive_up = 0
                        else:
                            break
                    
                    # 强信号判断
                    strong_up = (
                        consecutive_up >= 10 or                 # 连续10日上涨
                        period_returns.get('5d', 0) > 0.08 or    # 5日涨超8%
                        period_returns.get('10d', 0) > 0.12      # 10日涨超12%
                    )
                    
                    strong_down = (
                        consecutive_down >= 10 or               # 连续10日下跌
                        period_returns.get('5d', 0) < -0.08 or  # 5日跌超8%
                        period_returns.get('10d', 0) < -0.12    # 10日跌超12%
                    )
                    
                    detail[code] = {
                        'consecutive_up': consecutive_up,
                        'consecutive_down': consecutive_down,
                        'period_returns': period_returns,
                        'strong_up': strong_up,
                        'strong_down': strong_down
                    }
            except:
                detail[code] = {
                    'consecutive_up': 0, 'consecutive_down': 0,
                    'period_returns': {}, 'strong_up': False, 'strong_down': False
                }
        
        # 整体强信号：任一资产出现强信号
        strong_signal = any([
            d.get('strong_up', False) or d.get('strong_down', False)
            for d in detail.values()
        ])
        
        return {
            'signal': strong_signal,
            'detail': detail
        }
    
    def check_stop_loss(self, prices, current_positions, current_value, date, entry_prices):
        """
        检查止损条件
        
        Args:
            prices: 当前价格Series
            current_positions: 当前持仓（股数）
            current_value: 当前组合价值
            date: 检查日期
            entry_prices: 各资产入场价
        
        Returns:
            dict: {'trigger': True/False, 'assets': [...]}
        """
        stop_loss_assets = []
        
        for code, shares in current_positions.items():
            if shares > 0 and code in entry_prices and code in prices:
                entry_price = entry_prices[code]
                current_price = prices[code]
                
                if entry_price > 0:
                    asset_return = (current_price - entry_price) / entry_price
                    
                    # 触发严格止损
                    if asset_return < self.stop_loss_threshold:
                        stop_loss_assets.append({
                            'code': code,
                            'name': self.etf_pool[code]['name'],
                            'entry_price': entry_price,
                            'current_price': current_price,
                            'return': asset_return
                        })
        
        trigger = len(stop_loss_assets) > 0
        
        return {
            'trigger': trigger,
            'assets': stop_loss_assets
        }
    
    def check_trigger_conditions(self, prices, date, current_weights, target_weights,
                                 current_positions, current_value, entry_prices, 
                                 days_since_rebalance):
        """
触发条件检查
        
        综合        触发逻辑：
        1. 止损：强制触发
        2. 偏离度 + 信号强度 = 综合得分>0.5
        3. 冷却期内不触发
        
        Args:
            prices: 价格数据
            date: 检查日期
            current_weights: 当前权重
            target_weights: 目标权重
            current_positions: 当前持仓
            current_value: 当前价值
            entry_prices: 入场价
            days_since_rebalance: 距上次调仓天数
        
        Returns:
            dict: 触发结果
        """
        # 冷却期检查
        if days_since_rebalance < self.cooldown_days:
            return {
                'rebalance': False,
                'reason_type': 'cooldown',
                'reason': f"冷却期内({days_since_rebalance}/{self.cooldown_days}天)",
                'detail': {'cooldown': True}
            }
        
        # 条件1：权重偏离度
        deviation = self.calculate_deviation(current_weights, target_weights)
        max_deviation = deviation.max() if len(deviation) > 0 else 0
        avg_deviation = deviation.mean() if len(deviation) > 0 else 0
        
        # 条件2：强信号
        strong_signal_result = self.check_strong_signal(prices, date)
        
        # 条件3：止损
        current_prices = prices.loc[date]
        stop_loss_result = self.check_stop_loss(
            current_prices, current_positions,
            current_value, date, entry_prices
        )
        
        # 止损强制触发
        if stop_loss_result['trigger']:
            return {
                'rebalance': True,
                'reason_type': 'stop_loss',
                'reason': f"止损触发: {[a['name'] for a in stop_loss_result['assets']]}",
                'detail': {
                    'max_deviation': max_deviation,
                    'strong_signal': False,
                    'stop_loss': True
                },
                'stop_loss_assets': stop_loss_result['assets']
            }
        
        # 冷却期检查 - 但偏离度严重超标时忽略冷却期
        deviation_score = 1 if max_deviation > self.trigger_deviation else 0
        severe_deviation = max_deviation > self.trigger_deviation * 2  # 偏离度超过阈值2倍
        
        if days_since_rebalance < self.cooldown_days and not severe_deviation:
            return {
                'rebalance': False,
                'reason_type': 'cooldown',
                'reason': f"冷却期内({days_since_rebalance}/{self.cooldown_days}天)",
                'detail': {'cooldown': True, 'max_deviation': max_deviation}
            }
        
        # 综合判断（偏离度50% + 信号50%）
        signal_score = 1 if strong_signal_result['signal'] else 0
        
        total_score = (
            deviation_score * (1 - self.signal_weight) +
            signal_score * self.signal_weight
        )
        
        # 触发条件：综合得分>0.5或偏离度超过阈值，或严重偏离（忽略冷却期）
        if total_score > 0.5 or max_deviation > self.trigger_deviation or severe_deviation:
            reason_parts = []
            if deviation_score:
                reason_parts.append(f"偏离度{max_deviation:.2%}（阈值{self.trigger_deviation:.0%}）")
            if signal_score:
                reason_parts.append("强信号")
            if severe_deviation:
                reason_parts.append("严重偏离(忽略冷却期)")
            
            return {
                'rebalance': True,
                'reason_type': 'normal',
                'reason': ", ".join(reason_parts),
                'detail': {
                    'max_deviation': max_deviation,
                    'avg_deviation': avg_deviation,
                    'strong_signal': strong_signal_result['signal'],
                    'total_score': total_score
                }
            }
        
        return {
            'rebalance': False,
            'reason_type': 'no_trigger',
            'reason': f"偏离度{max_deviation:.2%} < 阈值，无强信号",
            'detail': {
                'max_deviation': max_deviation,
                'avg_deviation': avg_deviation,
                'strong_signal': strong_signal_result['signal'],
                'total_score': total_score
            }
        }
    
    def execute_rebalance(self, current_value, current_positions, target_weights, 
                        current_prices, date, cash, entry_prices):
        """
        执行再平衡操作
        
        Args:
            current_value: 当前组合价值
            current_positions: 当前持仓
            target_weights: 目标权重
            current_prices: 当前价格
            date: 调仓日期
            cash: 现金
            entry_prices: 入场价
        
        Returns:
            dict: 调仓结果
        """
        trades = []
        
        # 第一步：先卖出不再持有的ETF（目标权重为0）
        target_codes = set(target_weights[target_weights > 0].index)
        for code in list(current_positions.keys()):
            if code not in target_codes and current_positions.get(code, 0) > 0:
                shares = current_positions[code]
                price = current_prices.get(code, 0)
                
                # 确保价格有效
                if pd.isna(price) or price <= 0:
                    continue
                    
                gross_sell_value = shares * price
                fee = gross_sell_value * self.transaction_cost
                sell_value = self._sell_net_proceeds(gross_sell_value)
                cash += sell_value
                trades.append({
                    'date': date,
                    'action': '清仓',
                    'code': code,
                    'name': self.etf_pool[code]['name'],
                    'price': price,
                    'shares': -shares,
                    'value': sell_value,
                    'gross_value': gross_sell_value,
                    'fee': fee
                })
                current_positions[code] = 0
                entry_prices[code] = 0
        
        # 第二步：买入目标ETF
        for code in target_weights.index:
            price = current_prices.get(code, 0)
            
            # 跳过价格无效的标的
            if pd.isna(price) or price <= 0:
                continue
            
            target_value = current_value * target_weights[code]
            
            # 跳过目标价值小于最小持仓金额的标的
            min_value = self.constraints.get('min_holding', 1000)
            if target_value < min_value:
                continue
            
            current_shares = current_positions.get(code, 0)
            
            current_value_asset = current_shares * price
            
            # 买入/卖出判断（考虑最小交易单位）
            diff = target_value - current_value_asset
            
            if abs(diff) > 500:  # 差异超过500元才交易
                shares_to_trade = int(abs(diff) / price / 100) * 100  # 按手交易
                
                if shares_to_trade > 0:
                    if diff > 0:
                        affordable_shares = int(cash / (price * (1 + self.transaction_cost)) / 100) * 100
                        shares_to_trade = min(shares_to_trade, affordable_shares)

                    if diff > 0 and shares_to_trade > 0:
                        # 买入
                        gross_cost = shares_to_trade * price
                        fee = gross_cost * self.transaction_cost
                        total_cost = self._buy_total_cost(gross_cost)
                        cash -= total_cost
                        current_positions[code] = current_shares + shares_to_trade
                        
                        # 更新入场价
                        if current_shares > 0:
                            old_cost = entry_prices.get(code, 0) * current_shares
                            new_cost = old_cost + gross_cost
                            entry_prices[code] = new_cost / (current_shares + shares_to_trade)
                        else:
                            entry_prices[code] = price
                        
                        trades.append({
                            'date': date,
                            'action': '买入',
                            'code': code,
                            'name': self.etf_pool[code]['name'],
                            'price': price,
                            'shares': shares_to_trade,
                            'value': total_cost,
                            'gross_value': gross_cost,
                            'fee': fee
                        })
                        
                    elif diff < 0 and current_shares >= shares_to_trade:
                        # 卖出
                        gross_sell_value = shares_to_trade * price
                        fee = gross_sell_value * self.transaction_cost
                        sell_value = self._sell_net_proceeds(gross_sell_value)
                        cash += sell_value
                        current_shares_new = current_shares - shares_to_trade
                        current_positions[code] = current_shares_new
                        
                        # 如果全部卖出，重置入场价
                        if current_shares_new == 0:
                            entry_prices[code] = 0
                        
                        trades.append({
                            'date': date,
                            'action': '卖出',
                            'code': code,
                            'name': self.etf_pool[code]['name'],
                            'price': price,
                            'shares': shares_to_trade,
                            'value': sell_value,
                            'gross_value': gross_sell_value,
                            'fee': fee
                        })
        
        return {
            'cash': cash,
            'positions': current_positions,
            'entry_prices': entry_prices,
            'trades': trades
        }
    
    def backtest(self, start_date, end_date, verbose=True):
        """
        回测策略
        
        Args:
            start_date: 回测开始日期 'YYYY-MM-DD'
            end_date: 回测结束日期 'YYYY-MM-DD'
            verbose: 是否打印详细信息
        
        Returns:
            dict: 回测结果
        """
        if verbose:
            print("=" * 70)
            print(" " * 15 + "每日监测+触发调仓BLM策略（10只ETF版）")
            print("=" * 70)
            print(f"策略参数：")
            print(f"  初始资金: {self.initial_capital:,.0f}")
            print(f"  偏离度阈值: {self.trigger_deviation*100:.0f}%")
            print(f"  信号权重: {self.signal_weight*100:.0f}%")
            print(f"  止损阈值: {self.stop_loss_threshold*100:.0f}%")
            print(f"  动量回看期: {self.lookback_period}天")
            print(f"  交易成本: {self.transaction_cost*100:.2f}%（单边）")
            print("=" * 70)
        
        # 获取数据
        prices = self.fetch_data(start_date, end_date)
        
        if prices.empty or len(prices) < self.lookback_period:
            if verbose:
                print("错误：数据获取失败或数据不足！")
            return {}
        
        # 初始化变量
        cash = self.initial_capital
        current_positions = {code: 0 for code in self.etf_pool.keys()}
        entry_prices = {code: 0 for code in self.etf_pool.keys()}
        
        # 交易记录
        trades = []
        nav_history = []
        rebalance_count = 0
        
        # 前向填充价格数据（处理ETF上市日期不同的问题）
        prices = prices.ffill()
        
        # 移除NaN
        prices = prices.fillna(0)
        
        # 找到所有ETF都有数据的日期范围
        valid_dates = prices.dropna(axis=1, how='any').index
        if len(valid_dates) == 0:
            if verbose:
                print("错误：没有共同交易日！")
            return {}
        
        # 取第一个有数据的日期开始回测
        first_valid_date = valid_dates[0]
        trading_days = valid_dates[valid_dates >= prices.iloc[self.lookback_period:].index[0]]
        
        if len(trading_days) < 10:
            if verbose:
                print("错误：有效交易日不足！")
            return {}
        
        first_day = trading_days[0]
        first_prices = prices.loc[first_day]
        
        # 计算动量，只持仓前3只
        momentum_scores = self.calculate_momentum_score(prices, first_day)
        top3_codes = momentum_scores.nlargest(self.top_n).index.tolist()
        
        # 初始建仓只买前3只
        weight_per = 1.0 / self.top_n
        
        for code in top3_codes:
            price = first_prices.get(code)
            if pd.isna(price) or price == 0:
                continue
            target_value = self.initial_capital * weight_per
            shares = int(target_value / price / 100) * 100
            gross_cost = shares * price
            total_cost = self._buy_total_cost(gross_cost)
            fee = gross_cost * self.transaction_cost
            if shares > 0 and cash >= total_cost:
                cash -= total_cost
                current_positions[code] = shares
                entry_prices[code] = price
                trades.append({
                    'date': first_day,
                    'action': '初始建仓',
                    'code': code,
                    'name': self.etf_pool[code]['name'],
                    'price': price,
                    'shares': shares,
                    'value': total_cost,
                    'gross_value': gross_cost,
                    'fee': fee
                })
        
        # 记录初始建仓信息
        old_names = []
        new_names = [self.etf_pool[code]['name'] for code in current_positions.keys() if current_positions[code] > 0]
        initial_value = self.initial_capital
        initial_return = 0
        
        rebalance_count = 1
        self.rebalance_history.append({
            'date': first_day,
            'reason': '初始建仓',
            'max_deviation': 0,
            'trigger_type': 'initial',
            'old_positions': ','.join(old_names) if old_names else '空仓',
            'new_positions': ','.join(new_names),
            'value_before': initial_value,
            'return_before': initial_return
        })
        
        if verbose:
            print(f"\n回测设置：")
            print(f"  回测期间: {start_date} 至 {end_date}")
            print(f"  交易日数: {len(trading_days)}")
            print("-" * 70)
            print("开始回测...")
            print("-" * 70)
        
        # 逐日回测
        for i, date in enumerate(trading_days):
            # 获取当前价格
            current_prices = prices.loc[date]
            
            # 计算当前组合价值
            position_value = 0.0
            for code in current_positions.keys():
                shares = current_positions[code]
                price = current_prices.get(code, 0)
                if pd.isna(price):
                    price = 0
                price = float(price) if not pd.isna(price) else 0
                position_value += shares * price
            current_value = cash + position_value
            
            # 计算当前持仓权重
            if current_value > 0:
                current_weights_dict = {}
                for code in current_positions.keys():
                    price = current_prices.get(code, 0)
                    if pd.isna(price):
                        price = 0
                    weight = (current_positions[code] * price) / current_value
                    current_weights_dict[code] = weight
                current_weights = pd.Series(current_weights_dict)
            else:
                current_weights = pd.Series({code: 0 for code in self.etf_pool.keys()})
            
            # 记录净值
            nav = current_value / self.initial_capital
            nav_history.append({
                'date': date,
                'nav': nav,
                'nav_log': np.log(nav) if nav > 0 else 0,
                'value': current_value,
                'cash': cash,
                'total_return': (nav - 1) * 100
            })
            
            # 计算目标权重
            try:
                target_weights = self.calculate_BLM_weights(prices, date)
            except Exception as e:
                if verbose and i % 50 == 0:
                    print(f"[{date.strftime('%Y-%m-%d')}] 计算目标权重出错: {e}")
                continue
            
            # 检查触发条件（计算距上次调仓天数）
            if len(self.rebalance_history) > 0:
                last_rebalance_date = self.rebalance_history[-1]['date']
                days_since_rebalance = (date - last_rebalance_date).days
            else:
                days_since_rebalance = 999
            
            trigger_result = self.check_trigger_conditions(
                prices, date, current_weights, target_weights,
                current_positions, current_value, entry_prices,
                days_since_rebalance
            )
            
            # 处理止损
            if trigger_result.get('reason_type') == 'stop_loss':
                for asset in trigger_result.get('stop_loss_assets', []):
                    code = asset['code']
                    if current_positions[code] > 0:
                        sell_shares = current_positions[code]
                        gross_sell_value = sell_shares * current_prices[code]
                        fee = gross_sell_value * self.transaction_cost
                        sell_value = self._sell_net_proceeds(gross_sell_value)
                        cash += sell_value
                        current_positions[code] = 0
                        entry_prices[code] = 0
                        
                        trades.append({
                            'date': date,
                            'action': '止损',
                            'code': code,
                            'name': self.etf_pool[code]['name'],
                            'price': current_prices[code],
                            'shares': -sell_shares,
                            'value': sell_value,
                            'gross_value': gross_sell_value,
                            'fee': fee
                        })
            
            # 触发调仓
            if trigger_result['rebalance']:
                rebalance_count += 1
                
                # 计算调仓时的收益
                total_return = (current_value - self.initial_capital) / self.initial_capital * 100
                
                # 原持仓
                old_positions = {code: shares for code, shares in current_positions.items() if shares > 0}
                old_names = [self.etf_pool[code]['name'] for code in old_positions.keys()]
                
                # 新持仓（目标）
                new_codes = target_weights[target_weights > 0].index.tolist()
                new_names = [self.etf_pool[code]['name'] for code in new_codes]
                
                # 记录调仓历史
                self.rebalance_history.append({
                    'date': date,
                    'reason': trigger_result['reason'],
                    'max_deviation': trigger_result['detail'].get('max_deviation', 0),
                    'trigger_type': trigger_result['reason_type'],
                    'old_positions': ','.join(old_names) if old_names else '空仓',
                    'new_positions': ','.join(new_names),
                    'value_before': current_value,
                    'return_before': total_return
                })
                
                if verbose and rebalance_count <= 10:  # 只打印前10次
                    print(f"\n[{date.strftime('%Y-%m-%d')}] 第{rebalance_count}次调仓: {trigger_result['reason']}")
                
                # 执行再平衡
                rebalance_result = self.execute_rebalance(
                    current_value, current_positions, target_weights,
                    current_prices, date, cash, entry_prices
                )
                
                cash = rebalance_result['cash']
                current_positions = rebalance_result['positions']
                entry_prices = rebalance_result['entry_prices']
                
                # 记录交易
                trades.extend(rebalance_result['trades'])
        
        if verbose:
            print("-" * 70)
            print("回测完成！开始计算结果...")
            print("=" * 70)
        
        # 计算最终结果
        final_prices = prices.iloc[-1]
        final_value = cash + sum(
            current_positions[code] * final_prices.get(code, 0)
            for code in current_positions.keys()
        )
        final_nav = final_value / self.initial_capital
        
        # 构建净值数据
        nav_df = pd.DataFrame(nav_history).set_index('date')
        
        # 计算核心指标
        results = self._calculate_performance_metrics(nav_df, len(trading_days))
        
        # 添加额外信息
        results.update({
            'initial_capital': self.initial_capital,
            'final_value': final_value,
            'total_return': (final_nav - 1) * 100,
            'rebalance_count': rebalance_count,
            'trades': pd.DataFrame(trades),
            'nav_history': nav_df,
            'rebalance_history': self.rebalance_history,
            'final_positions': self._get_final_positions(current_positions, final_prices),
            'backtest_days': len(trading_days),
            'requested_start_date': start_date,
            'requested_end_date': end_date,
            'data_start_date': prices.index.min().strftime('%Y-%m-%d'),
            'data_end_date': prices.index.max().strftime('%Y-%m-%d')
        })
        
        # 生成报告
        if verbose:
            self.generate_report(results)
            self.plot_results(results)
        
        return results
    
    def _calculate_performance_metrics(self, nav_df, trading_days):
        """计算绩效指标"""
        nav = nav_df['nav']
        
        # 年化收益
        total_return = nav.iloc[-1] - 1
        years = trading_days / 252
        annual_return = ((nav.iloc[-1]) ** (1/years) - 1) if years > 0 else 0
        
        # 年化波动率
        daily_returns = nav.pct_change().dropna()
        annual_vol = daily_returns.std() * np.sqrt(252) if len(daily_returns) > 0 else 0
        
        # 夏普比率（无风险利率3%）
        sharpe_ratio = (annual_return - 0.03) / annual_vol if annual_vol > 0 else 0
        
        # 最大回撤
        cummax = nav.cummax()
        drawdown = (nav - cummax) / cummax
        max_drawdown = drawdown.min()
        
        # 最大回撤持续期
        is_drawdown = drawdown < 0
        drawdown_periods = []
        start_dd = None
        
        for i, is_dd in enumerate(is_drawdown):
            if is_dd and start_dd is None:
                start_dd = i
            elif not is_dd and start_dd is not None:
                drawdown_periods.append(i - start_dd)
                start_dd = None
        
        if start_dd is not None:
            drawdown_periods.append(len(is_drawdown) - start_dd)
        
        max_drawdown_duration = max(drawdown_periods) if drawdown_periods else 0
        
        # 胜率
        winning_days = (daily_returns > 0).sum()
        win_rate = winning_days / len(daily_returns) if len(daily_returns) > 0 else 0
        
        # 盈亏比
        positive_returns = daily_returns[daily_returns > 0]
        negative_returns = daily_returns[daily_returns < 0]
        profit_loss_ratio = (abs(positive_returns.mean()) / abs(negative_returns.mean()) 
                           if len(negative_returns) > 0 else 0)
        
        return {
            'annual_return': annual_return * 100,
            'annual_volatility': annual_vol * 100,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown * 100,
            'max_drawdown_duration': max_drawdown_duration,
            'win_rate': win_rate * 100,
            'profit_loss_ratio': profit_loss_ratio,
            'calmar_ratio': -annual_return / abs(max_drawdown) if max_drawdown < 0 else 0
        }
    
    def _get_final_positions(self, positions, prices):
        """获取最终持仓信息"""
        final_positions = {}
        for code, shares in positions.items():
            if shares > 0:
                price = prices.get(code, 0)
                final_positions[code] = {
                    'name': self.etf_pool[code]['name'],
                    'shares': shares,
                    'price': price,
                    'value': shares * price
                }
        return final_positions
    
    def generate_report(self, results):
        """生成回测报告"""
        print("\n" + "=" * 70)
        print(" " * 25 + "回测结果汇总")
        print("=" * 70)
        
        # 基本信息卡片
        print("\n【基本信息】")
        print(f"  初始本金: {results['initial_capital']:,.2f}")
        print(f"  最终资产: {results['final_value']:,.2f}")
        print(f"  总收益率: {results['total_return']:+.2f}%")
        print(f"  回测天数: {results['backtest_days']}天")
        
        # 绩效指标卡片
        print("\n【绩效指标】")
        print(f"  年化收益: {results['annual_return']:+.2f}%")
        print(f"  年化波动: {results['annual_volatility']:.2f}%")
        print(f"  最大回撤: {results['max_drawdown']:.2f}%")
        print(f"  夏普比率: {results['sharpe_ratio']:.2f}")
        print(f"  卡玛比率: {results['calmar_ratio']:.2f}")
        
        # 交易统计
        print("\n【交易统计】")
        print(f"  调仓次数: {results['rebalance_count']}次")
        if results['rebalance_count'] > 0:
            freq = results['backtest_days'] / results['rebalance_count']
            print(f"  平均频率: {freq:.1f}天/次")
            print(f"  预估年调仓: {252/freq:.0f}次")
        
        print(f"  总交易次数: {len(results['trades'])}笔")
        
        # 最终持仓
        print("\n【最终持仓】")
        total_value = sum(pos['value'] for pos in results['final_positions'].values())
        for code, pos in results['final_positions'].items():
            weight = pos['value'] / total_value if total_value > 0 else 0
            print(f"  {pos['name'][:8]:8s}: {pos['shares']:>5d}股, {pos['value']:>8.0f}, {weight*100:>5.1f}%")
        
        print("=" * 70)
    
    def plot_results(self, results):
        """绘制回测结果图表"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('BLM策略回测结果（10只ETF）', fontsize=16, fontweight='bold')
        
        nav_df = results['nav_history']
        
        # 1. 净值曲线
        ax1 = axes[0, 0]
        ax1.plot(nav_df.index, nav_df['nav'], linewidth=2, label='策略净值')
        # 添加参考线
        if nav_df['nav'].iloc[0] > 0:
            buy_hold_nav = nav_df['nav'].iloc[0] * (1 + 0.08 * np.arange(len(nav_df)) / 252)  # 8%年化收益参考
            ax1.plot(nav_df.index, buy_hold_nav, '--', alpha=0.6, label='8%年化参考')
        
        ax1.set_title('净值曲线', fontweight='bold')
        ax1.set_ylabel('净值')
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        
        # 标注最大回撤
        cummax = nav_df['nav'].cummax()
        drawdown = (nav_df['nav'] - cummax) / cummax
        max_dd_idx = drawdown.idxmin()
        ax1.scatter([max_dd_idx], [nav_df['nav'].loc[max_dd_idx]], 
                   color='red', s=100, zorder=5, label='最大回撤')
        
        # 2. 回撤曲线
        ax2 = axes[0, 1]
        ax2.fill_between(nav_df.index, 0, drawdown * 100, alpha=0.3, color='red')
        ax2.plot(nav_df.index, drawdown * 100, linewidth=1, color='red')
        ax2.set_title(f'回撤曲线（最大: {results["max_drawdown"]:.2f}%）', fontweight='bold')
        ax2.set_ylabel('回撤 (%)')
        ax2.grid(True, alpha=0.3)
        
        # 3. 每日收益率分布
        ax3 = axes[1, 0]
        daily_returns = nav_df['nav'].pct_change().dropna()
        ax3.hist(daily_returns * 100, bins=50, color='steelblue', edgecolor='black', alpha=0.7)
        ax3.axvline(daily_returns.mean() * 100, color='red', linestyle='--', 
                   label=f'均值: {daily_returns.mean()*100:.3f}%')
        ax3.set_title('日收益率分布', fontweight='bold')
        ax3.set_xlabel('日收益率 (%)')
        ax3.set_ylabel('频数')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. 净值对数收益率
        ax4 = axes[1, 1]
        ax4.plot(nav_df.index, nav_df['nav_log'], linewidth=1.5)
        ax4.set_title('对数净值曲线（观察复合增长）', fontweight='bold')
        ax4.set_ylabel('ln(净值)')
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()

# ================================
# 最优策略详细回测
# ================================

if __name__ == "__main__":
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=3650)).strftime('%Y-%m-%d')
    
    print("=" * 75)
    print("优化策略详细回测（偏离度20% + 冷却20天）")
    print("=" * 75)
    
    strategy = DailyMonitoringBLM(
        initial_capital=52000, trigger_deviation=0.20, signal_weight=0.2,
        stop_loss_threshold=-0.18, lookback_period=30, cooldown_days=20,
        top_n=3, transaction_cost=0.0002
    )
    strategy.constraints = {
        'max_single_weight': 0.35,
        'min_holding': 1000
    }
    
    results = strategy.backtest(start_date, end_date, verbose=True)
    
    # 保存JSON
    import json
    nav_df = results['nav_history']
    nav_data = nav_df[['nav', 'value', 'total_return']].reset_index()
    nav_data['date'] = nav_data['date'].dt.strftime('%Y-%m-%d')
    
    navs = nav_data['nav'].tolist()
    cummax = [max(navs[:i+1]) for i in range(len(navs))]
    drawdowns = [(navs[i] - cummax[i]) / cummax[i] * 100 for i in range(len(navs))]
    nav_data['drawdown'] = drawdowns
    
    rebalance_history = []
    import math
    for rb in results.get('rebalance_history', []):
        val_before = rb.get('value_before')
        ret_before = rb.get('return_before')
        
        # 强制转换，处理NaN
        value_before = 0 if (val_before is None or (isinstance(val_before, float) and math.isnan(val_before))) else float(val_before)
        return_before = 0 if (ret_before is None or (isinstance(ret_before, float) and math.isnan(ret_before))) else float(ret_before)
            
        rb_data = {
            'date': rb['date'].strftime('%Y-%m-%d') if hasattr(rb['date'], 'strftime') else str(rb['date']),
            'reason': rb['reason'],
            'old_positions': rb.get('old_positions', ''),
            'new_positions': rb.get('new_positions', ''),
            'value_before': value_before,
            'return_before': return_before,
        }
        rebalance_history.append(rb_data)
    
    # 计算年度收益
    nav_data['date_parsed'] = pd.to_datetime(nav_data['date'])
    nav_data['year'] = nav_data['date_parsed'].dt.year
    
    yearly_returns = []
    for year in sorted(nav_data['year'].unique()):
        year_data = nav_data[nav_data['year'] == year].sort_values('date')
        if len(year_data) > 0:
            start_nav = year_data.iloc[0]['nav']
            end_nav = year_data.iloc[-1]['nav']
            year_return = (end_nav - start_nav) / start_nav * 100
            yearly_returns.append({
                'year': int(year),
                'start_value': start_nav * results['initial_capital'],
                'end_value': end_nav * results['initial_capital'],
                'return': year_return,
                'trading_days': len(year_data)
            })
    
    web_data = {
        'summary': {
            'initial_capital': results['initial_capital'],
            'final_value': results['final_value'],
            'total_return': results['total_return'],
            'annual_return': results['annual_return'],
            'annual_volatility': results['annual_volatility'],
            'max_drawdown': results['max_drawdown'],
            'sharpe_ratio': results['sharpe_ratio'],
            'calmar_ratio': results.get('calmar_ratio', 0),
            'rebalance_count': results['rebalance_count'],
            'backtest_days': results['backtest_days'],
        },
        'yearly_returns': yearly_returns,
        'nav_history': nav_data[['date', 'nav', 'value', 'total_return', 'drawdown']].to_dict(orient='records'),
        'rebalance_history': rebalance_history,
        'final_positions': results.get('final_positions', {}),
    }
    
    with open('策略执行/backtest_data.json', 'w', encoding='utf-8') as f:
        json.dump(web_data, f, ensure_ascii=False, indent=2)
    
    print("\n数据已保存到 backtest_data.json")