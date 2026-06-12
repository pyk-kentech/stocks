from __future__ import annotations

import sqlite3
from pathlib import Path


DEFAULT_DB_PATH = Path("data") / "stock_risk_mcp.sqlite3"


def connect_db(path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path = Path(path)
    if db_path.parent != Path("."):
        db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(path: str | Path = DEFAULT_DB_PATH) -> None:
    with connect_db(path) as connection:
        create_schema(connection)


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS market_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            price REAL NOT NULL,
            market_cap_usd REAL,
            avg_dollar_volume_20d REAL,
            return_5d_pct REAL,
            return_20d_pct REAL,
            volatility_20d_pct REAL,
            sector TEXT,
            source TEXT NOT NULL DEFAULT 'unknown',
            observed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            raw_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS company_risks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            nasdaq_noncompliant INTEGER NOT NULL,
            dilution_risk TEXT NOT NULL,
            recent_reverse_split_days INTEGER,
            recent_offering_days INTEGER,
            has_warrants INTEGER NOT NULL,
            has_convertibles INTEGER NOT NULL,
            has_going_concern_warning INTEGER NOT NULL,
            source TEXT NOT NULL DEFAULT 'unknown',
            observed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            raw_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS toss_investor_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            tracked_investors_holding INTEGER NOT NULL,
            new_buy_count_7d INTEGER NOT NULL,
            consensus_level TEXT NOT NULL,
            signal_quality TEXT NOT NULL,
            historical_follow_return_30d_pct REAL,
            source TEXT NOT NULL DEFAULT 'unknown',
            observed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            raw_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS news_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            headline TEXT NOT NULL,
            source TEXT,
            published_at TEXT,
            url TEXT,
            sentiment TEXT,
            summary TEXT,
            ingested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            raw_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS risk_evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            decision TEXT NOT NULL,
            score INTEGER NOT NULL,
            max_order_usd REAL NOT NULL,
            max_position_pct REAL NOT NULL,
            market_snapshot_id INTEGER,
            company_risk_id INTEGER,
            toss_investor_snapshot_id INTEGER,
            proposal_json TEXT NOT NULL,
            policy_json TEXT NOT NULL,
            result_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (market_snapshot_id) REFERENCES market_snapshots(id),
            FOREIGN KEY (company_risk_id) REFERENCES company_risks(id),
            FOREIGN KEY (toss_investor_snapshot_id) REFERENCES toss_investor_snapshots(id)
        );

        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL NOT NULL,
            volume REAL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(ticker, date)
        );

        CREATE TABLE IF NOT EXISTS backtest_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            risk_evaluation_id INTEGER NOT NULL,
            ticker TEXT NOT NULL,
            evaluation_created_at TEXT NOT NULL,
            decision TEXT NOT NULL,
            score INTEGER NOT NULL,
            horizon_days INTEGER NOT NULL,
            entry_price REAL NOT NULL,
            exit_price REAL,
            return_pct REAL,
            max_drawdown_pct REAL,
            max_gain_pct REAL,
            outcome TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (risk_evaluation_id) REFERENCES risk_evaluations(id)
        );

        CREATE TABLE IF NOT EXISTS evaluation_reasons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            risk_evaluation_id INTEGER NOT NULL,
            ticker TEXT NOT NULL,
            reason_type TEXT NOT NULL,
            reason_code TEXT NOT NULL,
            message TEXT NOT NULL,
            severity TEXT NOT NULL,
            source_name TEXT,
            source_type TEXT,
            source_url TEXT,
            observed_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            raw_reference TEXT,
            confidence REAL,
            FOREIGN KEY (risk_evaluation_id) REFERENCES risk_evaluations(id)
        );

        CREATE TABLE IF NOT EXISTS compliance_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            company_name TEXT,
            issue TEXT,
            deficiency TEXT,
            notice_date TEXT,
            source_name TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_url TEXT,
            raw_reference TEXT,
            observed_at TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS indicator_values (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            indicator_code TEXT NOT NULL,
            category TEXT NOT NULL,
            value_json TEXT,
            unit TEXT,
            signal TEXT NOT NULL,
            severity TEXT NOT NULL,
            interpretation TEXT,
            beginner_explanation TEXT,
            source_name TEXT,
            source_type TEXT,
            observed_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS data_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            source_type TEXT NOT NULL,
            description TEXT,
            base_url TEXT,
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS ingestion_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name TEXT NOT NULL,
            source_type TEXT NOT NULL,
            started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            finished_at TEXT,
            status TEXT NOT NULL,
            records_seen INTEGER DEFAULT 0,
            records_saved INTEGER DEFAULT 0,
            error_message TEXT,
            metadata_json TEXT
        );
        """
    )
