from datetime import date
from typing import Protocol

from stock_risk_mcp.fx_normalizers import GenericFXCSVNormalizer
from stock_risk_mcp.normalize_run import NormalizeSourceResult, NormalizerType
from stock_risk_mcp.price_normalizers import GenericPriceCSVNormalizer
from stock_risk_mcp.signal_normalizers import (
    GenericDilutionCSVNormalizer, GenericFlowCSVNormalizer, GenericNewsCSVNormalizer,
)


class BaseNormalizer(Protocol):
    name: str
    normalizer_type: NormalizerType

    def normalize(
        self, input_path: str, output_dir: str, as_of_date: date | None = None, **kwargs
    ) -> NormalizeSourceResult: ...


class NormalizerRegistry:
    def __init__(self) -> None:
        self._normalizers: dict[str, BaseNormalizer] = {}

    def register_normalizer(self, normalizer: BaseNormalizer) -> None:
        self._normalizers[normalizer.name] = normalizer

    def get_normalizer(self, name: str):
        try:
            return self._normalizers[name]
        except KeyError as error:
            raise LookupError(f"Normalizer not found: {name}") from error

    def list_normalizers(self) -> list[BaseNormalizer]:
        return list(self._normalizers.values())


def default_normalizer_registry() -> NormalizerRegistry:
    registry = NormalizerRegistry()
    for normalizer in (
        GenericPriceCSVNormalizer(), GenericNewsCSVNormalizer(), GenericDilutionCSVNormalizer(),
        GenericFlowCSVNormalizer(), GenericFXCSVNormalizer(),
    ):
        registry.register_normalizer(normalizer)
    return registry
