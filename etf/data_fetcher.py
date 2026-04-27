"""
ETF 数据获取模块（轻量级版本）
直接使用 HTTP 请求获取数据，无需 pandas/numpy 依赖
"""
import urllib.request
import json
import sqlite3
from datetime import datetime
from pathlib import Path

# 配置
DB_PATH = Path('/opt/data/scripts/etf/data/etf.db')

ETF_POOL = {
    '510500': {'name': '中证500ETF', 'market': 'sh'},
    '159941': {'name': '纳指ETF', 'market': 'sz'},
    '511010': {'name': '国债ETF', 'market': 'sh'},
    '518880': {'name': '黄金ETF', 'market': 'sh'},
    '159928': {'name': '消费ETF', 'market': 'sz'},
}


def get_etf_price(code, retry=3):
    """
    获取 ETF 实时价格（使用新浪财经 API）
    
    Args:
        code: ETF 代码
        retry: 重试次数
    
    Returns:
        dict: {code, name, price, pct_change, date} 或 None
    """
    # 根据代码判断市场
    if code.startswith('51') or code.startswith('58') or code.startswith('511'):
        full_code = f'sh{code}'  # 上交所
    else:
        full_code = f'sz{code}'  # 深交所
    
    url = f'https://hq.sinajs.cn/list={full_code}'
    
    for attempt in range(retry):
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0',
                'Referer': 'https://finance.sina.com.cn'
            })
            with urllib.request.urlopen(req, timeout=10) as response:
                text = response.read().decode('gbk')
                # 解析: var hq_str_sh510500="中证500ETF,8.990,9.070,..."
                if '=' in text and '"' in text:
                    data_str = text.split('"')[1]
                    parts = data_str.split(',')
                    if len(parts) >= 4:
                        name = parts[0]
                        price = float(parts[3]) if parts[3] else 0
                        last_close = float(parts[2]) if parts[2] else 0
                        pct_change = ((price - last_close) / last_close * 100) if last_close > 0 else 0
                        date = datetime.now().strftime('%Y-%m-%d')
                        return {
                            'code': code,
                            'name': name,
                            'price': price,
                            'pct_change': round(pct_change, 2),
                            'date': date
                        }
        except Exception as e:
            if attempt < retry - 1:
                import time
                time.sleep(1)
                continue
            print(f'获取 {code} 价格失败: {e}')
    
    return None


def get_all_prices():
    """获取所有 ETF 最新价格"""
    prices = {}
    print('正在获取 ETF 行情...')
    
    for code in ETF_POOL.keys():
        info = get_etf_price(code)
        if info:
            prices[code] = info
            print(f"  ✓ {info['name']}: {info['price']:.3f} ({info['pct_change']:+.2f}%)")
        else:
            print(f"  ✗ {ETF_POOL[code]['name']}: 获取失败")
    
    return prices


def update_prices_to_db():
    """更新价格到数据库"""
    prices = get_all_prices()
    
    if not prices:
        print('没有获取到任何价格数据')
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    updated = 0
    for code, data in prices.items():
        # 更新 holdings 表的 current_price
        cursor.execute('''
            UPDATE holdings 
            SET current_price = ?, updated_at = ?
            WHERE code = ?
        ''', (data['price'], datetime.now().strftime('%Y-%m-%d %H:%M:%S'), code))
        
        updated += 1
    
    conn.commit()
    conn.close()
    
    print(f'\n已更新 {updated} 个 ETF 的价格数据')
    return True


def update_single_price(code):
    """更新单个 ETF 价格"""
    info = get_etf_price(code)
    if not info:
        return None
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 更新 holdings 表的 current_price
    cursor.execute('''
        UPDATE holdings 
        SET current_price = ?, updated_at = ?
        WHERE code = ?
    ''', (info['price'], datetime.now().strftime('%Y-%m-%d %H:%M:%S'), code))
    
    # 插入 nav_history
    cursor.execute('''
        INSERT OR REPLACE INTO nav_history (code, date, nav, pct_change)
        VALUES (?, ?, ?, ?)
    ''', (code, info['date'], info['price'], info['pct_change']))
    
    conn.commit()
    conn.close()
    
    return info


# 测试
if __name__ == '__main__':
    update_prices_to_db()
