from __future__ import annotations

from stock_risk_mcp.evidence import make_reason
from stock_risk_mcp.models import (
    CompanyRisk,
    Decision,
    DilutionRisk,
    EvaluationReason,
    MarketSnapshot,
    PolicyMode,
    PortfolioState,
    ReasonType,
    RiskPolicy,
    RiskResult,
    Severity,
    SignalLevel,
    TossSignal,
    TradeProposal,
    TradeSide,
)
from stock_risk_mcp.position_sizing import calculate_position_size
from stock_risk_mcp.reason_codes import HardBlockCode, PositiveCode, WarningCode
from stock_risk_mcp.scoring import calculate_soft_score


def evaluate_trade_risk(
    proposal: TradeProposal,
    market: MarketSnapshot,
    company: CompanyRisk,
    portfolio: PortfolioState,
    toss_signal: TossSignal,
    policy: RiskPolicy,
) -> RiskResult:
    hard_block_reasons = collect_hard_block_reasons(proposal, market, company, portfolio, policy)
    hard_blocks = [reason.message for reason in hard_block_reasons]
    warnings = collect_warnings(market, company, portfolio, policy)
    score_breakdown = calculate_soft_score(market, company, toss_signal)

    decision = decide(score_breakdown.score, hard_blocks)
    max_order_usd, max_position_pct = calculate_position_size(
        score_breakdown.score,
        policy,
        portfolio,
        blocked=bool(hard_blocks) or decision == Decision.BLOCK,
    )

    reason_details = [
        *hard_block_reasons,
        *collect_warning_reasons(proposal.ticker, market, company, portfolio, policy),
        *collect_positive_reasons(proposal.ticker, market, company, toss_signal),
        *collect_negative_reasons(proposal.ticker, market, company, toss_signal),
    ]

    return RiskResult(
        ticker=proposal.ticker,
        decision=decision,
        score=score_breakdown.score,
        max_order_usd=max_order_usd,
        max_position_pct=max_position_pct,
        hard_blocks=hard_blocks,
        warnings=warnings,
        positive_factors=score_breakdown.positive_factors,
        negative_factors=score_breakdown.negative_factors,
        beginner_summary=build_beginner_summary(decision),
        human_approval_required=policy.require_human_approval or decision == Decision.REVIEW,
        reason_details=reason_details,
    )


def decide(score: int, hard_blocks: list[str]) -> Decision:
    if hard_blocks:
        return Decision.BLOCK
    if score >= 80:
        return Decision.ALLOW
    if score >= 60:
        return Decision.REVIEW
    return Decision.BLOCK


def collect_hard_blocks(
    proposal: TradeProposal,
    market: MarketSnapshot,
    company: CompanyRisk,
    portfolio: PortfolioState,
    policy: RiskPolicy,
) -> list[str]:
    return [reason.message for reason in collect_hard_block_reasons(proposal, market, company, portfolio, policy)]


def collect_hard_block_reasons(
    proposal: TradeProposal,
    market: MarketSnapshot,
    company: CompanyRisk,
    portfolio: PortfolioState,
    policy: RiskPolicy,
) -> list[EvaluationReason]:
    blocks: list[EvaluationReason] = []
    ticker = proposal.ticker

    if policy.mode == PolicyMode.READ_ONLY:
        blocks.append(_hard_block(ticker, HardBlockCode.READ_ONLY_MODE, "정책이 READ_ONLY 모드라서 모든 투자 제안을 차단합니다."))
    if proposal.side != TradeSide.BUY:
        blocks.append(_hard_block(ticker, HardBlockCode.SIDE_NOT_ALLOWED, "MVP는 BUY 제안만 평가하며 BUY가 아닌 제안은 차단합니다."))
    if company.nasdaq_noncompliant and policy.block_nasdaq_noncompliant:
        blocks.append(
            _hard_block(
                ticker,
                HardBlockCode.NASDAQ_NONCOMPLIANT,
                "Nasdaq 상장 규정 미준수 리스크가 있습니다.",
                evidence=company.nasdaq_noncompliance_evidence,
            )
        )
    if company.dilution_risk == DilutionRisk.HIGH and policy.block_dilution_high:
        blocks.append(_hard_block(ticker, HardBlockCode.DILUTION_RISK_HIGH, "희석 리스크가 HIGH입니다."))
    if company.dilution_risk == DilutionRisk.UNKNOWN and policy.block_unknown_dilution:
        blocks.append(_hard_block(ticker, HardBlockCode.DILUTION_RISK_UNKNOWN, "희석 리스크를 확인할 수 없어 정책에 따라 차단합니다."))
    if _within_days(company.recent_reverse_split_days, policy.block_reverse_split_within_days):
        blocks.append(_hard_block(ticker, HardBlockCode.RECENT_REVERSE_SPLIT, "최근 역분할 이력이 정책 제한 기간 안에 있습니다."))
    if _within_days(company.recent_offering_days, policy.block_offering_within_days):
        blocks.append(_hard_block(ticker, HardBlockCode.RECENT_OFFERING, "최근 유상증자 또는 오퍼링 이력이 정책 제한 기간 안에 있습니다."))
    if company.has_warrants and policy.block_warrants:
        blocks.append(_hard_block(ticker, HardBlockCode.WARRANT_OVERHANG, "워런트가 있어 정책에 따라 차단합니다."))
    if company.has_convertibles and policy.block_convertibles:
        blocks.append(_hard_block(ticker, HardBlockCode.CONVERTIBLE_OVERHANG, "전환증권이 있어 정책에 따라 차단합니다."))
    if market.market_cap_usd is None and policy.block_missing_core_data:
        blocks.append(_hard_block(ticker, HardBlockCode.MISSING_MARKET_CAP, "시가총액 핵심 데이터가 누락되었습니다."))
    if market.avg_dollar_volume_20d is None and policy.block_missing_core_data:
        blocks.append(_hard_block(ticker, HardBlockCode.MISSING_DOLLAR_VOLUME, "20일 평균 거래대금 핵심 데이터가 누락되었습니다."))
    if market.market_cap_usd is not None and market.market_cap_usd < policy.min_market_cap_usd:
        blocks.append(_hard_block(ticker, HardBlockCode.MARKET_CAP_TOO_SMALL, "시가총액이 정책 최소 기준보다 낮습니다."))
    if market.avg_dollar_volume_20d is not None and market.avg_dollar_volume_20d < policy.min_avg_dollar_volume_usd:
        blocks.append(_hard_block(ticker, HardBlockCode.DOLLAR_VOLUME_TOO_LOW, "20일 평균 거래대금이 정책 최소 기준보다 낮습니다."))
    if market.return_5d_pct is not None and market.return_5d_pct > policy.max_5d_return_pct:
        blocks.append(_hard_block(ticker, HardBlockCode.RETURN_5D_TOO_HIGH, "5일 수익률이 정책상 허용된 급등 한도를 초과했습니다."))
    if portfolio.current_position_pct >= policy.max_single_position_pct:
        blocks.append(_hard_block(ticker, HardBlockCode.POSITION_LIMIT_EXCEEDED, "현재 포지션 비중이 종목별 최대 비중에 도달했습니다."))
    if portfolio.sector_exposure_pct >= policy.max_sector_exposure_pct:
        blocks.append(_hard_block(ticker, HardBlockCode.SECTOR_EXPOSURE_EXCEEDED, "섹터 노출 비중이 최대 한도에 도달했습니다."))
    if portfolio.daily_pnl_pct <= policy.max_daily_loss_pct:
        blocks.append(_hard_block(ticker, HardBlockCode.DAILY_LOSS_LIMIT_EXCEEDED, "일일 손실이 정책 손실 한도 이하입니다."))
    if _cash_pct(portfolio) < policy.min_cash_pct:
        blocks.append(_hard_block(ticker, HardBlockCode.CASH_BELOW_MINIMUM, "현금 비중이 정책 최소 기준보다 낮습니다."))
    if portfolio.open_orders_count >= 3:
        blocks.append(_hard_block(ticker, HardBlockCode.TOO_MANY_OPEN_ORDERS, "열린 주문 수가 3개 이상입니다."))

    return blocks


def collect_warnings(
    market: MarketSnapshot,
    company: CompanyRisk,
    portfolio: PortfolioState,
    policy: RiskPolicy,
) -> list[str]:
    return [reason.message for reason in collect_warning_reasons("", market, company, portfolio, policy)]


def collect_warning_reasons(
    ticker: str,
    market: MarketSnapshot,
    company: CompanyRisk,
    portfolio: PortfolioState,
    policy: RiskPolicy,
) -> list[EvaluationReason]:
    symbol = ticker or market.ticker
    reasons: list[EvaluationReason] = []
    if company.has_going_concern_warning:
        reasons.append(_warning(symbol, WarningCode.DATA_PARTIAL, "계속기업 관련 경고가 있어 추가 확인이 필요합니다.", Severity.HIGH))
    if market.return_20d_pct is not None and market.return_20d_pct > 80:
        reasons.append(_warning(symbol, WarningCode.SHORT_TERM_OVERHEATED, "20일 수익률이 매우 높아 추격 매수 리스크가 있습니다."))
    if portfolio.current_position_pct > 0:
        reasons.append(_warning(symbol, WarningCode.DATA_PARTIAL, "이미 보유 중인 종목이므로 추가 매수 한도가 제한될 수 있습니다."))
    if policy.mode == PolicyMode.AUTO_SMALL:
        reasons.append(_warning(symbol, WarningCode.DATA_PARTIAL, "AUTO_SMALL 모드라도 이 MVP는 실제 주문을 실행하지 않습니다."))
    return reasons


def collect_positive_reasons(
    ticker: str,
    market: MarketSnapshot,
    company: CompanyRisk,
    toss_signal: TossSignal,
) -> list[EvaluationReason]:
    reasons: list[EvaluationReason] = []
    if market.avg_dollar_volume_20d is not None and market.avg_dollar_volume_20d >= 50_000_000:
        reasons.append(_positive(ticker, PositiveCode.DOLLAR_VOLUME_STRONG, "20일 평균 거래대금이 5천만 달러 이상입니다."))
    if market.volatility_20d_pct is not None and market.volatility_20d_pct < 3:
        reasons.append(_positive(ticker, PositiveCode.VOLATILITY_LOW, "20일 변동성이 3% 미만입니다."))
    if market.return_5d_pct is not None and -10 <= market.return_5d_pct <= 15:
        reasons.append(_positive(ticker, PositiveCode.SHORT_TERM_NOT_OVERHEATED, "5일 수익률이 과열 구간이 아닙니다."))
    if company.dilution_risk == DilutionRisk.LOW:
        reasons.append(_positive(ticker, PositiveCode.DILUTION_RISK_LOW, "희석 리스크가 낮습니다."))
    if toss_signal.consensus_level == SignalLevel.HIGH:
        reasons.append(_positive(ticker, PositiveCode.TOSS_CONSENSUS_HIGH, "토스 추적 투자자 합의 수준이 높습니다."))
    elif toss_signal.consensus_level == SignalLevel.MEDIUM:
        reasons.append(_positive(ticker, PositiveCode.TOSS_CONSENSUS_MEDIUM, "토스 추적 투자자 합의 수준이 중간입니다."))
    if toss_signal.signal_quality == SignalLevel.HIGH:
        reasons.append(_positive(ticker, PositiveCode.TOSS_SIGNAL_QUALITY_HIGH, "토스 신호 품질이 높습니다."))
    elif toss_signal.signal_quality == SignalLevel.MEDIUM:
        reasons.append(_positive(ticker, PositiveCode.TOSS_SIGNAL_QUALITY_MEDIUM, "토스 신호 품질이 중간입니다."))
    if toss_signal.historical_follow_return_30d_pct is not None and toss_signal.historical_follow_return_30d_pct > 5:
        reasons.append(_positive(ticker, PositiveCode.HISTORICAL_FOLLOW_RETURN_POSITIVE, "과거 추종 30일 수익률이 5%를 초과했습니다."))
    return reasons


def collect_negative_reasons(
    ticker: str,
    market: MarketSnapshot,
    company: CompanyRisk,
    toss_signal: TossSignal,
) -> list[EvaluationReason]:
    reasons: list[EvaluationReason] = []
    if market.avg_dollar_volume_20d is not None and market.avg_dollar_volume_20d < 20_000_000:
        reasons.append(_negative(ticker, HardBlockCode.DOLLAR_VOLUME_TOO_LOW.value, "20일 평균 거래대금이 2천만 달러 미만입니다."))
    if market.volatility_20d_pct is not None and market.volatility_20d_pct > 8:
        reasons.append(_negative(ticker, WarningCode.VOLATILITY_HIGH.value, "20일 변동성이 8%를 초과했습니다."))
    if market.return_5d_pct is not None and market.return_5d_pct > 40:
        reasons.append(_negative(ticker, HardBlockCode.RETURN_5D_TOO_HIGH.value, "5일 수익률이 40%를 초과해 급등 리스크가 있습니다."))
    if company.dilution_risk == DilutionRisk.MEDIUM:
        reasons.append(_negative(ticker, WarningCode.DILUTION_RISK_MEDIUM.value, "희석 리스크가 중간 수준입니다."))
    if toss_signal.signal_quality == SignalLevel.LOW:
        reasons.append(_negative(ticker, WarningCode.TOSS_SIGNAL_LOW_QUALITY.value, "토스 신호 품질이 낮습니다."))
    if toss_signal.historical_follow_return_30d_pct is not None and toss_signal.historical_follow_return_30d_pct < 0:
        reasons.append(_negative(ticker, WarningCode.HISTORICAL_FOLLOW_RETURN_NEGATIVE.value, "과거 추종 30일 수익률이 음수입니다."))
    return reasons


def build_beginner_summary(decision: Decision) -> str:
    if decision == Decision.BLOCK:
        return "이 종목은 상장 유지/희석/유동성/급등 리스크 중 하나 이상에 걸려 초보자가 따라 사기에는 부적합합니다."
    if decision == Decision.REVIEW:
        return "치명적인 차단 조건은 없지만 변동성이나 데이터 불확실성이 있어 사용자 확인 후 소액만 검토할 수 있습니다."
    return "하드 블록 조건은 없고 점수도 양호하지만, 자동 매수보다는 정해진 한도 내에서 소액 지정가 주문만 검토하는 것이 안전합니다."


def _within_days(value: int | None, threshold: int) -> bool:
    return value is not None and value <= threshold


def _cash_pct(portfolio: PortfolioState) -> float:
    return (portfolio.cash_usd / portfolio.total_equity_usd) * 100


def _hard_block(ticker: str, code: HardBlockCode, message: str, evidence=None) -> EvaluationReason:
    return make_reason(ticker, ReasonType.HARD_BLOCK, code.value, message, Severity.CRITICAL, evidence=evidence)


def _warning(ticker: str, code: WarningCode, message: str, severity: Severity = Severity.MEDIUM) -> EvaluationReason:
    return make_reason(ticker, ReasonType.WARNING, code.value, message, severity)


def _positive(ticker: str, code: PositiveCode, message: str) -> EvaluationReason:
    return make_reason(ticker, ReasonType.POSITIVE, code.value, message, Severity.LOW)


def _negative(ticker: str, code: str, message: str) -> EvaluationReason:
    return make_reason(ticker, ReasonType.NEGATIVE, code, message, Severity.MEDIUM)
