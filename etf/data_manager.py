"""
ETF 数据管理模块
负责数据获取、更新、缓存
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json
import sys

sys.path.insert(0, '/opt/data/scripts/AkShare')
from pqquotation import use

from config import ETF_POOL, KLINE_DATA_PATH


class DataManager:
    """ETF 数据管理器"""
    
    def __init__(self):
        self.kline_path = Path(KLINE_DATA_PATH)
        self.kline_path.mkdir(parents=True, exist_ok=True)
    
    def fetch_kline(self, code, days=60):
        """
        获取 ETF K 线数据
        
        Args:
            code: ETF 代码
            days: 获取天数
        
        Returns:
            DataFrame: K线数据
        """
        try:
            # 尝试东方财富数据源
            q = use('eastmoney_kline')
            data = q.real(code, day=days)
            
            if data and code in data:
                klines = data[code]
                df = pd.DataFrame(klines, columns=[
                    'date', 'open', 'close', 'high', 'low', 
                    'volume', 'amount', 'amplitude', 'pct_change', 'change', 'turnover'
                ])
                df['date'] = pd.to_datetime(df['date'])
                df['close'] = pd.to_numeric(df['close'], errors='coerce')
                df = df.sort_values('date').reset_index(drop=True)
                return df
        except Exception as e:
            print(f"东方财富数据源失败: {e}")
        
        try:
            # 尝试腾讯数据源
            q = use('tencent_kline')
            data = q.real(code, day=days)
            
            if data and code in data:
                klines = data[code]
                df = pd.DataFrame(klines, columns=[
                    'date', 'open', 'close', 'high', 'low', 'volume'
                ])
                df['date'] = pd.to_datetime(df['date'])
                df['close'] = pd.to_numeric(df['close'], errors='coerce')
                df = df.sort_values('date').reset_index(drop=True)
                return df
        except Exception as e:
            print(f"腾讯数据源失败: {e}")
        
        return None
    
    def get_cached_kline(self, code):
        """获取缓存的 K 线数据"""
        csv_path = self.kline_path / f"{code}_kline.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path, encoding='utf-8')
            df['date'] = pd.to_datetime(df['date'])
            return df
        return None
    
    def save_kline(self, code, df):
        """保存 K 线数据到缓存"""
        csv_path = self.kline_path / f"{code}_kline.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8')
    
    def update_kline(self, code, force=False):
        """
        更新单个 ETF 的 K 线数据
        
        Args:
            code: ETF 代码
            force: 是否强制更新
        
        Returns:
            bool: 是否更新成功
        """
        cached = self.get_cached_kline(code)
        
        if cached is not None and not force:
            last_date = cached['date'].max()
            today = datetime.now()
            
            # 如果数据是最新的（今天已更新），跳过
            if last_date.date() >= today.date() - timedelta(days=1):
                return True
        
        # 获取新数据
        df = self.fetch_kline(code, days=500)  # 获取足够多的历史数据
        
        if df is not None and len(df) > 0:
            if cached is not None:
                # 合并数据
                df = pd.concat([cached, df]).drop_duplicates(subset=['date'], keep='last')
                df = df.sort_values('date').reset_index(drop=True)
            
            self.save_kline(code, df)
            print(f"✓ {ETF_POOL.get(code, {}).get('name', code)} 数据已更新，共 {len(df)} 条")
            return True
        else:
            print(f"✗ {ETF_POOL.get(code, {}).get('name', code)} 数据更新失败")
            return False
    
    def update_all(self, force=False):
        """更新所有 ETF 数据"""
        print(f"\n=== ETF 数据更新 ({datetime.now().strftime('%Y-%m-%d %H:%M')}) ===")
        
        success_count = 0
        for code in ETF_POOL.keys():
            if self.update_kline(code, force):
                success_count += 1
        
        print(f"\n更新完成: {success_count}/{len(ETF_POOL)}")
        return success_count == len(ETF_POOL)
    
    def get_latest_prices(self):
        """获取所有 ETF 最新价格"""
        prices = {}
        for code in ETF_POOL.keys():
            df = self.get_cached_kline(code)
            if df is not None and len(df) > 0:
                latest = df.iloc[-1]
                prices[code] = {
                    'price': float(latest['close']),
                    'date': latest['date'].strftime('%Y-%m-%d')
                }
        return prices
    
    def get_price_dataframe(self, start_date=None, end_date=None):
        """
        获取价格数据框
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            DataFrame: 价格数据（日期为索引，ETF代码为列）
        """
        price_data = {}
        
        for code in ETF_POOL.keys():
            df = self.get_cached_kline(code)
            if df is not None:
                df = df.set_index('date')['close']
                if start_date:
                    df = df[df.index >= pd.to_datetime(start_date)]
                if end_date:
                    df = df[df.index <= pd.to_datetime(end_date)]
                price_data[code] = df
        
        return pd.DataFrame(price_data)


# 测试
if __name__ == '__main__':
    dm = DataManager()
    dm.update_all()
    
    print("\n最新价格:")
    prices = dm.get_latest_prices()
    for code, data in prices.items():
        name = ETF_POOL.get(code, {}).get('name', code)
        print(f"  {name}: {data['price']:.3f} ({data['date']})")
