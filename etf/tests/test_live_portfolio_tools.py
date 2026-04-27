import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path("/opt/data/scripts/etf")
SCRIPT = ROOT / "live_portfolio_tools.py"


def test_init_live_portfolio_db_creates_tables_and_meta(tmp_path):
    sys.path.insert(0, str(ROOT))
    from live_portfolio_tools import init_live_portfolio_db

    db_path = tmp_path / "live_portfolio.db"
    summary = init_live_portfolio_db(db_path)

    assert summary["db_path"] == str(db_path)
    assert "live_position_snapshots" in summary["tables"]
    assert summary["meta"]["schema_version"] == "1"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='live_trades'")
    assert cur.fetchone() == ("live_trades",)
    conn.close()


def test_replace_complete_snapshot_for_same_date(tmp_path):
    sys.path.insert(0, str(ROOT))
    from live_portfolio_tools import init_live_portfolio_db, upsert_position_snapshot_rows, fetch_latest_snapshot

    db_path = tmp_path / "live_portfolio.db"
    init_live_portfolio_db(db_path)

    first_rows = [
        {
            "snapshot_date": "2026-04-16",
            "code": "510500",
            "name": "中证500ETF",
            "shares": 1500,
            "cash": 6951,
            "total_assets": 49687.5,
            "is_complete_snapshot": 1,
        },
        {
            "snapshot_date": "2026-04-16",
            "code": "159941",
            "name": "纳指ETF",
            "shares": 11600,
            "cash": 6951,
            "total_assets": 49687.5,
            "is_complete_snapshot": 1,
        },
    ]
    second_rows = [
        {
            "snapshot_date": "2026-04-16",
            "code": "510500",
            "name": "中证500ETF",
            "shares": 1600,
            "cash": 6000,
            "total_assets": 50000,
            "is_complete_snapshot": 1,
        }
    ]

    upsert_position_snapshot_rows(db_path, first_rows)
    upsert_position_snapshot_rows(db_path, second_rows)

    snapshot = fetch_latest_snapshot(db_path)
    assert snapshot["snapshot_date"] == "2026-04-16"
    assert len(snapshot["positions"]) == 1
    assert snapshot["positions"][0]["code"] == "510500"
    assert snapshot["positions"][0]["shares"] == 1600
    assert snapshot["cash"] == 6000
    assert snapshot["total_assets"] == 50000


def test_record_trade_and_list_recent_trades(tmp_path):
    sys.path.insert(0, str(ROOT))
    from live_portfolio_tools import init_live_portfolio_db, record_trade, list_recent_trades

    db_path = tmp_path / "live_portfolio.db"
    init_live_portfolio_db(db_path)

    record_trade(
        db_path=db_path,
        trade_date="2026-04-18",
        code="511010",
        name="国债ETF",
        action="buy",
        shares=300,
        price=139.82,
        fee=1.2,
        note="第一次测试录入",
    )

    trades = list_recent_trades(db_path, limit=5)
    assert len(trades) == 1
    assert trades[0]["action"] == "buy"
    assert trades[0]["amount"] == 300 * 139.82
    assert trades[0]["fee"] == 1.2


def test_cli_import_snapshot_csv_and_show_latest(tmp_path):
    db_path = tmp_path / "live_portfolio.db"
    csv_path = tmp_path / "snapshot.csv"
    csv_path.write_text(
        "snapshot_date,code,name,shares,cash,total_assets,is_complete_snapshot\n"
        "2026-04-16,510500,中证500ETF,1500,6951,49687.5,1\n"
        "2026-04-16,159941,纳指ETF,11600,6951,49687.5,1\n",
        encoding="utf-8",
    )

    import_result = subprocess.run(
        [sys.executable, str(SCRIPT), "import-snapshot-csv", "--db-path", str(db_path), "--csv", str(csv_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "imported_rows" in import_result.stdout

    show_result = subprocess.run(
        [sys.executable, str(SCRIPT), "show-latest", "--db-path", str(db_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "2026-04-16" in show_result.stdout
    assert "510500" in show_result.stdout
