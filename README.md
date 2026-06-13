# Project Direction

`stock-risk-mcp`의 장기 목표는 자동매매 가능한 risk-capped trading
research and execution platform입니다.

현재 구현 단계에서는 실제 주문 기능이 없습니다. 최종 목표는
자동매수/자동매도가 가능한 시스템이지만, live execution은 별도
단계에서 강한 risk gate와 kill switch를 갖춘 뒤 구현합니다.

개발 단계는 다음처럼 분리합니다.

1. **Research / Paper Trading**
   - 현재까지 구현된 scan, Provider Pack, paper trading, replay, report,
     dashboard 계층
2. **Realtime Monitoring**
   - 전체 universe 얕은 감시, Hot Watchlist 자동 갱신, intraday
     candidate signal 생성
   - 실제 주문 없음
3. **Execution Intent Layer**
   - strategy는 주문을 직접 실행하지 않고 `BUY`, `SELL`, `STOP`,
     `TAKE_PROFIT`, `REDUCE` 등의 `OrderIntent`만 생성
   - 모든 intent는 deterministic risk gate를 통과해야 함
4. **Live Execution Layer**
   - broker API 연동은 별도 단계에서 구현
   - live trading은 기본 OFF이며 명시적 활성화와 paper/sandbox 검증 필요

구현 순서:

```text
v2.8.0 Real-Time Market Data Foundation + Dynamic Watchlist Engine
v2.9.0 Order Intent / Execution Gate Foundation
v3.0.0 Broker Sandbox Execution Adapter
v3.1.0 Live Trading Guardrails
```

`v2.8.0` 범위는 realtime monitoring과 dynamic watchlist까지이며 실제
주문이나 broker/account endpoint는 포함하지 않습니다.

장기 execution 계층에도 다음 안전 계약은 유지됩니다.

- hard-risk rule은 strategy, agent, optimizer가 변경할 수 없음
- margin과 options는 기본 금지
- market order는 기본 금지
- stop-loss 비활성화 금지
- max daily loss, max single position, min cash 강제
- kill switch 필수
- 모든 OrderIntent와 execution result를 DB 감사 로그에 저장
- live trading 기본 OFF
- paper, sandbox, live mode를 명확히 분리

# Policy Report

백테스트 결과가 쌓이면 `report` 명령으로 리스크 정책이 실제 이후 수익률과 어떤 관계가 있었는지 분석할 수 있습니다.

```bash
python -m stock_risk_mcp.cli report --db data/stock_risk_mcp.sqlite3
```

리포트는 다음 섹션을 포함합니다.

- `decision_performance`: `ALLOW`, `REVIEW`, `BLOCK` 판정별 count, 평균/중앙 수익률, 승률, 손실률, 평균 최대 낙폭, 평균 최대 상승폭을 보여줍니다.
- `score_bucket_performance`: `0_39`, `40_59`, `60_79`, `80_100` 점수 구간별 성과를 보여줍니다.
- `hard_block_performance`: hard block 사유별 이후 성과를 보여줍니다. 차단된 종목의 평균 수익률이 크게 음수라면 해당 차단 규칙이 유효했을 가능성이 있습니다.
- `policy_recommendations`: decision, score bucket, hard block 성과를 바탕으로 정책 조정 후보를 생성합니다.

`policy_recommendations`는 자동 투자 지시가 아닙니다. 실제 주문 기능도 없으며, 정책 튜닝을 검토하기 위한 참고자료입니다.

# Evidence And Provenance

리스크 평가 결과의 근거는 호환용 `risk_evaluations.result_json`에도 계속 저장되지만, 분석과 추적은 normalized `evaluation_reasons` 테이블을 우선 사용합니다. 이 테이블은 hard block, warning, positive factor, negative factor를 `reason_code`와 evidence/source 정보로 저장합니다.

주요 hard block reason code:

- `READ_ONLY_MODE`
- `SIDE_NOT_ALLOWED`
- `NASDAQ_NONCOMPLIANT`
- `DILUTION_RISK_HIGH`
- `DILUTION_RISK_UNKNOWN`
- `RECENT_REVERSE_SPLIT`
- `RECENT_OFFERING`
- `WARRANT_OVERHANG`
- `CONVERTIBLE_OVERHANG`
- `MISSING_MARKET_CAP`
- `MISSING_DOLLAR_VOLUME`
- `MARKET_CAP_TOO_SMALL`
- `DOLLAR_VOLUME_TOO_LOW`
- `RETURN_5D_TOO_HIGH`
- `POSITION_LIMIT_EXCEEDED`
- `SECTOR_EXPOSURE_EXCEEDED`
- `DAILY_LOSS_LIMIT_EXCEEDED`
- `CASH_BELOW_MINIMUM`
- `TOO_MANY_OPEN_ORDERS`

Reason 조회:

```bash
python -m stock_risk_mcp.cli reasons --db data/stock_risk_mcp.sqlite3 --evaluation-id 1
```

Data source 조회:

```bash
python -m stock_risk_mcp.cli sources --db data/stock_risk_mcp.sqlite3
```

Ingestion run 조회:

```bash
python -m stock_risk_mcp.cli ingestion-runs --db data/stock_risk_mcp.sqlite3
```

외부 데이터 adapter를 붙일 때는 반드시 `source_name`, `source_type`, 가능한 경우 `source_url`, `observed_at`, `raw_reference`, `confidence`를 함께 저장해야 합니다. 이 프로젝트는 여전히 외부 API 호출과 실제 주문 기능을 구현하지 않습니다.

# stock-risk-mcp

`stock-risk-mcp`는 개인 투자자가 로컬에서 투자 제안을 검토하기 위한 리스크 평가 MVP입니다. 이 프로젝트는 투자 조언이나 자동매매 시스템이 아니며, 실제 주문 실행 기능을 포함하지 않습니다.

LLM은 주문을 직접 실행하면 안 됩니다. LLM이나 외부 클라이언트는 투자 제안만 만들고, Risk Engine이 정책과 리스크 데이터를 기준으로 최종 게이트 역할을 합니다.

## 기능

- LLM 또는 외부 클라이언트의 투자 제안을 JSON 형태의 `RiskResult`로 평가
- 하드 블록 조건 우선 적용
- 하드 블록이 없을 때 소프트 점수 계산
- `ALLOW`, `REVIEW`, `BLOCK` 결정
- 최대 주문 가능 금액과 최대 포지션 비중 계산
- MVP용 mock adapter 제공
- SQLite 기반 로컬 저장소 제공
- CSV/JSON 파일에서 market/company/toss/news 데이터를 읽는 file adapter 제공
- 평가 입력 스냅샷과 결과를 DB에 저장해 재현 가능한 평가 기록 생성
- 향후 FINVIZ, Newsfilter.io, Dilution Tracker, Nasdaq Noncompliant, 토스 포트폴리오, 브로커 API를 붙이기 쉬운 adapter 구조

## 설치

```bash
cd stock-risk-mcp
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## 실행

```bash
python -m stock_risk_mcp.cli --ticker SAFE --side BUY --confidence 0.7 --reason "토스 상위 투자자들이 공통 보유"
```

출력은 pretty JSON입니다. 예시는 다음과 같은 형태입니다.

```json
{
  "ticker": "SAFE",
  "decision": "ALLOW",
  "score": 94,
  "max_order_usd": 2000.0
}
```

## 평가 저장

`evaluate-and-save` 명령은 adapter가 반환한 데이터를 SQLite에 저장한 뒤 평가 결과도 함께 저장합니다. 외부 API 호출이나 실시간 크롤링은 하지 않습니다.

```bash
python -m stock_risk_mcp.cli evaluate-and-save --ticker SAFE --side BUY --confidence 0.7 --reason "토스 상위 투자자들이 공통 보유" --db data/stock_risk_mcp.sqlite3
```

파일 adapter를 사용하려면 CSV 또는 JSON 파일 경로를 전달합니다.

```bash
python -m stock_risk_mcp.cli evaluate-and-save \
  --ticker SAFE \
  --side BUY \
  --confidence 0.7 \
  --reason "파일 기반 재현 평가" \
  --db data/stock_risk_mcp.sqlite3 \
  --market-file fixtures/market.json \
  --company-risk-file fixtures/company_risks.json \
  --toss-file fixtures/toss_signals.json \
  --news-file fixtures/news.json
```

저장되는 테이블은 다음과 같습니다.

- `market_snapshots`
- `company_risks`
- `toss_investor_snapshots`
- `news_events`
- `risk_evaluations`
- `price_history`
- `backtest_results`
- `compliance_records`

## Nasdaq Noncompliant CSV

Nasdaq Noncompliant Companies 데이터는 외부 웹 요청이나 실시간 크롤링으로 가져오지 않습니다. 사용자가 저장한 CSV 파일을 로컬에서 읽고, 해당 ticker가 있으면 `NASDAQ_NONCOMPLIANT` hard block의 근거로 사용합니다.

CSV 최소 컬럼:

```csv
ticker
BAD
```

선택 컬럼:

- `company_name`
- `issue`
- `deficiency`
- `notice_date`
- `source_url`
- `raw_reference`

예시:

```csv
ticker,company_name,issue,deficiency,notice_date,source_url,raw_reference
BAD,Example Bad Corp,Bid Price,Minimum bid price below requirement,2026-05-01,https://www.nasdaq.com/market-activity/stocks/non-compliant-company-list,row-1
XYZ,XYZ Bio Inc,Market Value,Market value below requirement,2026-05-03,https://www.nasdaq.com/market-activity/stocks/non-compliant-company-list,row-2
```

CSV를 SQLite에 ingest:

```bash
python -m stock_risk_mcp.cli ingest-nasdaq-noncompliant --file data/nasdaq_noncompliant.csv --db data/stock_risk_mcp.sqlite3
```

단일 ticker 확인:

```bash
python -m stock_risk_mcp.cli check-compliance --ticker BAD --file data/nasdaq_noncompliant.csv
```

평가 저장 시 CSV 기반 Nasdaq 미준수 evidence를 사용:

```bash
python -m stock_risk_mcp.cli evaluate-and-save \
  --ticker BAD \
  --side BUY \
  --confidence 0.7 \
  --reason "파일 기반 compliance 확인" \
  --db data/stock_risk_mcp.sqlite3 \
  --nasdaq-noncompliant-file data/nasdaq_noncompliant.csv
```

이 경우 ticker가 CSV에 있으면 `RiskResult.reason_details`의 `NASDAQ_NONCOMPLIANT` reason evidence는 `source_name`이 `nasdaq_noncompliant_file`, `source_type`이 `FILE`로 기록됩니다.

## 가격 데이터

백테스트는 외부 API를 호출하지 않습니다. CSV 또는 JSON 파일로 가격 히스토리를 주입합니다.

CSV 형식:

```csv
ticker,date,open,high,low,close,volume
SAFE,2026-01-02,100,104,99,100,1000
SAFE,2026-02-01,109,112,106,110,1200
```

필수 컬럼은 `ticker`, `date`, `close`입니다. `open`, `high`, `low`, `volume`은 선택적으로 비워둘 수 있습니다.

가격 데이터 ingest:

```bash
python -m stock_risk_mcp.cli ingest-prices --file data/prices.csv --db data/stock_risk_mcp.sqlite3
```

`ingest-prices`는 가격 히스토리를 SQLite `price_history` 테이블에 저장합니다. 반면 `evaluate-and-save --price-history-file`은 저장 없이 해당 CSV/JSON 파일을 바로 읽어 이번 평가의 `MarketSnapshot`을 계산합니다.

파일 가격 데이터로 평가:

```bash
python -m stock_risk_mcp.cli evaluate-and-save \
  --ticker SAFE \
  --side BUY \
  --confidence 0.7 \
  --reason "파일 가격 데이터 기반 평가" \
  --db data/stock_risk_mcp.sqlite3 \
  --price-history-file data/prices.csv
```

DB에 저장된 가격 데이터로 평가:

```bash
python -m stock_risk_mcp.cli evaluate-and-save \
  --ticker SAFE \
  --side BUY \
  --confidence 0.7 \
  --reason "DB 가격 데이터 기반 평가" \
  --db data/stock_risk_mcp.sqlite3 \
  --use-db-price-history
```

가격 히스토리 기반 adapter는 다음 지표를 계산합니다.

- `price`: 최신 거래일 종가
- `avg_dollar_volume_20d`: 최근 20개 price bar의 `close * volume` 평균
- `return_5d_pct`: 최신 종가와 5거래일 전 종가의 수익률
- `return_20d_pct`: 최신 종가와 20거래일 전 종가의 수익률
- `volatility_20d_pct`: 최근 20개 일간 수익률의 표준편차

데이터가 부족하면 계산할 수 없는 필드는 `None`으로 둡니다. 예를 들어 20개 미만의 bar만 있으면 `avg_dollar_volume_20d`와 `return_20d_pct`는 비어 있을 수 있습니다.

가격 데이터는 투자 성과를 보장하기 위한 데이터가 아니라 리스크 평가와 백테스트 검증을 재현 가능하게 만들기 위한 입력입니다.

## Indicator Analysis Layer

Indicator Analysis Layer는 로컬 가격 히스토리에서 기술적·유동성·변동성 지표를 계산하고, 초보자가 이해하기 쉬운 해석과 보조 점수를 생성합니다. 이 결과는 기존 Risk Engine hard block을 대체하지 않으며 매수 추천도 아닙니다. 리스크 해석과 전략 실험을 위한 보조 신호입니다.

지원 지표:

- 가격/추세: `RETURN_1D_PCT`, `RETURN_5D_PCT`, `RETURN_20D_PCT`, `RETURN_60D_PCT`, `SMA_20`, `SMA_60`, `SMA_120`, `DISTANCE_FROM_SMA_20_PCT`, `DISTANCE_FROM_SMA_60_PCT`
- 거래량/유동성: `AVG_DOLLAR_VOLUME_20D`, `VOLUME_SPIKE_RATIO`, `DOLLAR_VOLUME_SPIKE_RATIO`
- 변동성: `VOLATILITY_20D_PCT`, `ATR_14_PCT`, `MAX_DRAWDOWN_60D_PCT`
- 기술적 지표: `RSI_14`, `BOLLINGER_POSITION`

초보자용 의미:

- 수익률과 이동평균 거리: 최근 급등·하락 또는 추세 이탈 여부를 확인합니다.
- 평균 거래대금과 거래량 급증: 진입/청산 용이성과 갑작스러운 시장 관심을 확인합니다.
- 변동성, ATR, 최대 낙폭: 가격 흔들림과 최근 손실 위험을 확인합니다.
- RSI와 볼린저 위치: 과매수·과매도 또는 단기 과열 가능성을 참고합니다.

파일 가격 히스토리 분석:

```bash
python -m stock_risk_mcp.cli analyze-indicators --ticker SAFE --price-history-file data/prices.csv
```

DB 가격 히스토리 분석:

```bash
python -m stock_risk_mcp.cli analyze-indicators --ticker SAFE --db data/stock_risk_mcp.sqlite3 --use-db-price-history
```

분석 결과 저장:

```bash
python -m stock_risk_mcp.cli analyze-indicators-and-save --ticker SAFE --price-history-file data/prices.csv --db data/stock_risk_mcp.sqlite3
```

계산에 필요한 가격 bar, 거래량, 고가 또는 저가 데이터가 부족하면 해당 지표의 값은 `None`, 신호는 `UNKNOWN`이 될 수 있습니다.

## ABC Setup And Trade Plan

ABC Setup Layer는 Indicator Analysis 결과를 LONG 중심의 paper trade 후보로 정리합니다. 실제 주문 기능이 아니며, 생성된 `TradePlan`도 주문 제안 전에 반드시 기존 Risk Engine 최종 검사를 통과해야 합니다.

셋업 등급:

- `A`: 강한 후보. 최소 손익비 3.0 이상을 요구하며 기본 목표 손익비는 4.0입니다.
- `B`: 검토 후보. 최소 손익비 2.5 이상을 요구하며 기본 목표 손익비는 3.0입니다.
- `C`: 약한 후보. 기본적으로 매매하지 않습니다.
- `NO_TRADE`: 현재 조건에서는 매매 후보를 만들지 않습니다.

LONG TradePlan 계산 방식:

- 진입가: 최신 종가
- 손절가: 최근 20개 bar의 swing low와 `latest close - 1.5 * ATR` 중 더 낮은 보수적 가격
- 목표가: `entry_price + risk_per_share * grade target_rr`
- 포지션 크기: 계좌 자산 대비 최대 손실금액을 주당 위험금액으로 나눠 계산
- 명목금액 한도: `cash_available`과 `account_equity * max_position_pct` 중 작은 값

셋업 분석:

```bash
python -m stock_risk_mcp.cli analyze-setup --ticker SAFE --price-history-file data/prices.csv
```

paper TradePlan 생성:

```bash
python -m stock_risk_mcp.cli create-trade-plan \
  --ticker SAFE \
  --price-history-file data/prices.csv \
  --account-equity 10000 \
  --cash-available 5000
```

TradePlan 생성 및 저장:

```bash
python -m stock_risk_mcp.cli create-trade-plan-and-save \
  --ticker SAFE \
  --price-history-file data/prices.csv \
  --db data/stock_risk_mcp.sqlite3 \
  --account-equity 10000 \
  --cash-available 5000
```

`TradePlan.decision`의 `PROPOSE` 또는 `REVIEW`는 주문 승인이 아닙니다. 뉴스, 상장 유지, 희석, 유동성, 포트폴리오 한도 등을 확인하는 기존 Risk Engine 검사를 반드시 별도로 수행해야 합니다.

## Basket Engine

Basket Engine은 여러 개의 저장된 `TradePlan`을 모아 급등 예상주 paper trading 바스켓 후보를 구성합니다. 개별 종목 Risk Engine을 대체하지 않으며 실제 주문도 실행하지 않습니다. 역할은 바스켓 전체 손실, 총 노출, 종목별 리스크 배분, 섹터·테마 집중 위험을 관리하는 것입니다.

`BasketPolicy` 주요 설정:

- `max_basket_loss_pct`: 계좌 자산 대비 바스켓 전체 최대 손실 한도
- `max_basket_notional_pct`: 계좌 자산 대비 바스켓 전체 최대 명목금액
- `max_single_candidate_loss_pct`: 종목 하나에 배분 가능한 최대 손실
- `max_single_position_pct`: 종목 하나의 최대 명목 비중
- `max_candidates`, `min_candidates`: 바스켓 후보 수 제한
- `max_same_sector_count`, `max_same_theme_count`: 동일 섹터·테마 집중 제한

셋업별 risk unit:

- A 셋업: `1.0`
- B 셋업: `0.5`
- C 및 NO_TRADE: `0.0`

전체 허용 손실은 risk unit 비율에 따라 후보에 배분됩니다. 각 배분은 개별 TradePlan의 최대 손실, 단일 후보 손실 한도, 현금, 단일 포지션 비중, 남은 바스켓 명목금액 한도를 넘을 수 없습니다. 동일 섹터나 테마 후보가 제한을 초과하면 낮은 score 후보부터 제외됩니다. DB TradePlan에 섹터나 테마 정보가 없으면 `UNKNOWN`으로 처리합니다.

최근 저장 TradePlan으로 바스켓 생성:

```bash
python -m stock_risk_mcp.cli build-basket-from-trade-plans \
  --db data/stock_risk_mcp.sqlite3 \
  --account-equity 10000 \
  --cash-available 5000 \
  --max-candidates 10
```

바스켓 생성 및 저장:

```bash
python -m stock_risk_mcp.cli build-basket-and-save \
  --db data/stock_risk_mcp.sqlite3 \
  --account-equity 10000 \
  --cash-available 5000 \
  --max-candidates 10
```

저장 바스켓 조회:

```bash
python -m stock_risk_mcp.cli show-basket --db data/stock_risk_mcp.sqlite3 --basket-id <basket_id>
```

`BasketPlan`은 paper trading/proposal 후보입니다. 실제 주문을 검토하기 전 각 종목은 기존 Risk Engine을 통과해야 하며 사용자가 뉴스와 공시를 다시 확인해야 합니다.

## 백테스트

저장된 `risk_evaluations`와 `price_history`를 매칭해 리스크 엔진 판단 이후 수익률을 계산합니다. 평가일 또는 그 다음 거래일의 종가를 entry price로 사용하고, 지정한 horizon 이후 가장 가까운 거래일 종가를 exit price로 사용합니다.

```bash
python -m stock_risk_mcp.cli backtest --db data/stock_risk_mcp.sqlite3 --horizon-days 30
```

요약 확인:

```bash
python -m stock_risk_mcp.cli backtest-summary --db data/stock_risk_mcp.sqlite3
```

요약은 decision별 count, 평균 수익률, 승률, 평균 최대 낙폭을 보여줍니다. 이 백테스트는 실제 투자 성과를 보장하지 않으며, 리스크 엔진의 판단이 이후 가격 움직임과 어떤 관계가 있었는지 검증하기 위한 도구입니다.

## 테스트

```bash
pytest
```

## 정책 수정

기본 정책은 `policies/default_policy.yaml`에 있습니다. 최소 시가총액, 최소 거래대금, 최대 포지션 비중, 현금 비중, 희석 리스크 차단 여부 등을 YAML에서 수정할 수 있습니다.

CLI에서 다른 정책 파일을 쓰려면 `--policy`를 전달합니다.

```bash
python -m stock_risk_mcp.cli --ticker WATCH --side BUY --confidence 0.6 --reason "관심 종목" --policy policies/default_policy.yaml
```

## 실제 데이터 소스 연결

외부 API 키나 비밀정보를 코드에 넣지 마세요. 실제 데이터 연결은 `src/stock_risk_mcp/adapters/base.py`의 인터페이스를 구현하는 새 adapter 클래스를 추가하는 방식으로 붙입니다.

- `MarketDataAdapter`: 가격, 시가총액, 거래대금, 변동성
- `CompanyRiskAdapter`: Nasdaq 미준수, 희석 리스크, 오퍼링, 워런트
- `PortfolioAdapter`: 총자산, 현금, 현재 포지션, 섹터 노출
- `TossSignalAdapter`: 추적 투자자 보유, 신규 매수, 신호 품질

서비스 생성 시 mock 대신 실제 adapter 인스턴스를 주입하면 됩니다.

저장 계층은 `src/stock_risk_mcp/repository.py`의 `RiskRepository`를 통해 사용합니다. ingestion 흐름은 `src/stock_risk_mcp/ingestion.py`의 `save_evaluation_inputs_and_result`가 담당합니다.

## MCP 서버

`mcp` 패키지가 설치되어 있으면 `mcp_server.py`가 FastMCP tool을 등록합니다. 설치되어 있지 않아도 import가 깨지지 않으며 안내 메시지를 출력합니다.

```bash
python -m stock_risk_mcp.mcp_server
```

등록되는 tool은 `evaluate_trade_proposal`이며, 입력은 `ticker`, `side`, `reason`, `llm_confidence`, `intended_holding_days`입니다.

## Paper Trading / Basket Backtest

저장된 `BasketPlan`을 DB 또는 CSV/JSON 가격 히스토리에 재생해 allocation별
`PaperTrade`와 합산 `BasketBacktestResult`를 생성하고 저장합니다.

종료 사유:

- `STOP_LOSS`: bar의 저가가 손절가에 닿음
- `TAKE_PROFIT`: bar의 고가가 목표가에 닿음
- `TIME_EXIT`: horizon까지 손절가와 목표가에 닿지 않음
- `NO_DATA`: 사용할 수 있는 가격 데이터가 없음

같은 bar에서 손절가와 목표가에 모두 닿으면 보수적으로 `STOP_LOSS`를 우선합니다.

DB 가격 히스토리로 실행:

```bash
python -m stock_risk_mcp.cli paper-trade-basket --db data/stock_risk_mcp.sqlite3 --basket-id <basket_id> --horizon-days 10
```

로컬 가격 파일로 실행:

```bash
python -m stock_risk_mcp.cli paper-trade-basket-from-file --db data/stock_risk_mcp.sqlite3 --basket-id <basket_id> --price-history-file data/prices.csv --horizon-days 10
```

저장된 paper trade 조회 및 전체 성과 요약:

```bash
python -m stock_risk_mcp.cli paper-trades --db data/stock_risk_mcp.sqlite3 --basket-id <basket_id>
python -m stock_risk_mcp.cli basket-performance --db data/stock_risk_mcp.sqlite3
```

이 기능은 전략 검증용이며 실제 주문을 실행하지 않습니다. 수수료, 슬리피지,
체결 지연, 부분 체결, bar 내부의 체결 순서는 아직 단순화되거나 생략되어 있습니다.

## Replay Snapshot Layer

The Replay Snapshot Layer stores reproducible inputs and outputs for a future
Policy Replay Engine. It is a snapshot storage layer, not `FULL_POLICY_REPLAY`.
It does not regenerate indicators, TradePlans, or BasketPlans using an
`as_of_date` cutoff. `as_of_date` is metadata only, so snapshots built from
recent TradePlans may contain information that was not available on that date.

Snapshot an existing official basket:

```bash
python -m stock_risk_mcp.cli replay-snapshot-from-basket --db data/stock_risk_mcp.sqlite3 --basket-id <basket_id> --as-of-date 2026-06-13
```

Build snapshots from recent TradePlans:

```bash
python -m stock_risk_mcp.cli replay-snapshot-from-recent-trade-plans --db data/stock_risk_mcp.sqlite3 --account-equity 10000 --cash-available 5000
```

The recent-TradePlan command is snapshot-only by default. It does not write to
`basket_plans`, `basket_allocations`, or `basket_blocked_candidates`. Its
replay-only `basket_id` may therefore have no matching row in `basket_plans`.
Use `--save-basket` only when the generated basket must also become an official
paper-trading/proposal basket. CLI output and `ReplayRun.notes` record
`saved_to_basket_plans: true/false`.

Inspect saved replay data:

```bash
python -m stock_risk_mcp.cli replay-runs --db data/stock_risk_mcp.sqlite3
python -m stock_risk_mcp.cli replay-show --db data/stock_risk_mcp.sqlite3 --run-id <run_id>
```

The `FULL_POLICY_REPLAY` workflow uses the same candidate universe and data
restricted by the same as-of cutoff to regenerate indicators, TradePlans, and
BasketPlans separately for each candidate policy.

## Full Policy Replay

`FULL_POLICY_REPLAY` regenerates policy-specific indicators, SetupSignals,
TradePlans, BasketPlans, and paper outcomes from a saved ReplayRun candidate
universe.

It differs from Replay Snapshot Layer:

- Replay Snapshot stores source records and may use `as_of_date` as metadata.
- Full Policy Replay strictly uses only price bars whose date is on or before
  `as_of_date` for indicator, trade, and basket generation.
- Paper outcomes use only price bars after `as_of_date` within `horizon_days`.
- Existing ReplayTradePlanSnapshot values are not reused as regenerated plans.

Run an explicit or active policy:

```bash
python -m stock_risk_mcp.cli policy-replay --db data/stock_risk_mcp.sqlite3 --replay-run-id <run_id> --policy-id default --policy-version v1 --horizon-days 10 --account-equity 10000 --cash-available 5000
python -m stock_risk_mcp.cli policy-replay-active --db data/stock_risk_mcp.sqlite3 --replay-run-id <run_id> --horizon-days 10 --account-equity 10000 --cash-available 5000
```

By default regenerated TradePlans and the BasketPlan remain in memory.
`--save-intermediate` saves regenerated TradePlans without a
`policy_replay_id` linkage. `--save-basket` saves the official BasketPlan.
A local `--price-history-file` may be used instead of DB price history.

List results and compare policies:

```bash
python -m stock_risk_mcp.cli policy-replay-results --db data/stock_risk_mcp.sqlite3 --replay-run-id <run_id>
python -m stock_risk_mcp.cli policy-compare --db data/stock_risk_mcp.sqlite3 --replay-run-id <run_id> --baseline-policy-id default --baseline-policy-version v1 --candidate-policy-id default --candidate-policy-version v2 --horizon-days 10 --account-equity 10000 --cash-available 5000
```

If either replay allocates fewer than three candidates, comparison returns
`NEED_MORE_DATA` regardless of favorable deltas. Otherwise an objective delta
of at least +5 accepts the candidate and at most -5 rejects it.

This is a local paper-trading policy comparison. It does not guarantee real
investment performance and never places real orders.

## Policy Evaluation Suite And Promotion Gate

The Policy Evaluation Suite compares baseline and candidate policies across
multiple ReplayRuns. Performance metrics use only identical ReplayRun pairs
where both policy replays are `COMPLETED`. Pairs containing `NO_DATA`, `FAILED`,
`CREATED`, or missing results are excluded and reported as unavailable data.

Data sufficiency takes priority over favorable performance:

- fewer than five requested ReplayRuns
- fewer than three completed pairs
- unavailable-data rate above 0.4
- any completed replay with fewer than three allocated candidates

An adequate suite accepts only when objective delta is at least +5, return
delta is positive, and candidate win rate does not deteriorate. Objective delta
at most -5 or return delta below -2 rejects the candidate. Other results need
more data.

```bash
python -m stock_risk_mcp.cli policy-evaluate-suite --db data/stock_risk_mcp.sqlite3 --baseline-policy-id default --baseline-policy-version v1 --candidate-policy-id default --candidate-policy-version v2 --horizon-days 10 --account-equity 10000 --cash-available 5000 --replay-run-id <run1> --replay-run-id <run2>
python -m stock_risk_mcp.cli policy-evaluation-suites --db data/stock_risk_mcp.sqlite3
python -m stock_risk_mcp.cli policy-propose-promotion --db data/stock_risk_mcp.sqlite3 --suite-id <suite_id>
python -m stock_risk_mcp.cli policy-promotion-proposals --db data/stock_risk_mcp.sqlite3
```

A promotion proposal does not change policy status. `policy-approve` explicitly
changes a non-rejected policy to `APPROVED`. `policy-activate` accepts only an
`APPROVED` policy, changes it to `ACTIVE`, and retires the prior active policy.
Activation changes which soft policy the current policy-aware pipeline uses, so
it requires deliberate operator review.

```bash
python -m stock_risk_mcp.cli policy-approve --db data/stock_risk_mcp.sqlite3 --policy-id default --policy-version v2
python -m stock_risk_mcp.cli policy-activate --db data/stock_risk_mcp.sqlite3 --policy-id default --policy-version v2
```

This suite is based on local paper replay outcomes and does not guarantee real
investment performance or place real orders.

## Candidate Scanner And Universe Builder

The Candidate Scanner builds a research universe from local price history. It
is not a buy recommendation, does not call external APIs, does not request
realtime data, does not calculate outcomes, and never places orders.

Every scan uses only price bars with `date <= as_of_date`. DB, local
CSV/JSON, and explicit `--ticker` universes are supported. The scanner reuses
the existing Indicator, policy-aware Setup, and TradePlan pipeline, then
applies liquidity, spike, price, return, setup, compliance, and score filters.
If no local compliance record exists, compliance is recorded as UNKNOWN with
a warning; the candidate is not excluded solely because the data is absent.

```bash
python -m stock_risk_mcp.cli scan-candidates --db data/stock_risk_mcp.sqlite3 --as-of-date 2026-06-13 --save
python -m stock_risk_mcp.cli scan-candidates --db data/stock_risk_mcp.sqlite3 --as-of-date 2026-06-13 --price-history-file data/prices.csv --use-active-policy
python -m stock_risk_mcp.cli scan-candidates --db data/stock_risk_mcp.sqlite3 --as-of-date 2026-06-13 --ticker AAA --ticker BBB
python -m stock_risk_mcp.cli scan-runs --db data/stock_risk_mcp.sqlite3
python -m stock_risk_mcp.cli scan-results --db data/stock_risk_mcp.sqlite3 --scan-run-id <scan_run_id> --decision INCLUDE
```

`scan-candidates` prints results without persistence by default. `--save`
stores `scan_runs` and `candidate_scan_results`; it does not save TradePlans.
Basket conversion is also output-only by default, and writes official basket
tables only with `--save-basket`.

```bash
python -m stock_risk_mcp.cli scan-to-basket --db data/stock_risk_mcp.sqlite3 --scan-run-id <scan_run_id> --account-equity 10000 --cash-available 5000
python -m stock_risk_mcp.cli scan-to-basket --db data/stock_risk_mcp.sqlite3 --scan-run-id <scan_run_id> --account-equity 10000 --cash-available 5000 --save-basket
python -m stock_risk_mcp.cli scan-to-replay-snapshot --db data/stock_risk_mcp.sqlite3 --scan-run-id <scan_run_id> --as-of-date 2026-06-13
```

Replay conversion stores selected candidate scan results, including score,
decision, reasons, warnings, and TradePlan metadata, as replay candidate
snapshots. It does not create an official basket or perform
`FULL_POLICY_REPLAY`.

## Signal Enrichment Layer

The Signal Enrichment Layer adjusts Candidate Scanner research scores with
normalized local news, dilution, Toss top-investor portfolio, and
foreign/institution flow records. Signals are auxiliary candidate-universe
inputs, not buy recommendations, and do not replace Risk Engine hard blocks.
No external APIs, realtime requests, or orders are used.

All DB and file signals must satisfy `observed_at <= as_of_date`.
`scan-candidates` merges existing `ticker_signals` rows with specified signal
files by default. Duplicates use the key `ticker`, `signal_type`,
`observed_at`, `source_name`, `raw_event_type`, and `title`; the file record
wins when both sources contain the same key. Use `--ignore-db-signals` to use
only specified files.

Supported file columns:

- news: `ticker`, `observed_at`, `title`, `summary`, `event_type`,
  `sentiment`, `materiality`
- dilution: `ticker`, `observed_at`, `event_type`, `severity`, `details`
- Toss portfolio: `ticker`, `observed_at`, `investor_id`,
  `investor_rank_group`, `holding_weight`, `change_type`, `change_pct`
- flow: `ticker`, `observed_at`, `foreign_net_buy`, `institution_net_buy`,
  `foreign_ownership_change`, `flow_window_days`

Critical negative signals conservatively exclude a candidate. High negative
signals lower only an existing INCLUDE candidate to WATCH. Positive signals
never promote an existing EXCLUDE candidate. Toss portfolio score deltas are
clamped to `-10` through `+10` to avoid overconfidence.

```bash
python -m stock_risk_mcp.cli ingest-signals --db data/stock_risk_mcp.sqlite3 --as-of-date 2026-06-13 --news-signal-file data/news.csv --dilution-signal-file data/dilution.csv --toss-signal-file data/toss.csv --flow-signal-file data/flow.csv
python -m stock_risk_mcp.cli signals --db data/stock_risk_mcp.sqlite3 --ticker AAPL --as-of-date 2026-06-13
python -m stock_risk_mcp.cli scan-candidates --db data/stock_risk_mcp.sqlite3 --as-of-date 2026-06-13 --news-signal-file data/news.csv --save-signals --save
```

`ingest-signals` and `--save-signals` skip an existing dedupe key.
`--save-signals` stores only file signals read for that scan; it does not
re-save DB signals. Candidate scan persistence remains controlled separately
by `--save`.

## Operational Pipeline And Watch Loop

The Operational Pipeline composes the existing local Candidate Scanner,
Signal Enrichment, Basket Engine, Paper Trading, Replay Snapshot, Policy
Replay, and Policy Evaluation Suite. It automates paper-trading operations,
not trading. It never calls external APIs, requests realtime data, or places
orders.

One-shot execution is the default:

```bash
python -m stock_risk_mcp.cli run-scan-pipeline --db data/stock_risk_mcp.sqlite3 --as-of-date 2026-06-13 --use-active-policy
python -m stock_risk_mcp.cli run-paper-pipeline --db data/stock_risk_mcp.sqlite3 --as-of-date 2026-06-13 --account-equity 10000 --cash-available 5000 --horizon-days 10 --use-active-policy
python -m stock_risk_mcp.cli run-policy-evaluation-pipeline --db data/stock_risk_mcp.sqlite3 --baseline-policy-id default --baseline-policy-version v1 --candidate-policy-id default --candidate-policy-version v2 --horizon-days 10 --account-equity 10000 --cash-available 5000
```

Every execution stores a PipelineRun and generated alerts. Errors are recorded
as FAILED or PARTIAL runs with PIPELINE_ERROR alerts instead of silently
discarding completed stages. Policy evaluation stores its suite but never
creates promotion proposals or changes policy status.

Paper storage is conservative:

- default `save_basket=false`: BasketPlan and paper outcome remain unofficial;
  paper results are computed in memory and are not written to `paper_trades`
  or `basket_backtest_results`
- `--save-basket`: stores the official BasketPlan and any computed paper result
- `--no-paper-trade`: skips paper outcome calculation and storage
- replay snapshot storage remains independent, so a replay-only `basket_id`
  may not exist in `basket_plans`

Inspect stored operations:

```bash
python -m stock_risk_mcp.cli pipeline-runs --db data/stock_risk_mcp.sqlite3
python -m stock_risk_mcp.cli pipeline-show --db data/stock_risk_mcp.sqlite3 --pipeline-run-id <pipeline_run_id>
python -m stock_risk_mcp.cli alerts --db data/stock_risk_mcp.sqlite3 --pipeline-run-id <pipeline_run_id>
```

Repeated execution occurs only through the explicit watch loop. Every
iteration creates an independent PipelineRun. The loop stops at
`--max-iterations` when provided or safely on KeyboardInterrupt.

```bash
python -m stock_risk_mcp.cli watch-loop --db data/stock_risk_mcp.sqlite3 --as-of-date 2026-06-13 --account-equity 10000 --cash-available 5000 --interval-seconds 60 --max-iterations 3 --use-active-policy
```

The watch loop performs local paper operations only and never places orders.

## Unified Data Import Pipeline

The Unified Data Import Pipeline validates and imports specified local CSV/JSON
files into the existing price, compliance, and normalized signal tables. It
does not call external APIs, request realtime data, or place orders. Each run
stores source-level row, saved, duplicate-skip, and error counts. A malformed
source is recorded without discarding successful sources from the same run.

```bash
python -m stock_risk_mcp.cli import-data --db data/stock_risk_mcp.sqlite3 --as-of-date 2026-06-13 --price-history-file data/prices.csv --nasdaq-noncompliant-file data/noncompliant.csv --news-signal-file data/news.csv --dilution-signal-file data/dilution.csv --toss-signal-file data/toss.csv --flow-signal-file data/flow.csv
python -m stock_risk_mcp.cli import-runs --db data/stock_risk_mcp.sqlite3
python -m stock_risk_mcp.cli import-show --db data/stock_risk_mcp.sqlite3 --import-run-id <import_run_id>
```

`import-data` is append-only operational ingest. Existing price rows and
duplicates within one file use `(ticker, date)` and are skipped without
updating stored values. The standalone `ingest-prices` command keeps its
existing UPSERT behavior for deliberate manual correction or refresh.
Compliance uses `(ticker, notice_date, source_name, issue, deficiency)`;
signals use the existing normalized signal dedupe key. Signal and compliance
records after `as_of_date` are skipped and recorded as warnings. Imported data
is immediately available to the local scan and paper pipelines.

## External Data Connector Interface

The External Data Connector Interface is a network-free provider skeleton. It
does not implement real external APIs, scraping, authentication, cookie
bypass, realtime requests, or order execution. Connectors produce normalized
local CSV/JSON files, and every connector attempt is stored in
`connector_runs` before optional handoff to the Unified Data Import Pipeline.

Default connectors are deterministic mocks:

- `mock_market_data`
- `mock_news_signal`
- `mock_dilution_signal`
- `mock_toss_signal`
- `mock_flow_signal`

```bash
python -m stock_risk_mcp.cli connectors
python -m stock_risk_mcp.cli run-connectors --db data/stock_risk_mcp.sqlite3 --as-of-date 2026-06-13 --output-dir data/connector_outputs --connector mock_market_data --connector mock_news_signal --ticker AAPL --ticker TSLA
python -m stock_risk_mcp.cli connector-runs --db data/stock_risk_mcp.sqlite3
python -m stock_risk_mcp.cli connector-show --db data/stock_risk_mcp.sqlite3 --connector-run-id <connector_run_id>
python -m stock_risk_mcp.cli run-connectors-and-import --db data/stock_risk_mcp.sqlite3 --as-of-date 2026-06-13 --output-dir data/connector_outputs --connector mock_market_data --connector mock_news_signal --ticker AAPL
```

Expected connector failures are recorded and do not stop later connectors. If
no connector output is available, `run-connectors-and-import` still creates a
failed ImportRun and returns traceable JSON. Future real providers can
implement the same `BaseConnector.fetch` contract while preserving normalized
file output and run recording.

### Public HTTP Data Connector

The Public HTTP Data Connector is an opt-in adapter for explicitly configured
public CSV/JSON URLs. Network access is OFF by default and requires
`--enable-network`. The default registry never auto-registers public HTTP
providers; they exist only when `--provider-config-file` is supplied.

Every initial URL and redirect target must use HTTP/HTTPS and exactly match a
configured `allowed_hosts` entry. Subdomains are not implicitly allowed. CLI
`--allowed-host` values further restrict the config allowlist by intersection.
URL usernames/passwords and credential-like headers such as `Authorization`,
`Cookie`, and `X-API-Key` are blocked. Logged URLs omit query strings and
fragments.

This layer does not support authentication, sessions, cookies, private API
keys, brokerage access, Toss or other login-based scraping, or order
execution. Download and validation failures are isolated in `ConnectorRun`
records. Tests use injected fake clients and make no external network calls.

Example provider config:

```json
{
  "providers": [
    {
      "provider_name": "sample_prices",
      "url": "https://example.com/prices.csv",
      "data_kind": "PRICE_HISTORY",
      "output_format": "CSV",
      "allowed_hosts": ["example.com"],
      "enabled": true
    }
  ]
}
```

```bash
python -m stock_risk_mcp.cli validate-provider-config --provider-config-file configs/providers.json
python -m stock_risk_mcp.cli run-http-connector --db data/stock_risk_mcp.sqlite3 --as-of-date 2026-06-13 --provider-config-file configs/providers.json --provider sample_prices --output-dir data/provider_outputs --enable-network
python -m stock_risk_mcp.cli run-connectors-and-import --db data/stock_risk_mcp.sqlite3 --as-of-date 2026-06-13 --output-dir data/provider_outputs --provider-config-file configs/providers.json --enable-network
```

Run `system-smoke` before attaching or enabling a real public provider:

```bash
python -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs
```

### Provider Normalization Layer

Provider files often use vendor-specific column names and shapes. The Provider
Normalization Layer converts already-downloaded Public HTTP or local CSV/JSON
files into the stable schemas accepted by Unified Import. Normalizers never
write business data directly to SQLite and never make network requests. They
create reproducible normalized files; `normalize-and-import` then passes only
successful outputs to the existing import pipeline.

Default generic normalizers:

- `generic-price-csv`
- `generic-news-csv`
- `generic-dilution-csv`
- `generic-flow-csv`
- `generic-fx-csv`

```bash
python -m stock_risk_mcp.cli normalize-file --db data/stock_risk_mcp.sqlite3 --normalizer generic-price-csv --input-file raw/provider_prices.csv --output-dir normalized --as-of-date 2026-06-13 --ticker-column Symbol --date-column Date --open-column Open --high-column High --low-column Low --close-column Close --volume-column Volume --save
python -m stock_risk_mcp.cli normalize-run --db data/stock_risk_mcp.sqlite3 --config-file configs/normalizers.json --output-dir normalized --as-of-date 2026-06-13 --save
python -m stock_risk_mcp.cli normalize-and-import --db data/stock_risk_mcp.sqlite3 --config-file configs/normalizers.json --output-dir normalized --as-of-date 2026-06-13
python -m stock_risk_mcp.cli normalize-runs --db data/stock_risk_mcp.sqlite3
python -m stock_risk_mcp.cli normalize-show --db data/stock_risk_mcp.sqlite3 --normalize-run-id <normalize_run_id>
```

Example config:

```json
{
  "sources": [
    {
      "normalizer": "generic-price-csv",
      "input_file": "raw/prices.csv",
      "output_name": "prices_normalized.csv",
      "columns": {
        "ticker": "Symbol",
        "date": "Date",
        "close": "Close",
        "volume": "Volume"
      }
    }
  ]
}
```

Price rows after `as_of_date` are skipped. Missing price `open`, `high`, or
`low` values use close and produce warnings; missing close or volume values are
row errors. Per-source failures are isolated and recorded in `NormalizeRun`.
Output names must be safe CSV/JSON file names and cannot escape `output_dir`.

Normalized FX data can be imported into `fx_rates` and consumed by the
FX-aware context described below. Validate a provider with a generic normalizer
and local fixtures before building a provider-specific adapter.

### FX-aware Portfolio / Risk Layer

The FX-aware layer lets an account-currency balance, such as KRW, drive the
existing USD paper-trading pipeline without changing max-loss-first sizing or
hard-risk rules. It builds a `PortfolioCurrencyContext`, converts account
equity and cash into trading currency, and passes those converted values to the
existing pipeline. Generated TradePlan, basket, paper, pipeline, report,
notification, and dashboard records retain both currency views.

FX lookup uses only manually supplied rates or stored `fx_rates` rows. No
external FX API or web request is made. Manual `--fx-rate` takes priority.
Database lookup uses the latest rate on or before `as_of_date` and can invert
the opposite pair. Rates older than `--max-fx-staleness-days` remain usable but
produce a WARNING. Missing FX preserves legacy trading-currency behavior,
leaves account-currency conversions null, and records a warning.

```bash
python -m stock_risk_mcp.cli fx-rates --db data/stock_risk_mcp.sqlite3 --base-currency USD --quote-currency KRW
python -m stock_risk_mcp.cli fx-latest --db data/stock_risk_mcp.sqlite3 --base-currency USD --quote-currency KRW --as-of-date 2026-06-13
python -m stock_risk_mcp.cli fx-convert --db data/stock_risk_mcp.sqlite3 --amount 100000 --from-currency KRW --to-currency USD --as-of-date 2026-06-13
python -m stock_risk_mcp.cli run-paper-pipeline --db data/stock_risk_mcp.sqlite3 --as-of-date 2026-06-13 --account-equity 10000000 --cash-available 5000000 --account-currency KRW --trading-currency USD --horizon-days 10
python -m stock_risk_mcp.cli run-paper-pipeline --db data/stock_risk_mcp.sqlite3 --as-of-date 2026-06-13 --account-equity 10000000 --cash-available 5000000 --account-currency KRW --trading-currency USD --fx-rate 1380 --fx-source-name manual --horizon-days 10
```

The default remains USD account / USD trading with rate 1.0. All outputs remain
paper-trading and research records, not investment advice or real orders.

## Analysis Report Layer

The Analysis Report Layer converts stored pipeline, candidate scan, basket,
paper result, policy evaluation, and alert evidence into deterministic
structured JSON and Markdown. It does not call an LLM or external API, request
realtime data, execute orders, guarantee investment performance, or encourage
a purchase. Reports are paper-trading and research summaries only.

```bash
python -m stock_risk_mcp.cli report-pipeline --db data/stock_risk_mcp.sqlite3 --pipeline-run-id <pipeline_run_id> --format markdown --language ko --save
python -m stock_risk_mcp.cli report-scan --db data/stock_risk_mcp.sqlite3 --scan-run-id <scan_run_id> --format json --save
python -m stock_risk_mcp.cli report-basket --db data/stock_risk_mcp.sqlite3 --basket-id <basket_id> --format markdown
python -m stock_risk_mcp.cli report-policy-suite --db data/stock_risk_mcp.sqlite3 --suite-id <suite_id> --format markdown
python -m stock_risk_mcp.cli reports --db data/stock_risk_mcp.sqlite3
python -m stock_risk_mcp.cli report-show --db data/stock_risk_mcp.sqlite3 --report-id <report_id>
```

Use `--output-file` to write the selected JSON or Markdown rendering. A file
write failure becomes a report warning and does not prevent report generation
or an independent `--save` to `analysis_reports`. Replay-only basket reports
explicitly warn when their basket may not exist in official `basket_plans`.
Stored paper results are reported when available; memory-only outcomes are
never reconstructed or estimated.

The deterministic `context_json` is suitable input for a future LLM/MCP agent,
but that future agent remains separate from this report builder.

## Adaptive Strategy Layer

Adaptive Strategy Layer는 저장된 Basket Paper Trading 성과를 이용해 soft
strategy policy의 후보를 만들고 실험 결과를 기록합니다. 실제 주문 기능이나 외부
API 호출은 없으며, 후보 정책은 기본적으로 `DRAFT`로 저장되고 자동으로
`ACTIVE`가 되지 않습니다.

Optimizer가 조정할 수 있는 범위:

- soft scoring weights
- A/B/C setup thresholds
- basket candidate 및 concentration rules
- basket allocation risk units와 허용 손실 한도

Optimizer가 절대 변경할 수 없는 hard block / safety rule:

- Nasdaq 미준수, 희석 위험, unknown dilution 차단
- 시장가, 마진, 옵션 허용 여부
- stop loss 비활성화
- 일일 최대 손실, 단일 포지션 한도, 최소 현금 비율

기본 정책 초기화 및 active 정책 조회:

```bash
python -m stock_risk_mcp.cli strategy-init --db data/stock_risk_mcp.sqlite3
python -m stock_risk_mcp.cli strategy-active --db data/stock_risk_mcp.sqlite3
```

결정론적 `DRAFT` 후보 생성:

```bash
python -m stock_risk_mcp.cli strategy-propose --db data/stock_risk_mcp.sqlite3 --n 5
```

저장된 전체 `basket_backtest_results`로 공통 성과 objective 계산:

```bash
python -m stock_risk_mcp.cli strategy-evaluate --db data/stock_risk_mcp.sqlite3 --policy-id default --version v1 --horizon-days 10
```

정책과 실험 기록 조회:

```bash
python -m stock_risk_mcp.cli strategy-policies --db data/stock_risk_mcp.sqlite3
python -m stock_risk_mcp.cli strategy-experiments --db data/stock_risk_mcp.sqlite3
```

현재 MVP는 `COMMON_OUTCOME_EVALUATION`만 구현합니다. 모든 정책이 같은 저장
basket 성과를 사용하므로, 결과는 후보 정책 간 실제 우열 검증이 아닙니다.
candidate policy를 과거 feature, indicator, trade plan, basket construction에
재적용하지 않습니다. `FEATURE_RESCORING`은 구현하지 않았으며, 진짜 정책별 성과
비교는 향후 Policy Replay Engine의 `FULL_POLICY_REPLAY`에서 수행해야 합니다.

`sample_count < 30`인 실험은 항상 `NEED_MORE_DATA`이며 정책을 승격하면 안 됩니다.
이 계층은 paper trading 기반 전략 실험 자동화일 뿐 실제 투자 성과를 보장하지
않습니다.

## Policy-aware Scoring Integration

StrategyPolicy를 현재 실행하는 Setup, TradePlan, Basket, Paper Trading
pipeline에 선택적으로 적용할 수 있습니다.

- 정책 옵션 없음: 기존 `FIXED_RULES` 동작 유지
- 정책 선택: `POLICY_WEIGHTED` setup/basket soft scoring 적용

active 정책으로 setup 분석:

```bash
python -m stock_risk_mcp.cli analyze-setup \
  --ticker SAFE \
  --price-history-file data/prices.csv \
  --db data/stock_risk_mcp.sqlite3 \
  --use-active-policy
```

명시적 정책으로 TradePlan 생성:

```bash
python -m stock_risk_mcp.cli create-trade-plan-and-save \
  --ticker SAFE \
  --price-history-file data/prices.csv \
  --db data/stock_risk_mcp.sqlite3 \
  --account-equity 10000 \
  --cash-available 5000 \
  --policy-id default \
  --policy-version v1
```

active 정책으로 BasketPlan 생성:

```bash
python -m stock_risk_mcp.cli build-basket-and-save \
  --db data/stock_risk_mcp.sqlite3 \
  --account-equity 10000 \
  --cash-available 5000 \
  --use-active-policy
```

정책은 setup indicator weight와 threshold, basket 후보 scoring, 후보 수와
집중도 설정, basket loss/notional limit, A/B/C risk unit에만 영향을 줍니다.
Basket weighted scoring은 decision component를 `0.40`으로 고정하고,
나머지 `0.60`을 `setup_grade_score`와 `risk_reward_score` 비율로 재분배합니다.
`BLOCK`과 `NO_TRADE` 후보는 weighted scoring 전에 차단됩니다.

StrategyPolicy는 Nasdaq 미준수, 희석 위험, 시장가/마진/옵션 허용, stop loss
비활성화, 일일 손실 한도, 단일 포지션 한도, 최소 현금 비율 같은 hard block과
safety rule을 변경할 수 없습니다.

정책 ID/version과 가능한 scoring mode는 SetupSignal, TradePlan, BasketPlan,
PaperTrade, BasketBacktestResult, StrategyMemory에 전달됩니다. 기존 SQLite
DB에는 nullable policy metadata 컬럼을 자동 추가합니다.

이 단계는 과거 데이터를 재구성하는 `FULL_POLICY_REPLAY`가 아닙니다. 선택한
정책을 현재 시점에 실행하는 pipeline에 적용하는 기능이며, 진짜 정책별 과거
성과 비교는 향후 Policy Replay Engine에서 구현해야 합니다.

## 안전 원칙

- 실제 주문 실행 기능 없음
- 시장가, 마진, 옵션 주문은 정책 필드로만 표현하며 MVP에서 실행하지 않음
- LLM은 제안자이고 Risk Engine이 최종 게이트
- `BLOCK` 결과는 초보자가 따라 사기 부적합한 제안으로 취급
## Local LLM Agent Bridge

The Local LLM Agent Bridge turns stored AnalysisReport and PipelineRun records
into read-only AgentContext, deterministic prompts, and deterministic briefs.
Its default backend is `DRY_RUN`, which generates the request without making an
HTTP call. Persistence is opt-in through `--save`.

The agent is explanation-only. Its tool manifest contains read-only lookup
tools, and it cannot place orders, approve or activate policies, change broker
settings, or modify hard-risk and safety rules.

`OLLAMA_LOCAL` and `OPENAI_COMPAT_LOCAL` are local-server-only backends.
Only `localhost`, `127.0.0.1`, and `::1` endpoint hosts are permitted. Any
non-local endpoint is blocked before HTTP transport with
`error="non-local endpoint blocked"`. This security policy prevents reports,
trading context, and prompts from being sent to external cloud endpoints.

```bash
python -m stock_risk_mcp.cli agent-context-from-report --db data/stock_risk_mcp.sqlite3 --report-id REPORT_ID --save
python -m stock_risk_mcp.cli agent-prompt --db data/stock_risk_mcp.sqlite3 --context-id CONTEXT_ID --save
python -m stock_risk_mcp.cli agent-brief --db data/stock_risk_mcp.sqlite3 --context-id CONTEXT_ID
python -m stock_risk_mcp.cli agent-run-local --db data/stock_risk_mcp.sqlite3 --prompt-id PROMPT_ID --backend dry-run
python -m stock_risk_mcp.cli agent-tools
```
## Alert Delivery / Notification Layer

The notification layer converts saved PipelineAlert, AnalysisReport,
AgentBrief, and LocalLLMResponse evidence into local paper-trading and research
alerts. It does not send external network requests, execute orders, or provide
investment advice.

Implemented delivery targets are `CONSOLE`, `LOCAL_FILE`, `MOCK`, and
`DISABLED`. Telegram, Discord, Slack, email, and webhook delivery remain
disabled placeholders for future interfaces. Local-file output writes Markdown
by default and JSONL when the output filename ends in `.jsonl`.

```bash
python -m stock_risk_mcp.cli notify-pipeline --db data/stock_risk_mcp.sqlite3 --pipeline-run-id PIPELINE_ID --channel local-file --output-file notifications/pipeline.md --min-severity warning --save
python -m stock_risk_mcp.cli notify-report --db data/stock_risk_mcp.sqlite3 --report-id REPORT_ID --channel console --save
python -m stock_risk_mcp.cli notify-brief --db data/stock_risk_mcp.sqlite3 --brief-id BRIEF_ID --channel local-file --output-file notifications/brief.md --save
python -m stock_risk_mcp.cli notify-local-response --db data/stock_risk_mcp.sqlite3 --response-id RESPONSE_ID --channel mock --save
python -m stock_risk_mcp.cli notify-digest --db data/stock_risk_mcp.sqlite3 --as-of-date 2026-06-13 --channel local-file --output-file notifications/daily.md --include-local-llm-responses --save
```

`run-paper-pipeline` and `watch-loop` support opt-in notification delivery with
`--notify`, `--notification-channel`, `--notification-output-file`, and
`--notification-min-severity`. Notification failures are recorded separately
and do not change the pipeline status.

```bash
python -m stock_risk_mcp.cli watch-loop --db data/stock_risk_mcp.sqlite3 --as-of-date 2026-06-13 --account-equity 10000 --cash-available 5000 --interval-seconds 60 --max-iterations 3 --notify --notification-channel local-file --notification-output-file notifications/watch.md
python -m stock_risk_mcp.cli notification-runs --db data/stock_risk_mcp.sqlite3
```

Saved `dedupe_key` values prevent repeated delivery. Local LLM notifications
contain at most a 500-character response preview; full responses remain in the
original local database record.
## Local Static Dashboard

The Local Dashboard layer generates self-contained UTF-8 HTML files from stored
paper-trading and research-monitoring records. It starts no web server, makes no
external network request, and uses no CDN, external JavaScript, CSS, or images.
Dashboards contain no order controls, investment advice, or performance
guarantees.

```bash
python -m stock_risk_mcp.cli dashboard-overview --db data/stock_risk_mcp.sqlite3 --output-file dashboard/overview.html --limit 20 --save
python -m stock_risk_mcp.cli dashboard-pipeline --db data/stock_risk_mcp.sqlite3 --pipeline-run-id PIPELINE_ID --output-file dashboard/pipeline.html --save
python -m stock_risk_mcp.cli dashboard-daily --db data/stock_risk_mcp.sqlite3 --as-of-date 2026-06-13 --output-file dashboard/daily.html --save
python -m stock_risk_mcp.cli dashboard-policy --db data/stock_risk_mcp.sqlite3 --output-file dashboard/policy.html --save
python -m stock_risk_mcp.cli run-paper-pipeline ... --build-dashboard --dashboard-output-file dashboard/pipeline.html
```

Generated files can be opened directly in a browser with
`start dashboard/overview.html`. An optional dependency-free smoke check is
available with `python scripts/preview_dashboard.py dashboard/overview.html`
and can attempt a local browser open with `--open`. Browser smoke is optional
and is not part of the required pytest or CI path.
## End-to-End Local Demo And Release Hardening

The deterministic local demo validates the complete mock/local workflow:
connectors, unified import, paper pipeline, analysis report, read-only agent
context and prompt, local LLM `DRY_RUN`, local-file notification, static
dashboard, and JSON summary.

It uses no external provider API, web request, scraping, or real order
execution. Demo results are system smoke/release validation results, not
investment advice.

```bash
python -m stock_risk_mcp.cli run-local-demo --db data/demo.sqlite3 --as-of-date 2026-06-13 --output-dir demo_outputs --ticker AAPL --ticker TSLA --ticker NVDA
python -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs
python -m stock_risk_mcp.cli release-check
```

`run-local-demo` records every stage as completed, skipped, or failed and writes
`demo_summary.json`, `notification.md`, `dashboard.html`, and `report.md`.
Expected step failures are returned as JSON without losing the location of the
failure. `release-check` prints recommended commands and a tag suggestion but
does not run verification commands or create a git tag.

Run `system-smoke` before attaching any future real provider adapter. A provider
adapter remains outside the deterministic local-demo security boundary.

## Provider Pack #1: Public Price And FX

The Price and FX Provider Pack connects the existing Safe HTTP Connector or a
local raw file to provider-specific normalization and append-only Unified
Import. One provider-pack JSON or YAML file is the single source for both
connector settings and the provider's `normalizer` and `columns`; there is no
separate normalizer-config option.

Network access remains off by default. Public HTTP providers run only with
`--enable-network` and only for allowed hosts. The pack adds no login,
credentials, cookies, sessions, scraping, broker API, or order execution.

```bash
python -m stock_risk_mcp.cli run-price-provider-pack --db data/stock_risk_mcp.sqlite3 --as-of-date 2026-06-13 --provider-pack-config configs/provider_pack.json --output-dir data/provider_outputs --enable-network
python -m stock_risk_mcp.cli run-fx-provider-pack --db data/stock_risk_mcp.sqlite3 --as-of-date 2026-06-13 --provider-pack-config configs/provider_pack.json --output-dir data/provider_outputs --enable-network
python -m stock_risk_mcp.cli run-price-fx-provider-pack --db data/stock_risk_mcp.sqlite3 --as-of-date 2026-06-13 --provider-pack-config configs/provider_pack.json --output-dir data/provider_outputs --enable-network
python -m stock_risk_mcp.cli provider-pack-runs --db data/stock_risk_mcp.sqlite3
python -m stock_risk_mcp.cli provider-pack-show --db data/stock_risk_mcp.sqlite3 --provider-pack-run-id PROVIDER_PACK_RUN_ID
```

Recommended workflow: run the Provider Pack, run `run-paper-pipeline` with the
desired account and trading currencies, build a local dashboard, and review
local notifications.

The combined pack treats price data as core. FX failure after successful price
import produces `PARTIAL`; a missing successful price import produces `FAILED`.
Provider pack records are operational audit evidence, not investment advice or
a performance guarantee.

## Provider Pack #2: News Public Data Adapter

The News Provider Pack reuses the same safe Provider Pack path for public or
local news exports:

```text
safe HTTP or local_file -> raw news -> provider normalizer -> Unified Import -> NEWS signal enrichment
```

`provider_pack_config` remains the single source for connector and normalizer
settings. There is no separate normalizer config file. External provider
configuration uses `columns.headline`; normalization maps it to the existing
internal signal field `title`.

```json
{
  "news": {
    "providers": [
      {
        "provider_name": "sample_news_provider",
        "url": "https://example.com/news.csv",
        "data_kind": "NEWS",
        "output_format": "CSV",
        "allowed_hosts": ["example.com"],
        "enabled": true,
        "normalizer": "generic-news-csv",
        "columns": {
          "ticker": "Symbol",
          "observed_at": "PublishedAt",
          "headline": "Headline",
          "source_name": "Source",
          "url": "Url",
          "sentiment": "Sentiment",
          "severity": "Severity",
          "summary": "Summary"
        }
      }
    ]
  }
}
```

Required news mappings are `ticker`, `observed_at`, `headline`, and
`source_name`. `INFO` severity is stored internally as `LOW`, while the
provider's original severity remains in `raw_payload_json`. The News Provider
Pack applies a conservative pack-specific score from +3 to -10. It does not
change common signal scoring.

```bash
python -m stock_risk_mcp.cli run-news-provider-pack --db data/stock_risk_mcp.sqlite3 --as-of-date 2026-06-13 --provider-pack-config configs/provider_pack.json --output-dir data/provider_outputs --enable-network
```

Public HTTP still requires explicit `--enable-network` and exact allowed-host
validation. Redirect targets are revalidated. Credentials, cookies, sessions,
authentication headers, private scraping, and Toss scraping are not supported.
`local_file` news providers run without network access.

Imported records are stored as NEWS signals and participate in the existing
scan and pipeline enrichment contract: critical negative signals exclude,
high negative signals downgrade INCLUDE to WATCH, and positive signals do not
promote an existing EXCLUDE candidate.

## Provider Pack #3: Dilution / Filings Public Data Adapter

The Dilution Provider Pack extends the same safe provider-pack pipeline:

```text
safe HTTP or local_file -> raw dilution/filings -> provider normalizer -> Unified Import -> DILUTION signal enrichment
```

`provider_pack_config` remains the single connector and normalizer config
source. There is no separate normalizer config file. Required dilution
mappings are `ticker`, `observed_at`, `event_type`, `dilution_risk`, and
`source_name`.

```json
{
  "dilution": {
    "providers": [
      {
        "provider_name": "sample_dilution_provider",
        "local_file": "data/dilution.csv",
        "data_kind": "DILUTION",
        "output_format": "CSV",
        "allowed_hosts": [],
        "enabled": true,
        "normalizer": "generic-dilution-csv",
        "columns": {
          "ticker": "Symbol",
          "observed_at": "ObservedAt",
          "event_type": "EventType",
          "dilution_risk": "DilutionRisk",
          "source_name": "Source"
        }
      }
    ]
  }
}
```

Provider Pack dilution scores are never positive: `NONE=0`, `LOW=-1`,
`MEDIUM=-3`, `HIGH=-7`, `CRITICAL=-10`, and conservative `UNKNOWN=-7`.
`UNKNOWN` is stored as HIGH severity while its original value remains in
`raw_payload_json`. This pack-specific mapping does not change common signal
scoring.

```bash
python -m stock_risk_mcp.cli run-dilution-provider-pack --db data/stock_risk_mcp.sqlite3 --as-of-date 2026-06-13 --provider-pack-config configs/provider_pack.json --output-dir data/provider_outputs
```

HTTP providers still require explicit `--enable-network` and exact
`allowed_hosts`; `local_file` providers use no network. The adapter adds no
credentials, cookies, sessions, private scraping, Toss scraping, orders, or
automatic trading.

Imported dilution records currently affect the Signal Enrichment path only:
HIGH/UNKNOWN negative signals downgrade INCLUDE to WATCH and CRITICAL negative
signals EXCLUDE. They are **not** automatically converted into
`CompanyRisk.dilution_risk`. Existing `block_dilution_high` and
`block_unknown_dilution` hard-risk rules remain unchanged, but the direct
Provider Pack signal-to-CompanyRisk bridge is future work.

## Provider Pack #4: Flow Public Data Adapter

The Flow Provider Pack imports public or local foreign and institution flow as
a conservative ranking and watching aid:

```text
safe HTTP or local_file -> raw flow -> provider normalizer -> Unified Import -> FOREIGN_INSTITUTION_FLOW signal enrichment
```

`flow.providers` uses the shared `provider_pack_config` as the single source
for connector, normalizer, and column mappings. There is no separate
`normalizer_config_file`. Required mappings are `ticker`, `observed_at`,
`source_name`, and at least one foreign/institution amount or shares field.

```json
{
  "flow": {
    "providers": [
      {
        "provider_name": "sample_flow_provider",
        "local_file": "data/flow.csv",
        "data_kind": "FOREIGN_INSTITUTION_FLOW",
        "output_format": "CSV",
        "allowed_hosts": [],
        "enabled": true,
        "normalizer": "generic-flow-csv",
        "columns": {
          "ticker": "Symbol",
          "observed_at": "ObservedAt",
          "source_name": "Source",
          "foreign_net_buy_amount": "ForeignNetBuyAmount",
          "institution_net_buy_amount": "InstitutionNetBuyAmount"
        }
      }
    ]
  }
}
```

If either amount mapping exists, the provider uses amount values for every
row. Shares are used only when no amount mapping exists. Missing selected
values are zero; rows never fall back from amount to shares.

The deterministic pack-specific score mapping is:

- both buy: `POSITIVE / LOW / +2`
- one buys and the other is zero or missing: `POSITIVE / LOW / +1`
- both sell: `NEGATIVE / MEDIUM / -3`
- one sells and the other is zero or missing: `NEGATIVE / LOW / -1`
- opposite signs or both zero/missing: `NEUTRAL / LOW / 0`

```bash
python -m stock_risk_mcp.cli run-flow-provider-pack --db data/stock_risk_mcp.sqlite3 --as-of-date 2026-06-13 --provider-pack-config configs/provider_pack.json --output-dir data/provider_outputs
```

HTTP providers require explicit `--enable-network` and exact `allowed_hosts`;
`local_file` providers use no network. Flow Provider Pack does not create
HIGH/CRITICAL signals by default, change common signal scoring, or add Risk
Engine hard-risk rules. Positive Flow alone cannot promote EXCLUDE or blocked
candidates. Flow is research and paper-trading support, not a buy instruction,
automatic trading signal, or real-order feature.
