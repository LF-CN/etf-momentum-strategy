# ETF 动量轮动策略配置

# ETF 资产池（与 Stage6 正式基线一致）
ETF_POOL = {
    '510500': {'name': '中证500ETF', 'category': 'stock', 'base_weight': 0.25, 'style': 'a_share'},
    '159941': {'name': '纳指ETF', 'category': 'stock', 'base_weight': 0.25, 'style': 'us_tech'},
    '518880': {'name': '黄金ETF', 'category': 'gold', 'base_weight': 0.20, 'style': 'commodity'},
    '511010': {'name': '国债ETF', 'category': 'bond', 'base_weight': 0.20, 'style': 'gov_bond'},
    '159928': {'name': '消费ETF', 'category': 'sector', 'base_weight': 0.10, 'style': 'defensive'},
}

# 策略参数（Stage7 P1-P5 全验证通过新基线 2026-04-27）
STRATEGY_PARAMS = {
    'initial_capital': 50000.0,        # 当前账户初始本金（实盘账户口径）
    'lookback_period': 30,             # 动量计算回看期（交易日）
    'trigger_deviation': 0.24,         # P3精扫最优：0.24比0.25多捕获一次调仓且不增回撤
    'signal_weight': 0.2,              # 信号强度权重
    'cooldown_days': 20,               # 调仓冷却期（交易日条数口径）
    'stop_loss_threshold': -0.18,      # 止损阈值
    'top_n': 3,                        # 最大持仓数量
    'transaction_cost': 0.0002,        # 单边交易成本
    'min_trade_amount': 1000,          # 最小交易金额（元）
    'data_start_date': '2016-01-01',   # 与正式回测主线对齐的数据起点
    'factor_weights': {
        'momentum_20d': 425,           # P2网格最优：400→425，短期动量更敏感
        'momentum_60d': 175,           # P2网格最优：150→175，与m20d协同
        'momentum_strength': 200,      # P1确认：150~250无明显差异，保持200
        'volatility_reward': 75,       # P2网格最优：50→75，回撤改善1.28%
        'r_squared': 30,              # 保持30不变；rsq=15后半段夏普降至0.847
    },
    'style_factors': {
        'small_cap': 1.0,
        'growth': 1.0,
        'mid_cap': 1.0,
        'large_cap': 1.0,
        'tech': 1.0,
        'cyclical': 1.0,
        'defensive': 1.0,
        'gov_bond': 1.0,
        'convertible': 1.0,
        'commodity': 1.0,
        'a_share': 1.0,
        'us_tech': 1.0,
    },
}

# 风控参数（Stage7 P1-P5 全验证通过新基线 2026-04-27）
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
