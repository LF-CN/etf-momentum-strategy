"""
初始化持仓数据
录入用户的初始持仓信息
"""
import sys
sys.path.insert(0, '/opt/data/scripts/etf')

from database import init_db, update_holding, set_cash, set_initial_capital, get_holdings, get_cash
from config import ETF_POOL


def init_holdings():
    """初始化持仓"""
    # 初始持仓数据（根据用户提供的截图）
    initial_holdings = {
        '510500': {'name': '中证500ETF', 'shares': 1500, 'cost_price': 8.990},
        '159941': {'name': '纳指ETF', 'shares': 11600, 'cost_price': 1.271},
        '511010': {'name': '国债ETF', 'shares': 100, 'cost_price': 140.180},
        '518880': {'name': '黄金ETF', 'shares': 0, 'cost_price': 0},
        '159928': {'name': '消费ETF', 'shares': 0, 'cost_price': 0},
    }
    
    # 录入持仓
    for code, data in initial_holdings.items():
        update_holding(code, data['name'], data['shares'], data['cost_price'])
        print(f"已录入: {data['name']} ({code}) - {data['shares']}份")
    
    # 设置现金
    cash = 6951.0
    set_cash(cash)
    print(f"已录入现金: {cash}元")
    
    # 计算并设置初始本金
    # 持仓市值约 42049.70 + 现金 6951 ≈ 49000.70
    # 但初始投入应该是成本价计算
    total_cost = 0
    for code, data in initial_holdings.items():
        total_cost += data['shares'] * data['cost_price']
    total_cost += cash
    
    set_initial_capital(total_cost)
    print(f"初始本金: {total_cost:.2f}元")


def verify_holdings():
    """验证持仓录入"""
    print("\n=== 当前持仓验证 ===")
    holdings = get_holdings()
    cash = get_cash()
    
    total_value = 0
    for code, data in holdings.items():
        if data['shares'] > 0:
            print(f"{data['name']}: {data['shares']}份, 成本价: {data['cost_price']:.3f}")
            total_value += data['shares'] * data['cost_price']
    
    print(f"\n持仓成本: {total_value:.2f}元")
    print(f"现金: {cash:.2f}元")
    print(f"总资产: {total_value + cash:.2f}元")


if __name__ == '__main__':
    print("开始初始化持仓数据...")
    print("-" * 40)
    init_holdings()
    verify_holdings()
    print("-" * 40)
    print("初始化完成！")
