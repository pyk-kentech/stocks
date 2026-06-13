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

        CREATE TABLE IF NOT EXISTS trade_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            direction TEXT NOT NULL,
            setup_grade TEXT NOT NULL,
            setup_score INTEGER,
            entry_price REAL,
            stop_price REAL,
            target_price REAL,
            risk_reward_ratio REAL,
            max_loss_amount REAL,
            max_loss_currency TEXT,
            position_size REAL,
            notional_value REAL,
            decision TEXT NOT NULL,
            reasons_json TEXT,
            warnings_json TEXT,
            beginner_summary TEXT,
            policy_id TEXT,
            policy_version TEXT,
            setup_scoring_mode TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS basket_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            basket_id TEXT NOT NULL UNIQUE,
            basket_name TEXT NOT NULL,
            mode TEXT NOT NULL,
            policy_json TEXT NOT NULL,
            decision TEXT NOT NULL,
            risk_summary_json TEXT NOT NULL,
            beginner_summary TEXT,
            created_at TEXT NOT NULL,
            policy_id TEXT,
            policy_version TEXT,
            basket_scoring_mode TEXT
        );

        CREATE TABLE IF NOT EXISTS basket_allocations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            basket_id TEXT NOT NULL,
            ticker TEXT NOT NULL,
            setup_grade TEXT NOT NULL,
            allocated_loss_amount REAL,
            allocated_notional_value REAL,
            position_size REAL,
            entry_price REAL,
            stop_price REAL,
            target_price REAL,
            risk_reward_ratio REAL,
            allocation_reason TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS basket_blocked_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            basket_id TEXT NOT NULL,
            ticker TEXT NOT NULL,
            setup_grade TEXT,
            decision TEXT,
            score INTEGER,
            reasons_json TEXT,
            warnings_json TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS paper_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_id TEXT NOT NULL UNIQUE,
            basket_id TEXT NOT NULL,
            ticker TEXT NOT NULL,
            direction TEXT NOT NULL,
            setup_grade TEXT NOT NULL,
            entry_price REAL NOT NULL,
            stop_price REAL NOT NULL,
            target_price REAL,
            position_size REAL NOT NULL,
            allocated_loss_amount REAL NOT NULL,
            notional_value REAL NOT NULL,
            entry_date TEXT NOT NULL,
            exit_date TEXT,
            exit_price REAL,
            exit_reason TEXT,
            realized_pnl REAL,
            realized_return_pct REAL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            policy_id TEXT,
            policy_version TEXT,
            basket_scoring_mode TEXT
        );

        CREATE TABLE IF NOT EXISTS basket_backtest_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            basket_id TEXT NOT NULL,
            horizon_days INTEGER NOT NULL,
            entry_date TEXT NOT NULL,
            exit_date TEXT,
            total_notional_value REAL NOT NULL,
            total_allocated_loss REAL NOT NULL,
            realized_pnl REAL NOT NULL,
            realized_return_pct REAL NOT NULL,
            max_drawdown REAL,
            max_gain REAL,
            win_count INTEGER NOT NULL,
            loss_count INTEGER NOT NULL,
            flat_count INTEGER NOT NULL,
            no_data_count INTEGER NOT NULL,
            closed_trade_count INTEGER NOT NULL,
            outcome TEXT NOT NULL,
            created_at TEXT NOT NULL,
            policy_id TEXT,
            policy_version TEXT,
            basket_scoring_mode TEXT
        );

        CREATE TABLE IF NOT EXISTS strategy_policies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            policy_id TEXT NOT NULL,
            version TEXT NOT NULL,
            status TEXT NOT NULL,
            weights_json TEXT NOT NULL,
            setup_thresholds_json TEXT NOT NULL,
            basket_rules_json TEXT NOT NULL,
            risk_overrides_json TEXT NOT NULL,
            created_by TEXT NOT NULL,
            reason TEXT,
            parent_policy_id TEXT,
            parent_version TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(policy_id, version)
        );

        CREATE TABLE IF NOT EXISTS strategy_experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_id TEXT NOT NULL UNIQUE,
            baseline_policy_id TEXT NOT NULL,
            baseline_version TEXT NOT NULL,
            candidate_policy_id TEXT NOT NULL,
            candidate_version TEXT NOT NULL,
            evaluation_mode TEXT NOT NULL,
            horizon_days INTEGER NOT NULL,
            sample_count INTEGER NOT NULL,
            avg_return_pct REAL,
            median_return_pct REAL,
            win_rate REAL,
            loss_rate REAL,
            profit_factor REAL,
            avg_max_drawdown REAL,
            avg_realized_pnl REAL,
            objective_score REAL NOT NULL,
            recommendation TEXT NOT NULL,
            notes_json TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS strategy_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            memory_id TEXT NOT NULL UNIQUE,
            basket_id TEXT,
            ticker TEXT,
            setup_grade TEXT,
            decision TEXT NOT NULL,
            features_json TEXT NOT NULL,
            outcome TEXT,
            realized_return_pct REAL,
            realized_pnl REAL,
            max_drawdown REAL,
            policy_id TEXT,
            policy_version TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS replay_runs (
            run_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            snapshot_mode TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_basket_id TEXT,
            as_of_date TEXT,
            policy_id TEXT,
            policy_version TEXT,
            notes_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS replay_candidate_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            ticker TEXT NOT NULL,
            source TEXT NOT NULL,
            snapshot_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS replay_trade_plan_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            ticker TEXT NOT NULL,
            trade_plan_id INTEGER,
            decision TEXT NOT NULL,
            snapshot_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS replay_basket_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL UNIQUE,
            basket_id TEXT NOT NULL,
            decision TEXT NOT NULL,
            policy_id TEXT,
            policy_version TEXT,
            scoring_mode TEXT NOT NULL,
            snapshot_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS replay_outcome_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL UNIQUE,
            basket_id TEXT NOT NULL,
            outcome TEXT NOT NULL,
            realized_return_pct REAL NOT NULL,
            snapshot_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS policy_replay_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            policy_replay_id TEXT NOT NULL UNIQUE,
            source_replay_run_id TEXT NOT NULL,
            replay_mode TEXT NOT NULL,
            policy_id TEXT NOT NULL,
            policy_version TEXT NOT NULL,
            as_of_date TEXT NOT NULL,
            horizon_days INTEGER NOT NULL,
            candidate_count INTEGER NOT NULL,
            trade_plan_count INTEGER NOT NULL,
            basket_id TEXT,
            total_notional_value REAL,
            total_allocated_loss REAL,
            realized_pnl REAL,
            realized_return_pct REAL,
            win_count INTEGER,
            loss_count INTEGER,
            no_data_count INTEGER,
            outcome TEXT,
            objective_score REAL,
            status TEXT NOT NULL,
            notes_json TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS policy_comparison_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            comparison_id TEXT NOT NULL UNIQUE,
            source_replay_run_id TEXT NOT NULL,
            baseline_policy_id TEXT NOT NULL,
            baseline_policy_version TEXT NOT NULL,
            candidate_policy_id TEXT NOT NULL,
            candidate_policy_version TEXT NOT NULL,
            baseline_replay_id TEXT,
            candidate_replay_id TEXT,
            baseline_return_pct REAL,
            candidate_return_pct REAL,
            return_delta_pct REAL,
            baseline_objective_score REAL,
            candidate_objective_score REAL,
            objective_delta REAL,
            recommendation TEXT NOT NULL,
            notes_json TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS policy_evaluation_suites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            suite_id TEXT NOT NULL UNIQUE,
            baseline_policy_id TEXT NOT NULL,
            baseline_policy_version TEXT NOT NULL,
            candidate_policy_id TEXT NOT NULL,
            candidate_policy_version TEXT NOT NULL,
            replay_run_count INTEGER NOT NULL,
            completed_pair_count INTEGER NOT NULL,
            no_data_replay_count INTEGER NOT NULL,
            incomplete_pair_count INTEGER NOT NULL,
            baseline_avg_return_pct REAL,
            candidate_avg_return_pct REAL,
            return_delta_pct REAL,
            baseline_avg_objective_score REAL,
            candidate_avg_objective_score REAL,
            objective_delta REAL,
            baseline_win_rate REAL,
            candidate_win_rate REAL,
            win_rate_delta REAL,
            baseline_loss_rate REAL,
            candidate_loss_rate REAL,
            no_data_rate REAL NOT NULL,
            recommendation TEXT NOT NULL,
            result_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS policy_promotion_proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposal_id TEXT NOT NULL UNIQUE,
            suite_id TEXT NOT NULL,
            candidate_policy_id TEXT NOT NULL,
            candidate_policy_version TEXT NOT NULL,
            from_status TEXT NOT NULL,
            proposed_status TEXT NOT NULL,
            recommendation TEXT NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS scan_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_run_id TEXT NOT NULL UNIQUE,
            as_of_date TEXT NOT NULL,
            source TEXT NOT NULL,
            policy_id TEXT,
            policy_version TEXT,
            universe_size INTEGER NOT NULL,
            included_count INTEGER NOT NULL,
            watch_count INTEGER NOT NULL,
            excluded_count INTEGER NOT NULL,
            status TEXT NOT NULL,
            notes_json TEXT,
            run_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS candidate_scan_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_run_id TEXT NOT NULL,
            ticker TEXT NOT NULL,
            as_of_date TEXT NOT NULL,
            decision TEXT NOT NULL,
            score INTEGER NOT NULL,
            setup_grade TEXT,
            setup_score INTEGER,
            trade_plan_decision TEXT,
            price REAL,
            return_1d_pct REAL,
            return_5d_pct REAL,
            return_20d_pct REAL,
            avg_dollar_volume_20d REAL,
            volume_spike_ratio REAL,
            dollar_volume_spike_ratio REAL,
            volatility_20d_pct REAL,
            risk_reward_ratio REAL,
            sector TEXT,
            theme TEXT,
            reasons_json TEXT,
            warnings_json TEXT,
            metadata_json TEXT,
            result_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS ticker_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            as_of_date TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            direction TEXT NOT NULL,
            severity TEXT NOT NULL,
            score_delta INTEGER NOT NULL,
            source_name TEXT NOT NULL,
            title TEXT,
            summary TEXT,
            raw_event_type TEXT,
            metadata_json TEXT,
            reasons_json TEXT,
            warnings_json TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS pipeline_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pipeline_run_id TEXT NOT NULL UNIQUE,
            mode TEXT NOT NULL,
            as_of_date TEXT NOT NULL,
            policy_id TEXT,
            policy_version TEXT,
            scan_run_id TEXT,
            basket_id TEXT,
            replay_run_id TEXT,
            policy_replay_id TEXT,
            evaluation_suite_id TEXT,
            status TEXT NOT NULL,
            candidate_count INTEGER NOT NULL,
            included_count INTEGER NOT NULL,
            watch_count INTEGER NOT NULL,
            basket_allocation_count INTEGER NOT NULL,
            alert_count INTEGER NOT NULL,
            notes_json TEXT,
            error TEXT,
            run_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            completed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS pipeline_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_id TEXT NOT NULL UNIQUE,
            pipeline_run_id TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            ticker TEXT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            metadata_json TEXT,
            alert_json TEXT NOT NULL,
            created_at TEXT NOT NULL
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

        CREATE TABLE IF NOT EXISTS import_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_run_id TEXT NOT NULL UNIQUE,
            as_of_date TEXT,
            status TEXT NOT NULL,
            total_row_count INTEGER NOT NULL,
            total_saved_count INTEGER NOT NULL,
            total_skipped_duplicate_count INTEGER NOT NULL,
            total_error_count INTEGER NOT NULL,
            notes_json TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS import_source_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_run_id TEXT NOT NULL,
            source_type TEXT NOT NULL,
            file_path TEXT NOT NULL,
            row_count INTEGER NOT NULL,
            saved_count INTEGER NOT NULL,
            skipped_duplicate_count INTEGER NOT NULL,
            error_count INTEGER NOT NULL,
            warnings_json TEXT,
            errors_json TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS connector_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            connector_run_id TEXT NOT NULL UNIQUE,
            as_of_date TEXT NOT NULL,
            connector_name TEXT NOT NULL,
            connector_type TEXT NOT NULL,
            mode TEXT NOT NULL,
            status TEXT NOT NULL,
            output_path TEXT,
            row_count INTEGER NOT NULL,
            warnings_json TEXT,
            errors_json TEXT,
            metadata_json TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS normalize_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            normalize_run_id TEXT NOT NULL UNIQUE,
            as_of_date TEXT,
            status TEXT NOT NULL,
            total_row_count INTEGER NOT NULL,
            total_normalized_count INTEGER NOT NULL,
            total_skipped_count INTEGER NOT NULL,
            total_error_count INTEGER NOT NULL,
            output_paths_json TEXT,
            notes_json TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS normalize_source_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            normalize_run_id TEXT NOT NULL,
            normalizer_name TEXT NOT NULL,
            normalizer_type TEXT NOT NULL,
            input_path TEXT NOT NULL,
            output_path TEXT,
            row_count INTEGER NOT NULL,
            normalized_count INTEGER NOT NULL,
            skipped_count INTEGER NOT NULL,
            error_count INTEGER NOT NULL,
            warnings_json TEXT,
            errors_json TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS fx_rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            base_currency TEXT NOT NULL,
            quote_currency TEXT NOT NULL,
            date TEXT NOT NULL,
            rate REAL NOT NULL,
            source_name TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(base_currency, quote_currency, date, source_name)
        );

        CREATE TABLE IF NOT EXISTS provider_pack_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider_pack_run_id TEXT NOT NULL UNIQUE,
            provider_pack_type TEXT NOT NULL,
            as_of_date TEXT NOT NULL,
            status TEXT NOT NULL,
            connector_run_ids_json TEXT,
            normalize_run_id TEXT,
            import_run_id TEXT,
            output_paths_json TEXT,
            warnings_json TEXT,
            errors_json TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS analysis_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id TEXT NOT NULL UNIQUE,
            report_type TEXT NOT NULL,
            source_id TEXT NOT NULL,
            generated_at TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            sections_json TEXT NOT NULL,
            key_metrics_json TEXT,
            warnings_json TEXT,
            disclaimer TEXT,
            context_json TEXT,
            markdown TEXT
        );

        CREATE TABLE IF NOT EXISTS agent_contexts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            context_id TEXT NOT NULL UNIQUE,
            context_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS agent_prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt_id TEXT NOT NULL UNIQUE,
            prompt_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS agent_briefs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brief_id TEXT NOT NULL UNIQUE,
            brief_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS local_llm_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT NOT NULL UNIQUE,
            request_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS local_llm_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            response_id TEXT NOT NULL UNIQUE,
            request_id TEXT NOT NULL,
            response_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS notification_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            notification_run_id TEXT NOT NULL UNIQUE,
            source_type TEXT NOT NULL,
            source_id TEXT NOT NULL,
            channel_type TEXT NOT NULL,
            status TEXT NOT NULL,
            message_count INTEGER NOT NULL,
            delivered_count INTEGER NOT NULL,
            skipped_duplicate_count INTEGER NOT NULL,
            failed_count INTEGER NOT NULL,
            output_path TEXT,
            warnings_json TEXT,
            errors_json TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS notification_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            notification_id TEXT NOT NULL UNIQUE,
            source_type TEXT NOT NULL,
            source_id TEXT NOT NULL,
            channel_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            metadata_json TEXT,
            dedupe_key TEXT NOT NULL,
            created_at TEXT NOT NULL,
            delivered_at TEXT,
            delivery_status TEXT NOT NULL,
            error TEXT
        );
        CREATE TABLE IF NOT EXISTS dashboard_builds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dashboard_id TEXT NOT NULL UNIQUE,
            dashboard_type TEXT NOT NULL,
            as_of_date TEXT,
            source_id TEXT,
            status TEXT NOT NULL,
            output_path TEXT,
            section_count INTEGER NOT NULL,
            warnings_json TEXT,
            errors_json TEXT,
            generated_at TEXT NOT NULL
        );
        """
    )
    _add_missing_columns(
        connection,
        "trade_plans",
        {
            "policy_id": "TEXT",
            "policy_version": "TEXT",
            "setup_scoring_mode": "TEXT",
            "fx_json": "TEXT",
        },
    )
    _add_missing_columns(
        connection,
        "basket_plans",
        {"policy_id": "TEXT", "policy_version": "TEXT", "basket_scoring_mode": "TEXT"},
    )
    _add_missing_columns(
        connection,
        "paper_trades",
        {"policy_id": "TEXT", "policy_version": "TEXT", "basket_scoring_mode": "TEXT", "fx_json": "TEXT"},
    )
    _add_missing_columns(
        connection,
        "basket_backtest_results",
        {"policy_id": "TEXT", "policy_version": "TEXT", "basket_scoring_mode": "TEXT", "fx_json": "TEXT"},
    )
    _add_missing_columns(connection, "basket_allocations", {"fx_json": "TEXT"})
    _add_missing_columns(
        connection,
        "scan_runs",
        {
            "as_of_date": "TEXT",
            "source": "TEXT",
            "policy_id": "TEXT",
            "policy_version": "TEXT",
            "universe_size": "INTEGER",
            "included_count": "INTEGER",
            "watch_count": "INTEGER",
            "excluded_count": "INTEGER",
            "status": "TEXT",
            "notes_json": "TEXT",
        },
    )
    _add_missing_columns(
        connection,
        "candidate_scan_results",
        {
            "as_of_date": "TEXT",
            "score": "INTEGER",
            "setup_grade": "TEXT",
            "setup_score": "INTEGER",
            "trade_plan_decision": "TEXT",
            "price": "REAL",
            "return_1d_pct": "REAL",
            "return_5d_pct": "REAL",
            "return_20d_pct": "REAL",
            "avg_dollar_volume_20d": "REAL",
            "volume_spike_ratio": "REAL",
            "dollar_volume_spike_ratio": "REAL",
            "volatility_20d_pct": "REAL",
            "risk_reward_ratio": "REAL",
            "sector": "TEXT",
            "theme": "TEXT",
            "reasons_json": "TEXT",
            "warnings_json": "TEXT",
            "metadata_json": "TEXT",
        },
    )


def _add_missing_columns(connection: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
    existing = {str(row["name"]) for row in connection.execute(f"PRAGMA table_info({table})")}
    for name, column_type in columns.items():
        if name not in existing:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {column_type}")
