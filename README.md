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

## 안전 원칙

- 실제 주문 실행 기능 없음
- 시장가, 마진, 옵션 주문은 정책 필드로만 표현하며 MVP에서 실행하지 않음
- LLM은 제안자이고 Risk Engine이 최종 게이트
- `BLOCK` 결과는 초보자가 따라 사기 부적합한 제안으로 취급
