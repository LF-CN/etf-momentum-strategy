# 实盘仓位跟踪脚本使用说明

状态：Active
更新日期：2026-04-16

## 1. 目标

为真实实盘仓位提供一套独立于策略库的录入与维护工具，覆盖：
- 完整持仓快照导入
- 单笔真实交易录入
- 现金变动录入
- 最新快照与最近交易查询

## 2. 关键文件

- 数据库：`/opt/data/scripts/etf/data/live_portfolio.db`
- 脚本：`/opt/data/scripts/etf/live_portfolio_tools.py`
- Schema：`/opt/data/scripts/etf/data/live_portfolio_schema.sql`
- CSV 模板：`/opt/data/scripts/etf/data/live_position_snapshot_template.csv`

## 3. 常用命令

### 3.1 初始化数据库

```bash
python3 /opt/data/scripts/etf/live_portfolio_tools.py init-db
```

### 3.2 从 CSV 导入完整持仓快照

```bash
python3 /opt/data/scripts/etf/live_portfolio_tools.py import-snapshot-csv   --csv /opt/data/scripts/etf/data/live_position_snapshot_template.csv
```

说明：
- 同一 `snapshot_date` 下，如果导入的是完整快照（`is_complete_snapshot=1`），脚本会先删除该日期旧记录，再写入新记录。
- 这样可以避免同一天的持仓快照重复堆积。

### 3.3 录入单笔交易

```bash
python3 /opt/data/scripts/etf/live_portfolio_tools.py add-trade   --date 2026-04-18   --code 511010   --name 国债ETF   --action buy   --shares 300   --price 139.82   --fee 1.2   --note "手工补录"
```

### 3.4 录入现金变动

```bash
python3 /opt/data/scripts/etf/live_portfolio_tools.py add-cash   --date 2026-04-18   --amount 5000   --action deposit   --note "追加资金"
```

### 3.5 查看最新持仓快照

```bash
python3 /opt/data/scripts/etf/live_portfolio_tools.py show-latest
```

### 3.6 查看最近交易

```bash
python3 /opt/data/scripts/etf/live_portfolio_tools.py list-trades --limit 10
```

## 4. 推荐维护方式

### 方式 A：收盘后完整快照
最稳妥，优先推荐。

流程：
1. 复制 `live_position_snapshot_template.csv`
2. 填写当日真实份额、现金、总资产
3. 用 `import-snapshot-csv` 导入
4. 用 `show-latest` 复核

### 方式 B：盘中/盘后补录交易
适合先快速记录成交行为。

流程：
1. 每有真实成交，就用 `add-trade` 补一笔
2. 若有入金/出金，用 `add-cash` 补录
3. 收盘后最好再补一份完整快照，作为当日最终基准口径

## 5. 输出格式

脚本统一输出 JSON，方便：
- 直接人工查看
- 后续接入自动化
- 给 Hermes 继续读入分析

## 6. 维护原则

1. 真实仓位优先于策略样例仓位。
2. 完整收盘快照优先于零散交易记录。
3. 若只有交易记录而没有完整快照，后续分析必须标注为“部分更新口径”。
4. 不删除历史日期，只覆盖同一日期下的完整快照，保留追溯能力。

## 7. 当前支持的命令

- `init-db`
- `import-snapshot-csv`
- `add-trade`
- `add-cash`
- `show-latest`
- `list-trades`

## 8. 下一步可扩展方向

1. 自动根据交易记录推导最新持仓
2. 自动生成“真实仓位 vs 策略目标”偏离表
3. 自动导出周报/月报
4. 接入 Obsidian / CSV / 飞书报表
