from __future__ import annotations

from stock_risk_mcp.models import Decision, PolicyMode
from stock_risk_mcp.service import RiskEvaluationService

from tests.utils import make_policy, make_proposal


def test_bad_ticker_blocks() -> None:
    result = RiskEvaluationService(policy=make_policy()).evaluate(make_proposal("BAD"))
    assert result.decision == Decision.BLOCK
    assert result.hard_blocks


def test_dilute_ticker_blocks() -> None:
    result = RiskEvaluationService(policy=make_policy()).evaluate(make_proposal("DILUTE"))
    assert result.decision == Decision.BLOCK
    assert any("희석" in block for block in result.hard_blocks)


def test_pump_ticker_blocks() -> None:
    result = RiskEvaluationService(policy=make_policy()).evaluate(make_proposal("PUMP"))
    assert result.decision == Decision.BLOCK
    assert any("5일 수익률" in block for block in result.hard_blocks)


def test_unknown_ticker_blocks_when_missing_core_data_is_blocked() -> None:
    result = RiskEvaluationService(policy=make_policy(block_missing_core_data=True)).evaluate(make_proposal("UNKNOWN"))
    assert result.decision == Decision.BLOCK
    assert any("누락" in block for block in result.hard_blocks)


def test_read_only_mode_blocks() -> None:
    result = RiskEvaluationService(policy=make_policy(mode=PolicyMode.READ_ONLY)).evaluate(make_proposal("SAFE"))
    assert result.decision == Decision.BLOCK
    assert any("READ_ONLY" in block for block in result.hard_blocks)
