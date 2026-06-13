from __future__ import annotations

from typing import Any

from stock_risk_mcp.models import TradeProposal
from stock_risk_mcp.agent_tools import read_only_tool_manifest
from stock_risk_mcp.service import RiskEvaluationService

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    FastMCP = None  # type: ignore[assignment]


def evaluate_trade_proposal(
    ticker: str,
    side: str,
    reason: str,
    llm_confidence: float,
    intended_holding_days: int = 30,
) -> dict[str, Any]:
    proposal = TradeProposal(
        ticker=ticker,
        side=side,
        reason=reason,
        llm_confidence=llm_confidence,
        intended_holding_days=intended_holding_days,
    )
    result = RiskEvaluationService().evaluate(proposal)
    return result.model_dump(mode="json")


def create_mcp_server() -> Any:
    if FastMCP is None:
        return None
    mcp = FastMCP("stock-risk-mcp")
    mcp.tool()(evaluate_trade_proposal)
    mcp.tool()(read_only_tool_manifest)
    return mcp


mcp = create_mcp_server()


def main() -> None:
    if mcp is None:
        print("FastMCP is not installed. Install the optional MCP dependency to run this as an MCP server.")
        return
    mcp.run()


if __name__ == "__main__":
    main()
