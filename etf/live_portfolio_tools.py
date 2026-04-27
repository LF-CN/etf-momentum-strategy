#!/usr/bin/env python3
"""实盘仓位跟踪库维护工具。"""
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from pathlib import Path
from typing import Iterable

DEFAULT_DB_PATH = Path('/opt/data/scripts/etf/data/etf.db')
DEFAULT_SCHEMA_VERSION = '1'

ALLOWED_TRADE_ACTIONS = {
    'buy', 'sell', 'transfer_in', 'transfer_out', 'dividend', 'cash_adjust'
}
ALLOWED_CASH_ACTIONS = {
    'deposit', 'withdraw', 'dividend', 'fee_adjust', 'manual_adjust'
}

SCHEMA_SQL = '''
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS live_position_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_date TEXT NOT NULL,
    code TEXT NOT NULL,
    name TEXT,
    shares REAL NOT NULL DEFAULT 0,
    cost_price REAL,
    close_price REAL,
    market_value REAL,
    weight_pct REAL,
    cash REAL,
    total_assets REAL,
    is_complete_snapshot INTEGER NOT NULL DEFAULT 1,
    source TEXT NOT NULL DEFAULT 'user_report',
    note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_live_snapshots_date
ON live_position_snapshots(snapshot_date);

CREATE INDEX IF NOT EXISTS idx_live_snapshots_date_code
ON live_position_snapshots(snapshot_date, code);

CREATE TABLE IF NOT EXISTS live_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date TEXT NOT NULL,
    code TEXT NOT NULL,
    name TEXT,
    action TEXT NOT NULL,
    shares REAL NOT NULL,
    price REAL,
    amount REAL,
    fee REAL,
    side_note TEXT,
    source TEXT NOT NULL DEFAULT 'user_report',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK(action IN ('buy', 'sell', 'transfer_in', 'transfer_out', 'dividend', 'cash_adjust'))
);

CREATE INDEX IF NOT EXISTS idx_live_trades_date
ON live_trades(trade_date);

CREATE INDEX IF NOT EXISTS idx_live_trades_date_code
ON live_trades(trade_date, code);

CREATE TABLE IF NOT EXISTS live_cash_journal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    journal_date TEXT NOT NULL,
    amount REAL NOT NULL,
    action TEXT NOT NULL,
    note TEXT,
    source TEXT NOT NULL DEFAULT 'user_report',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK(action IN ('deposit', 'withdraw', 'dividend', 'fee_adjust', 'manual_adjust'))
);

CREATE INDEX IF NOT EXISTS idx_live_cash_journal_date
ON live_cash_journal(journal_date);

CREATE TABLE IF NOT EXISTS live_tracking_meta (
    meta_key TEXT PRIMARY KEY,
    meta_value TEXT NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
'''


def _resolve_db_path(db_path: str | Path | None) -> Path:
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connect(db_path: str | Path | None) -> sqlite3.Connection:
    conn = sqlite3.connect(_resolve_db_path(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _to_float(value):
    if value in (None, ''):
        return None
    return float(value)


def _to_int(value, default=0):
    if value in (None, ''):
        return default
    return int(float(value))


def init_live_portfolio_db(db_path: str | Path | None = None) -> dict:
    path = _resolve_db_path(db_path)
    with _connect(path) as conn:
        cur = conn.cursor()
        cur.executescript(SCHEMA_SQL)
        meta = {
            'schema_version': DEFAULT_SCHEMA_VERSION,
            'owner': 'Mr.P',
            'scope': '真实实盘仓位、调仓记录与现金变动跟踪',
            'canonical_rule': '后续分析优先以用户亲自提供的真实仓位为准',
        }
        for key, value in meta.items():
            cur.execute(
                '''
                INSERT INTO live_tracking_meta(meta_key, meta_value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(meta_key) DO UPDATE SET
                    meta_value = excluded.meta_value,
                    updated_at = CURRENT_TIMESTAMP
                ''',
                (key, value),
            )
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
        tables = [row['name'] for row in cur.fetchall()]
    return {'db_path': str(path), 'tables': tables, 'meta': meta}


def upsert_position_snapshot_rows(db_path: str | Path | None, rows: Iterable[dict]) -> dict:
    rows = list(rows)
    if not rows:
        raise ValueError('snapshot rows cannot be empty')

    init_live_portfolio_db(db_path)
    snapshot_date = rows[0]['snapshot_date']
    if any(row.get('snapshot_date') != snapshot_date for row in rows):
        raise ValueError('all snapshot rows must use the same snapshot_date')

    replace_existing = any(_to_int(row.get('is_complete_snapshot'), 1) == 1 for row in rows)

    with _connect(db_path) as conn:
        cur = conn.cursor()
        if replace_existing:
            cur.execute('DELETE FROM live_position_snapshots WHERE snapshot_date = ?', (snapshot_date,))

        inserted = 0
        for row in rows:
            cur.execute(
                '''
                INSERT INTO live_position_snapshots (
                    snapshot_date, code, name, shares, cost_price, close_price,
                    market_value, weight_pct, cash, total_assets,
                    is_complete_snapshot, source, note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    row['snapshot_date'],
                    row['code'],
                    row.get('name'),
                    float(row.get('shares', 0) or 0),
                    _to_float(row.get('cost_price')),
                    _to_float(row.get('close_price')),
                    _to_float(row.get('market_value')),
                    _to_float(row.get('weight_pct')),
                    _to_float(row.get('cash')),
                    _to_float(row.get('total_assets')),
                    _to_int(row.get('is_complete_snapshot'), 1),
                    row.get('source') or 'user_report',
                    row.get('note'),
                ),
            )
            inserted += 1

    return {
        'snapshot_date': snapshot_date,
        'imported_rows': inserted,
        'replaced_existing_for_date': replace_existing,
    }


def import_snapshot_csv(db_path: str | Path | None, csv_path: str | Path) -> dict:
    csv_path = Path(csv_path)
    with csv_path.open('r', encoding='utf-8-sig', newline='') as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise ValueError(f'CSV is empty: {csv_path}')
    result = upsert_position_snapshot_rows(db_path, rows)
    result['csv_path'] = str(csv_path)
    return result


def fetch_latest_snapshot(db_path: str | Path | None = None) -> dict | None:
    init_live_portfolio_db(db_path)
    with _connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute('SELECT MAX(snapshot_date) AS snapshot_date FROM live_position_snapshots')
        row = cur.fetchone()
        snapshot_date = row['snapshot_date'] if row else None
        if not snapshot_date:
            return None
        cur.execute(
            '''
            SELECT snapshot_date, code, name, shares, cost_price, close_price, market_value,
                   weight_pct, cash, total_assets, is_complete_snapshot, source, note, created_at
            FROM live_position_snapshots
            WHERE snapshot_date = ?
            ORDER BY code
            ''',
            (snapshot_date,),
        )
        positions = [dict(r) for r in cur.fetchall()]

    first = positions[0]
    return {
        'snapshot_date': snapshot_date,
        'cash': first.get('cash'),
        'total_assets': first.get('total_assets'),
        'is_complete_snapshot': first.get('is_complete_snapshot'),
        'positions': positions,
    }


def record_trade(
    db_path: str | Path | None,
    trade_date: str,
    code: str,
    action: str,
    shares: float,
    price: float | None = None,
    amount: float | None = None,
    fee: float | None = 0,
    note: str | None = None,
    name: str | None = None,
    source: str = 'user_report',
) -> dict:
    if action not in ALLOWED_TRADE_ACTIONS:
        raise ValueError(f'unsupported trade action: {action}')
    shares = float(shares)
    price = _to_float(price)
    amount = _to_float(amount)
    fee = _to_float(fee)
    if amount is None:
        amount = shares * price if price is not None else None

    init_live_portfolio_db(db_path)
    with _connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            '''
            INSERT INTO live_trades (trade_date, code, name, action, shares, price, amount, fee, side_note, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (trade_date, code, name, action, shares, price, amount, fee, note, source),
        )
        trade_id = cur.lastrowid

    return {
        'id': trade_id,
        'trade_date': trade_date,
        'code': code,
        'name': name,
        'action': action,
        'shares': shares,
        'price': price,
        'amount': amount,
        'fee': fee,
        'note': note,
        'source': source,
    }


def list_recent_trades(db_path: str | Path | None = None, limit: int = 20) -> list[dict]:
    init_live_portfolio_db(db_path)
    with _connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            '''
            SELECT id, trade_date, code, name, action, shares, price, amount, fee, side_note, source, created_at
            FROM live_trades
            ORDER BY trade_date DESC, id DESC
            LIMIT ?
            ''',
            (int(limit),),
        )
        rows = [dict(r) for r in cur.fetchall()]
    for row in rows:
        row['note'] = row.pop('side_note')
    return rows


def record_cash_journal(
    db_path: str | Path | None,
    journal_date: str,
    amount: float,
    action: str,
    note: str | None = None,
    source: str = 'user_report',
) -> dict:
    if action not in ALLOWED_CASH_ACTIONS:
        raise ValueError(f'unsupported cash action: {action}')
    init_live_portfolio_db(db_path)
    with _connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            '''
            INSERT INTO live_cash_journal (journal_date, amount, action, note, source)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (journal_date, float(amount), action, note, source),
        )
        journal_id = cur.lastrowid
    return {
        'id': journal_id,
        'journal_date': journal_date,
        'amount': float(amount),
        'action': action,
        'note': note,
        'source': source,
    }


def _normalize_cli_argv(argv: list[str] | None) -> list[str] | None:
    if argv is None:
        return None
    args = list(argv)
    if '--db-path' not in args:
        return args
    idx = args.index('--db-path')
    if idx == 0:
        return args
    if idx + 1 >= len(args):
        return args
    db_args = args[idx:idx + 2]
    remaining = args[:idx] + args[idx + 2:]
    return db_args + remaining


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='ETF 实盘仓位跟踪库维护工具')
    parser.add_argument('--db-path', default=str(DEFAULT_DB_PATH), help='SQLite 数据库路径')
    subparsers = parser.add_subparsers(dest='command', required=True)

    subparsers.add_parser('init-db', help='初始化实盘跟踪数据库')

    import_csv = subparsers.add_parser('import-snapshot-csv', help='从 CSV 导入完整持仓快照')
    import_csv.add_argument('--csv', required=True, help='CSV 文件路径')

    add_trade = subparsers.add_parser('add-trade', help='录入一笔真实交易')
    add_trade.add_argument('--date', required=True, help='交易日期 YYYY-MM-DD')
    add_trade.add_argument('--code', required=True)
    add_trade.add_argument('--name')
    add_trade.add_argument('--action', required=True, choices=sorted(ALLOWED_TRADE_ACTIONS))
    add_trade.add_argument('--shares', required=True, type=float)
    add_trade.add_argument('--price', type=float)
    add_trade.add_argument('--amount', type=float)
    add_trade.add_argument('--fee', type=float, default=0.0)
    add_trade.add_argument('--note')

    add_cash = subparsers.add_parser('add-cash', help='录入现金变动')
    add_cash.add_argument('--date', required=True, help='日期 YYYY-MM-DD')
    add_cash.add_argument('--amount', required=True, type=float)
    add_cash.add_argument('--action', required=True, choices=sorted(ALLOWED_CASH_ACTIONS))
    add_cash.add_argument('--note')

    show_latest = subparsers.add_parser('show-latest', help='显示最新持仓快照')
    show_latest.add_argument('--pretty', action='store_true', help='美化 JSON 输出')

    list_trades_parser = subparsers.add_parser('list-trades', help='列出最近交易')
    list_trades_parser.add_argument('--limit', type=int, default=20)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    normalized_argv = _normalize_cli_argv(raw_argv)
    args = parser.parse_args(normalized_argv)
    db_path = args.db_path

    if args.command == 'init-db':
        payload = init_live_portfolio_db(db_path)
    elif args.command == 'import-snapshot-csv':
        payload = import_snapshot_csv(db_path, args.csv)
    elif args.command == 'add-trade':
        payload = record_trade(
            db_path=db_path,
            trade_date=args.date,
            code=args.code,
            name=args.name,
            action=args.action,
            shares=args.shares,
            price=args.price,
            amount=args.amount,
            fee=args.fee,
            note=args.note,
        )
    elif args.command == 'add-cash':
        payload = record_cash_journal(
            db_path=db_path,
            journal_date=args.date,
            amount=args.amount,
            action=args.action,
            note=args.note,
        )
    elif args.command == 'show-latest':
        payload = fetch_latest_snapshot(db_path) or {'message': 'no snapshots found'}
    elif args.command == 'list-trades':
        payload = {'trades': list_recent_trades(db_path, limit=args.limit)}
    else:
        parser.error(f'unknown command: {args.command}')
        return 2

    indent = 2 if getattr(args, 'pretty', False) else None
    print(json.dumps(payload, ensure_ascii=False, indent=indent, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
