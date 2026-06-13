from stock_risk_mcp.provider_pack_pipeline import run_provider_pack
from stock_risk_mcp.provider_packs import ProviderPackType


def run_dilution_provider_pack(repository, config, output_dir, as_of_date, **kwargs):
    return run_provider_pack(
        repository, config, ProviderPackType.DILUTION, output_dir, as_of_date, **kwargs
    )
