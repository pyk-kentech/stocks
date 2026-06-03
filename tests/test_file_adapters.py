from __future__ import annotations

import csv
import json

from stock_risk_mcp.adapters.file_company_risk import FileCompanyRiskAdapter
from stock_risk_mcp.adapters.file_market_data import FileMarketDataAdapter
from stock_risk_mcp.adapters.file_news import FileNewsAdapter
from stock_risk_mcp.adapters.file_toss_signal import FileTossSignalAdapter
from stock_risk_mcp.cli import main
from stock_risk_mcp.models import Decision
from stock_risk_mcp.repository import RiskRepository


def test_file_adapters_load_json_and_csv(tmp_path) -> None:
    market_file = tmp_path / "market.json"
    market_file.write_text(
        json.dumps(
            [
                {
                    "ticker": "FILE",
                    "price": 10,
                    "market_cap_usd": 1000000000,
                    "avg_dollar_volume_20d": 60000000,
                    "return_5d_pct": 2,
                    "return_20d_pct": 5,
                    "volatility_20d_pct": 2.5,
                    "sector": "Technology",
                }
            ]
        ),
        encoding="utf-8",
    )
    company_file = tmp_path / "company.csv"
    with company_file.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "ticker",
                "nasdaq_noncompliant",
                "dilution_risk",
                "recent_reverse_split_days",
                "recent_offering_days",
                "has_warrants",
                "has_convertibles",
                "has_going_concern_warning",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "ticker": "FILE",
                "nasdaq_noncompliant": "false",
                "dilution_risk": "LOW",
                "recent_reverse_split_days": "",
                "recent_offering_days": "",
                "has_warrants": "false",
                "has_convertibles": "false",
                "has_going_concern_warning": "false",
            }
        )
    toss_file = tmp_path / "toss.json"
    toss_file.write_text(
        json.dumps(
            [
                {
                    "ticker": "FILE",
                    "tracked_investors_holding": 12,
                    "new_buy_count_7d": 4,
                    "consensus_level": "HIGH",
                    "signal_quality": "HIGH",
                    "historical_follow_return_30d_pct": 6,
                }
            ]
        ),
        encoding="utf-8",
    )

    assert FileMarketDataAdapter(market_file).get_market_snapshot("FILE").sector == "Technology"
    assert FileCompanyRiskAdapter(company_file).get_company_risk("FILE").dilution_risk == "LOW"
    assert FileTossSignalAdapter(toss_file).get_toss_signal("FILE").tracked_investors_holding == 12


def test_evaluate_and_save_cli_persists_file_adapter_rows(tmp_path, capsys) -> None:
    db_path = tmp_path / "risk.sqlite3"
    market_file = tmp_path / "market.json"
    company_file = tmp_path / "company.json"
    toss_file = tmp_path / "toss.json"
    news_file = tmp_path / "news.json"

    market_file.write_text(
        json.dumps(
            [
                {
                    "ticker": "FILE",
                    "price": 10,
                    "market_cap_usd": 1000000000,
                    "avg_dollar_volume_20d": 60000000,
                    "return_5d_pct": 2,
                    "return_20d_pct": 5,
                    "volatility_20d_pct": 2.5,
                    "sector": "Technology",
                }
            ]
        ),
        encoding="utf-8",
    )
    company_file.write_text(
        json.dumps(
            [
                {
                    "ticker": "FILE",
                    "nasdaq_noncompliant": False,
                    "dilution_risk": "LOW",
                    "recent_reverse_split_days": None,
                    "recent_offering_days": None,
                    "has_warrants": False,
                    "has_convertibles": False,
                    "has_going_concern_warning": False,
                }
            ]
        ),
        encoding="utf-8",
    )
    toss_file.write_text(
        json.dumps(
            [
                {
                    "ticker": "FILE",
                    "tracked_investors_holding": 12,
                    "new_buy_count_7d": 4,
                    "consensus_level": "HIGH",
                    "signal_quality": "HIGH",
                    "historical_follow_return_30d_pct": 6,
                }
            ]
        ),
        encoding="utf-8",
    )
    news_file.write_text(
        json.dumps(
            [
                {
                    "ticker": "FILE",
                    "headline": "FILE has a reproducible local fixture",
                    "source": "fixture",
                }
            ]
        ),
        encoding="utf-8",
    )

    main(
        [
            "evaluate-and-save",
            "--ticker",
            "FILE",
            "--side",
            "BUY",
            "--confidence",
            "0.7",
            "--reason",
            "file fixture",
            "--db",
            str(db_path),
            "--market-file",
            str(market_file),
            "--company-risk-file",
            str(company_file),
            "--toss-file",
            str(toss_file),
            "--news-file",
            str(news_file),
        ]
    )

    output = json.loads(capsys.readouterr().out)
    repository = RiskRepository(db_path)
    assert output["result"]["decision"] in {Decision.ALLOW.value, Decision.REVIEW.value}
    assert output["saved"]["evaluation_id"] == 1
    assert repository.count_rows("market_snapshots") == 1
    assert repository.count_rows("company_risks") == 1
    assert repository.count_rows("toss_investor_snapshots") == 1
    assert repository.count_rows("news_events") == 1
    assert repository.count_rows("risk_evaluations") == 1
