from datetime import date

from stock_risk_mcp.provider_packs import ProviderPackRun, ProviderPackRunStatus, ProviderPackType
from stock_risk_mcp.repository import RiskRepository


def test_provider_pack_run_repository_round_trip(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    run = ProviderPackRun(
        provider_pack_type=ProviderPackType.PRICE,
        as_of_date=date(2026, 6, 13),
        status=ProviderPackRunStatus.COMPLETED,
        connector_run_ids=["connector_1"],
        normalize_run_id="normalize_1",
        import_run_id="import_1",
        output_paths=["prices.csv"],
    )

    repository.save_provider_pack_run(run)

    assert repository.get_provider_pack_run(run.provider_pack_run_id) == run
    assert repository.list_provider_pack_runs()[0] == run


def test_provider_pack_type_includes_news() -> None:
    assert ProviderPackType.NEWS.value == "NEWS"
