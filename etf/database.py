"""
ETF 策略系统数据库管理
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

from config import DB_PATH


def get_db():
    """获取数据库连接"""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db_context():
    """数据库连接上下文管理器"""
    conn = get_db()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """初始化数据库表"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        
        # 持仓表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS holdings (
                code TEXT PRIMARY KEY,
                name TEXT,
                shares REAL NOT NULL DEFAULT 0,
                cost_price REAL,
                current_price REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 交易记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                name TEXT,
                action TEXT NOT NULL,
                shares REAL NOT NULL,
                price REAL NOT NULL,
                amount REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                note TEXT
            )
        ''')
        
        # 净值记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nav_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                total_value REAL NOT NULL,
                cash REAL NOT NULL,
                holdings_value REAL NOT NULL,
                daily_return REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 调仓信号表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                type TEXT NOT NULL,
                code TEXT,
                name TEXT,
                action TEXT,
                shares REAL,
                reason TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP
            )
        ''')
        
        # 系统设置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_nav_date ON nav_history(date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_date ON signals(date)')


# ==================== 持仓管理 ====================

def get_holdings():
    """获取当前持仓"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM holdings WHERE shares > 0')
        rows = cursor.fetchall()
        return {row['code']: dict(row) for row in rows}


def update_holding(code, name, shares, cost_price=None, current_price=None):
    """更新持仓"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO holdings (code, name, shares, cost_price, current_price, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(code) DO UPDATE SET
                shares = excluded.shares,
                name = excluded.name,
                cost_price = COALESCE(excluded.cost_price, holdings.cost_price),
                current_price = COALESCE(excluded.current_price, holdings.current_price),
                updated_at = CURRENT_TIMESTAMP
        ''', (code, name, shares, cost_price, current_price))


def get_cash():
    """获取剩余现金"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'cash'")
        row = cursor.fetchone()
        return float(row['value']) if row else 0.0


def set_cash(amount):
    """设置剩余现金"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO settings (key, value, updated_at)
            VALUES ('cash', ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
        ''', (str(amount),))


def get_initial_capital():
    """获取初始本金"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'initial_capital'")
        row = cursor.fetchone()
        return float(row['value']) if row else 0.0


def set_initial_capital(amount):
    """设置初始本金"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO settings (key, value, updated_at)
            VALUES ('initial_capital', ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
        ''', (str(amount),))


def get_setting(key, default=None):
    """读取任意系统设置"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        row = cursor.fetchone()
        return row['value'] if row else default


def set_setting(key, value):
    """写入任意系统设置"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
        ''', (key, str(value)))


# ==================== 交易记录 ====================

def add_trade(code, name, action, shares, price, note=None):
    """添加交易记录"""
    amount = shares * price
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO trades (code, name, action, shares, price, amount, note)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (code, name, action, shares, price, amount, note))


def get_trades(limit=20):
    """获取交易记录"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM trades ORDER BY created_at DESC LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]


# ==================== 净值记录 ====================

def save_nav(date, total_value, cash, holdings_value):
    """保存净值记录"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        # 计算日收益
        cursor.execute('''
            SELECT total_value FROM nav_history ORDER BY date DESC LIMIT 1
        ''')
        row = cursor.fetchone()
        daily_return = 0.0
        if row and row['total_value'] > 0:
            daily_return = (total_value - row['total_value']) / row['total_value']
        
        cursor.execute('''
            INSERT INTO nav_history (date, total_value, cash, holdings_value, daily_return)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                total_value = excluded.total_value,
                cash = excluded.cash,
                holdings_value = excluded.holdings_value,
                daily_return = excluded.daily_return
        ''', (date, total_value, cash, holdings_value, daily_return))


def get_latest_nav():
    """获取最新净值"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM nav_history ORDER BY date DESC LIMIT 1')
        row = cursor.fetchone()
        return dict(row) if row else None


def get_nav_history(days=30):
    """获取净值历史"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM nav_history ORDER BY date DESC LIMIT ?
        ''', (days,))
        return [dict(row) for row in cursor.fetchall()]


# ==================== 信号管理 ====================

def save_signal(signal_data):
    """保存信号"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO signals (date, type, code, name, action, shares, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            signal_data.get('date'),
            signal_data.get('type'),
            signal_data.get('code'),
            signal_data.get('name'),
            signal_data.get('action'),
            signal_data.get('shares'),
            signal_data.get('reason')
        ))


def get_pending_signals():
    """获取待处理信号"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM signals WHERE status = 'pending' ORDER BY created_at DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]


def process_signal(signal_id, status):
    """处理信号"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE signals SET status = ?, processed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (status, signal_id))


# 初始化数据库
init_db()
