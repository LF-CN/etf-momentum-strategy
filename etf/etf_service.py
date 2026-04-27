#!/usr/bin/env python3
"""
ETF 策略服务入口
统一调用接口，供 Hermes 调用
"""
import sys
import os
import json
from datetime import datetime
from pathlib import Path

# 添加路径
sys.path.insert(0, '/opt/data/scripts/etf')

# 设置工作目录
os.chdir('/opt/data/scripts/etf')

# 导入本地配置（注意：要先用绝对导入）
import importlib.util
spec = importlib.util.spec_from_file_location("etf_config", "/opt/data/scripts/etf/config.py")
etf_config = importlib.util.module_from_spec(spec)
sys.modules['etf_config'] = etf_config
spec.loader.exec_module(etf_config)

ETF_POOL = etf_config.ETF_POOL
STRATEGY_PARAMS = etf_config.STRATEGY_PARAMS
DB_PATH = etf_config.DB_PATH
SIGNAL_FILE = etf_config.SIGNAL_FILE

# 现在可以导入数据库模块
from database import (
    get_holdings, get_cash, set_cash, get_initial_capital,
    add_trade, get_trades, update_holding,
    save_nav, get_latest_nav, get_nav_history,
    save_signal, get_pending_signals, process_signal,
    set_setting,
)


class ETFService:
    """ETF 策略服务"""
    
    def __init__(self):
        self.etf_pool = ETF_POOL
        self.params = STRATEGY_PARAMS
    
    def get_portfolio_summary(self):
        """获取持仓概览"""
        holdings = get_holdings()
        cash = get_cash()
        initial_capital = get_initial_capital()
        
        # 获取最新价格
        prices = self._get_current_prices()
        
        # 计算市值
        total_value = 0
        holdings_detail = []
        
        for code, data in holdings.items():
            if data['shares'] > 0:
                price = prices.get(code, data.get('cost_price', 0))
                market_value = data['shares'] * price
                cost_value = data['shares'] * data.get('cost_price', 0)
                profit = market_value - cost_value
                profit_pct = (profit / cost_value * 100) if cost_value > 0 else 0
                
                holdings_detail.append({
                    'code': code,
                    'name': data['name'],
                    'shares': data['shares'],
                    'cost_price': data.get('cost_price', 0),
                    'current_price': price,
                    'market_value': market_value,
                    'profit': profit,
                    'profit_pct': profit_pct
                })
                total_value += market_value
        
        total_asset = total_value + cash
        total_profit = total_asset - initial_capital
        total_profit_pct = (total_profit / initial_capital * 100) if initial_capital > 0 else 0
        
        return {
            'holdings': holdings_detail,
            'cash': cash,
            'total_value': total_value,
            'total_asset': total_asset,
            'initial_capital': initial_capital,
            'total_profit': total_profit,
            'total_profit_pct': total_profit_pct,
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def _get_current_prices(self):
        """获取当前价格"""
        prices = {}
        try:
            from pqquotation import use
            q = use('dc')  # 东方财富实时行情
            
            for code in self.etf_pool.keys():
                try:
                    data = q.real(code)
                    if data and code in data:
                        prices[code] = float(data[code].get('now', 0))
                except:
                    pass
        except Exception as e:
            # 如果获取失败，使用缓存的价格
            for code in self.etf_pool.keys():
                holdings = get_holdings()
                if code in holdings:
                    prices[code] = holdings[code].get('current_price', holdings[code].get('cost_price', 0))
        
        return prices
    
    def record_trade(self, code, action, shares, price=None, note=None):
        """记录交易"""
        if code not in self.etf_pool:
            return {'success': False, 'error': f'未知ETF代码: {code}'}
        
        name = self.etf_pool[code]['name']
        
        # 如果没有提供价格，获取当前价格
        if price is None:
            prices = self._get_current_prices()
            price = prices.get(code, 0)
        
        shares = float(shares)
        price = float(price)
        
        # 获取当前持仓
        holdings = get_holdings()
        current_shares = holdings.get(code, {}).get('shares', 0)
        cost_price = holdings.get(code, {}).get('cost_price', price)
        
        if action == 'buy':
            # 买入：更新成本价（加权平均）
            total_cost = current_shares * cost_price + shares * price
            new_shares = current_shares + shares
            new_cost_price = total_cost / new_shares if new_shares > 0 else price
            
            update_holding(code, name, new_shares, new_cost_price, price)
            
            # 扣除现金
            cash = get_cash()
            set_cash(cash - shares * price)
            
        elif action == 'sell':
            # 卖出
            if current_shares < shares:
                return {'success': False, 'error': f'卖出数量超过持仓 ({current_shares}份)'}
            
            new_shares = current_shares - shares
            update_holding(code, name, new_shares, cost_price, price)
            
            # 增加现金
            cash = get_cash()
            set_cash(cash + shares * price)
        else:
            return {'success': False, 'error': f'未知操作: {action}'}
        
        # 记录交易
        add_trade(code, name, action, shares, price, note)
        set_setting('last_rebalance_date', datetime.now().strftime('%Y-%m-%d'))
        
        return {
            'success': True,
            'action': action,
            'code': code,
            'name': name,
            'shares': shares,
            'price': price,
            'amount': shares * price
        }
    
    def calculate_signals(self):
        """计算策略信号（统一走正式回测核心链路）"""
        from daily_task_full import run_daily_task as run_live_task

        result = run_live_task()
        if result is None:
            return {'error': '实盘信号计算失败'}

        if result.get('signals'):
            for sig in result['signals']:
                save_signal({
                    'date': result.get('date', datetime.now().strftime('%Y-%m-%d')),
                    'type': 'rebalance' if result.get('should_rebalance') else 'monitor',
                    'code': sig['code'],
                    'name': sig['name'],
                    'action': sig['action'],
                    'reason': sig['reason']
                })

        return result
    
    def _get_price_dataframe(self):
        """获取价格数据框"""
        import pandas as pd
        
        kline_path = Path('/opt/data/scripts/AkShare/etf_data')
        price_data = {}
        
        for code in self.etf_pool.keys():
            csv_path = kline_path / f"{code}_kline.csv"
            if csv_path.exists():
                try:
                    df = pd.read_csv(csv_path, encoding='utf-8')
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.set_index('date')['close']
                    price_data[code] = df
                except:
                    pass
        
        if price_data:
            return pd.DataFrame(price_data).dropna()
        return None
    
    def _calculate_current_weights(self):
        """计算当前持仓权重"""
        prices = self._get_current_prices()
        holdings = get_holdings()
        cash = get_cash()
        
        total_value = cash
        values = {}
        
        for code, data in holdings.items():
            if data['shares'] > 0:
                value = data['shares'] * prices.get(code, data.get('cost_price', 0))
                values[code] = value
                total_value += value
        
        weights = {}
        for code, value in values.items():
            weights[code] = value / total_value if total_value > 0 else 0
        
        return weights
    
    def update_data(self):
        """更新数据"""
        import subprocess
        result = subprocess.run(
            [sys.executable, '/opt/data/scripts/etf/data_manager.py'],
            capture_output=True,
            text=True
        )
        return result.stdout
    
    def save_signal_file(self, data):
        """保存信号文件（用于推送检测）"""
        with open(SIGNAL_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def check_signal_file(self):
        """检查是否有待推送的信号"""
        if Path(SIGNAL_FILE).exists():
            with open(SIGNAL_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # 读取后删除文件，避免重复推送
            Path(SIGNAL_FILE).unlink()
            return data
        return None


# 命令行入口
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='ETF 策略服务')
    parser.add_argument('command', choices=['summary', 'signals', 'update'], help='执行命令')
    parser.add_argument('--code', help='ETF代码')
    parser.add_argument('--action', choices=['buy', 'sell'], help='交易操作')
    parser.add_argument('--shares', type=float, help='份额')
    parser.add_argument('--price', type=float, help='价格')
    
    args = parser.parse_args()
    
    service = ETFService()
    
    if args.command == 'summary':
        result = service.get_portfolio_summary()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif args.command == 'signals':
        result = service.calculate_signals()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif args.command == 'update':
        output = service.update_data()
        print(output)
