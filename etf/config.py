# ETF 动量轮动策略配置

# ETF 资产池（与 Stage6 正式基线一致）
ETF_POOL = {
    '510500': {'name': '中证500ETF', 'category': 'stock', 'base_weight': 0.25, 'style': 'a_share'},
    '159941': {'name': '纳指ETF', 'category': 'stock', 'base_weight': 0.25, 'style': 'us_tech'},
    '518880': {'name': '黄金ETF', 'category': 'gold', 'base_weight': 0.20, 'style': 'commodity'},
    '511010': {'name': '国债ETF', 'category': 'bond', 'base_weight': 0.20, 'style': 'gov_bond'},
    '159928': {'name': '消费ETF', 'category': 'sector', 'base_weight': 0.10, 'style': 'defensive'},
}

# 策略参数（新基线 2026-04-29：双引擎统一，style_factors已移除）
STRATEGY_PARAMS = {
    'initial_capital': 50000.0,        # 当前账户初始本金（实盘账户口径）
    'lookback_period': 30,             # 动量计算回看期（交易日）
    'trigger_deviation': 0.24,         # P3精扫最优
    'signal_weight': 0.2,              # 信号强度权重
    'cooldown_days': 20,               # 调仓冷却期
    'stop_loss_threshold': -0.18,      # 止损阈值
    'top_n': 3,                        # 最大持仓数量
    'transaction_cost': 0.0002,        # 单边交易成本
    'min_trade_amount': 1000,          # 最小交易金额
    'data_start_date': '2016-01-01',   # 数据起点
    'factor_weights': {
        'momentum_20d': 425,
        'momentum_60d': 175,
        'momentum_strength': 200,
        'volatility_reward': 75,
        'r_squared': 30,
    },
}

# 风控参数
RISK_PARAMS = {
    'max_single_weight': 0.325,
    'min_cash_reserve': 500,
}

# 数据库路径
DB_PATH = '/opt/data/scripts/etf/data/etf.db'

# K线数据路径
KLINE_DATA_PATH = '/opt/data/scripts/AkShare/etf_data'

# 日志路径
LOG_PATH = '/opt/data/scripts/etf/logs'

# 信号文件路径（用于推送）
SIGNAL_FILE = '/opt/data/scripts/etf/data/signal.json'

# 推送配置
PUSH_CONFIG = {
    'telegram_chat_id': '2001908191',
}
