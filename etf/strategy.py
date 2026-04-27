"""
ETF 策略计算模块（简化版）
不依赖 pandas/numpy，使用纯 Python 实现
"""
from datetime import datetime, timedelta
import sqlite3
from pathlib import Path


DB_PATH = Path('/opt/data/scripts/etf/data/etf.db')

ETF_POOL = {
    '510500': {'name': '中证500ETF', 'style': 'small_cap', 'base_weight': 0.25},
    '159941': {'name': '纳指ETF', 'style': 'us_tech', 'base_weight': 0.25},
    '511010': {'name': '国债ETF', 'style': 'gov_bond', 'base_weight': 0.20},
    '518880': {'name': '黄金ETF', 'style': 'commodity', 'base_weight': 0.15},
    '159928': {'name': '消费ETF', 'style': 'defensive', 'base_weight': 0.15},
}

# 风格因子
STYLE_FACTORS = {
    'small_cap': 1.25, 'growth': 1.20, 'mid_cap': 1.10,
    'large_cap': 1.00, 'tech': 1.15, 'cyclical': 1.10,
    'defensive': 0.70, 'gov_bond': 0.60, 'convertible': 0.85,
    'commodity': 0.95, 'a_share': 1.00, 'us_tech': 1.15
}


class Strategy:
    """ETF 动量策略计算器（简化版）"""
    
    def __init__(self, etf_pool=None, params=None):
        self.etf_pool = etf_pool or ETF_POOL
        self.params = params or {}
        self.trigger_deviation = self.params.get('trigger_deviation', 0.15)
        self.lookback_period = self.params.get('lookback_period', 60)
        self.top_n = self.params.get('top_n', 3)
        self.stop_loss_threshold = self.params.get('stop_loss_threshold', -0.18)
    
    def calculate_momentum_scores(self, prices_dict):
        """
        计算动量得分
        
        Args:
            prices_dict: {code: {'price': float, 'pct_change': float, ...}}
        
        Returns:
            dict: {code: score}
        """
        scores = {}
        
        for code, info in prices_dict.items():
            if code not in self.etf_pool:
                continue
            
            # 基础得分 = 涨跌幅 * 风格因子
            pct_change = info.get('pct_change', 0)
            style = self.etf_pool[code].get('style', 'a_share')
            style_factor = STYLE_FACTORS.get(style, 1.0)
            
            # 简化的动量得分
            # 涨幅越大得分越高，跌幅越大得分越低
            base_score = 50 + pct_change * 10  # 基准50分
            
            # 应用风格因子
            score = base_score * style_factor
            
            # 限制在 0-100 之间
            scores[code] = max(0, min(100, score))
        
        return scores
    
    def calculate_target_weights(self, prices_dict):
        """
        计算目标权重
        
        Args:
            prices_dict: {code: {'price': float, 'pct_change': float, ...}}
        
        Returns:
            dict: {code: weight}
        """
        scores = self.calculate_momentum_scores(prices_dict)
        
        if not scores:
            return {}
        
        # 按得分排序
        sorted_codes = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        
        # 只保留前 top_n 个
        top_codes = sorted_codes[:self.top_n]
        
        # 计算权重
        weights = {}
        total_score = sum(scores[c] for c in top_codes)
        
        if total_score > 0:
            for code in self.etf_pool.keys():
                if code in top_codes:
                    weights[code] = scores[code] / total_score
                else:
                    weights[code] = 0
        else:
            # 如果得分为0，平均分配
            for code in top_codes:
                weights[code] = 1.0 / len(top_codes)
        
        # 应用单一资产上限
        max_weight = 0.40
        for code in weights:
            if weights[code] > max_weight:
                weights[code] = max_weight
        
        # 重新归一化
        total = sum(weights.values())
        if total > 0:
            weights = {k: v/total for k, v in weights.items()}
        
        return weights
    
    def check_rebalance(self, current_weights, target_weights, prices_dict, 
                        last_rebalance_date=None, current_shares=None, entry_prices=None):
        """
        检查是否需要调仓
        
        Args:
            current_weights: 当前持仓权重 {code: weight}
            target_weights: 目标权重 {code: weight}
            prices_dict: 价格数据
            last_rebalance_date: 上次调仓日期
            current_shares: 当前持仓 {code: shares}
            entry_prices: 入场价格 {code: price}
        
        Returns:
            dict: 调仓建议
        """
        # 计算偏离度
        max_deviation = 0
        deviation_detail = {}
        
        all_codes = set(current_weights.keys()) | set(target_weights.keys())
        
        for code in all_codes:
            current = current_weights.get(code, 0)
            target = target_weights.get(code, 0)
            dev = abs(current - target)
            deviation_detail[code] = round(dev * 100, 2)
            if dev > max_deviation:
                max_deviation = dev
        
        # 止损检测
        stop_loss_assets = []
        if current_shares and entry_prices:
            for code, shares in current_shares.items():
                if shares > 0 and code in entry_prices and code in prices_dict:
                    entry_price = entry_prices.get(code, 0)
                    current_price = prices_dict[code].get('price', 0)
                    
                    if entry_price > 0 and current_price > 0:
                        asset_return = (current_price - entry_price) / entry_price
                        
                        if asset_return < self.stop_loss_threshold:
                            stop_loss_assets.append({
                                'code': code,
                                'name': self.etf_pool[code]['name'],
                                'return': round(asset_return * 100, 2)
                            })
        
        stop_loss_trigger = len(stop_loss_assets) > 0
        
        # 判断是否需要调仓
        reasons = []
        should_rebalance = False
        
        if stop_loss_trigger:
            should_rebalance = True
            reasons.append(f"止损触发: {[a['name'] for a in stop_loss_assets]}")
        
        if max_deviation > self.trigger_deviation:
            should_rebalance = True
            reasons.append(f"偏离度{max_deviation*100:.1f}% > 阈值{self.trigger_deviation*100:.0f}%")
        
        if not should_rebalance:
            reasons.append("无需调仓")
        
        return {
            'should_rebalance': should_rebalance,
            'reasons': reasons,
            'max_deviation': round(max_deviation * 100, 2),
            'deviation_detail': deviation_detail,
            'target_weights': {k: round(v*100, 1) for k, v in target_weights.items() if v > 0},
            'stop_loss_trigger': stop_loss_trigger,
            'stop_loss_assets': stop_loss_assets
        }
    
    def analyze(self, prices_dict, current_weights, last_rebalance_date=None):
        """
        完整分析
        
        Args:
            prices_dict: 价格数据
            current_weights: 当前权重
            last_rebalance_date: 上次调仓日期
        
        Returns:
            dict: 分析结果
        """
        scores = self.calculate_momentum_scores(prices_dict)
        target_weights = self.calculate_target_weights(prices_dict)
        rebalance_check = self.check_rebalance(
            current_weights, target_weights, prices_dict, last_rebalance_date
        )
        
        # 动量排名列表
        momentum_list = []
        for code, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            momentum_list.append({
                'code': code,
                'name': self.etf_pool[code]['name'],
                'score': round(score, 1),
                'target_weight': round(target_weights.get(code, 0) * 100, 1)
            })
        
        return {
            'target_weights': target_weights,
            'momentum_scores': scores,
            'momentum_list': momentum_list,
            'rebalance_check': rebalance_check
        }
