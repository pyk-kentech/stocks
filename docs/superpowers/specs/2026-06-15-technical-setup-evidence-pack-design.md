# v3.2 Technical Setup Evidence Pack Design

## Scope

v3.2 adds an offline deterministic technical setup evidence layer. It reads
one explicitly selected local JSON OHLCV fixture, computes reproducible
technical features, scores technical evidence, and produces advisory
`A`, `B`, `C`, or `NO_TRADE` setup grades.

The output is evidence only. It does not create `StrategyDecision`,
`OrderIntent`, order drafts, trades, executions, or execution approvals. It
does not query SQLite, provider, realtime, broker, Kiwoom, account, order,
credential, token, PROD, or LIVE paths. Tests and system smoke use no external
network.

## Architecture

v3.2 uses only new pure modules:

- `technical_evidence_models.py` defines strict fixture and result models.
- `technical_evidence_fixture.py` reads and validates one exact local JSON
  fixture.
- `macd_features.py`, `rsi_features.py`, `ma_trend_features.py`,
  `hma_features.py`, `atr_features.py`, `volume_features.py`, and
  `divergence_features.py` contain deterministic feature calculations.
- `setup_evidence_scoring.py` classifies setup taxonomy and calculates
  component scores and grade caps.
- `technical_evidence_service.py` coordinates pure fixture-to-result
  calculation and optional local JSON output.

Existing `indicator_calculators.py`, `SetupGrader`, and their behavior remain
unchanged. No v3.2 core module imports database, repository, provider,
realtime, broker, Kiwoom, account, order, strategy decision, credential,
token, or network modules. No SQLite audit is added.

## Fixture Contract

The strict fixture is:

```json
{
  "schema_version": "3.2",
  "as_of_timestamp": "2026-01-01T16:00:00+00:00",
  "config": {},
  "series": [
    {
      "ticker": "ABC",
      "points": [
        {
          "timestamp": "2026-01-01T15:59:00+00:00",
          "open": 100,
          "high": 105,
          "low": 99,
          "close": 103,
          "volume": 100000
        }
      ]
    }
  ]
}
```

Validation requires:

- schema version exactly `3.2`
- timezone-aware `as_of_timestamp` and point timestamps
- strictly increasing points within each ticker
- unique ticker series
- positive OHLC values and non-negative volume
- `low <= open <= high` and `low <= close <= high`
- no point timestamp after `as_of_timestamp`
- no unknown fields

Invalid fixtures return JSON-safe validation errors. The loader reads only the
explicit path and does not discover files or inspect directories.

## Calculation Scope And Missing Data

Evidence is generated independently for each ticker at its latest fixture
point. The complete historical series is used only for deterministic
calculation. No future or external data is used.

Insufficient lookback makes the affected feature `null` or its state
`INSUFFICIENT_DATA`. Missing required OHLCV or fewer than 20 points produces
`NO_TRADE`. Evidence completeness and grade caps are:

- at least 200 points: complete evidence, no data-length grade cap
- 50-199 points: limited evidence, maximum grade `B`
- 20-49 points: sparse evidence, maximum grade `C`
- fewer than 20 points: `NO_TRADE`

## MACD Features

MACD uses close prices:

- fast EMA period 12
- slow EMA period 26
- signal EMA period 9
- each EMA seed is the first close
- `macd_line = ema12 - ema26`
- `macd_signal = ema9(macd_line)`
- `macd_histogram = macd_line - macd_signal`
- `macd_histogram_slope = latest histogram - previous histogram`
- `macd_histogram_acceleration = latest slope - previous slope`
- golden cross: previous MACD is at or below signal and current MACD is above
  signal
- dead cross: previous MACD is at or above signal and current MACD is below
  signal
- bullish reacceleration: current histogram, slope, and acceleration are all
  positive

The full MACD histogram series is retained internally for setup taxonomy and
divergence support but output exposes only safe normalized evidence fields.

## RSI Features

RSI uses period 14 with Wilder smoothing:

- seed average gain and loss from the first 14 close deltas
- subsequent averages use Wilder smoothing
- `rsi_level` is the latest RSI value
- reclaim: previous RSI is below 50 and current RSI is at or above 50
- loss: previous RSI is at or above 50 and current RSI is below 50
- overbought: RSI at or above 70
- oversold: RSI at or below 30

Insufficient RSI history produces null level and false crossing flags.

## MA And HMA Features

Simple moving averages use close prices:

- `ma20`, `ma50`, and `ma200`
- price-above flags compare latest close with each available MA
- alignment is `BULLISH` for `ma20 > ma50 > ma200`, `BEARISH` for
  `ma20 < ma50 < ma200`, `MIXED` otherwise, or `INSUFFICIENT_DATA`

HMA 100 is:

```text
WMA(2 * WMA(close, 50) - WMA(close, 100), 10)
```

`hma100_slope` is latest HMA minus previous HMA. Trend state is `FLAT` when
the absolute slope is at most `latest_close * 0.001`, otherwise `BULLISH` or
`BEARISH` by slope sign. Missing values produce `INSUFFICIENT_DATA`.

## ATR And Risk Features

ATR 14 uses true range and Wilder smoothing:

- `atr14` is the latest ATR
- `atr_stop_distance = 2 * atr14`
- `stop_distance_pct = atr_stop_distance / latest_close * 100`
- `stop_distance_pct > 12` is an excessive-risk hard technical block

Missing high or low values are rejected by strict fixture validation rather
than inferred.

## Volume Features

Volume baselines use the previous 20 points and exclude the latest point:

- `volume_ratio = latest volume / previous-20 average volume`
- `dollar_volume = latest close * latest volume`
- `dollar_volume_ratio = latest dollar volume / previous-20 average dollar
  volume`
- spike confirmation is true when either available ratio is at least 1.5
- dry-up warning is true when both available ratios are below 0.7

Zero baselines produce null ratios rather than division or inferred values.
No feature is named CVD. If an OHLCV-only directional approximation is later
added, it must be named `volume_pressure_proxy`.

## Divergence Features

Basic divergence uses close and RSI within the latest 20 points:

- a local swing low is lower than the point immediately left and right
- a local swing high is higher than the point immediately left and right
- bullish RSI divergence requires the latest two price swing lows to show a
  lower price low and their aligned RSI values to show a higher RSI low
- bearish RSI divergence requires the latest two price swing highs to show a
  higher price high and their aligned RSI values to show a lower RSI high

If aligned RSI values or two suitable swings are unavailable, the divergence
flag is false and an insufficient-evidence reason is recorded.

## Setup Taxonomy

Allowed setup types are:

- `ROSS_MOMENTUM_CROSS`
- `ROSS_PULLBACK_REACCELERATION`
- `TECHNICAL_NO_TRADE`

`ROSS_MOMENTUM_CROSS` requires:

- MACD golden cross or bullish reacceleration
- RSI at or above 50 or RSI reclaim
- volume spike confirmation
- MA and HMA trend are not bearish

`ROSS_PULLBACK_REACCELERATION` requires:

- positive MACD histogram history within the latest 10 points
- a later histogram weakening
- current bullish reacceleration
- RSI at or above 50 or RSI reclaim
- volume spike confirmation

If both setup patterns match, pullback reacceleration takes precedence because
it contains the more specific historical sequence. Otherwise the taxonomy is
`TECHNICAL_NO_TRADE`.

## Scoring And Grades

Each evidence result contains component scores, normalized reasons, warnings,
feature evidence, total score, taxonomy, and grade:

- trend: 0-30
- momentum: 0-30
- volume: 0-20
- risk: 0-20
- total: 0-100

Deterministic component policy:

- trend awards 15 for bullish MA alignment or 8 for mixed alignment, plus 10
  for bullish HMA or 5 for flat HMA, plus 5 when price is above MA20
- momentum awards 15 for golden cross, 12 for bullish reacceleration, 8 for
  RSI at or above 50, 5 for RSI reclaim, and up to 5 for bullish divergence,
  capped at 30
- volume awards 15 for spike confirmation or 5 for neutral available ratios,
  plus 5 when dollar volume ratio is at least 1, capped at 20; dry-up receives
  zero and a warning
- risk starts at 20, subtracts 10 when stop distance exceeds 8%, and becomes
  zero when stop distance exceeds 12%; bearish divergence subtracts 5

Grades are:

- `A` for total at least 80
- `B` for total at least 60
- `C` for total at least 40
- `NO_TRADE` below 40 or on a hard technical block

Hard technical blocks are insufficient core data, missing OHLCV, simultaneous
bearish MA alignment and bearish HMA, or excessive risk distance. Data-length
grade caps are applied after score thresholds.

Grades and scores are advisory evidence only. They do not create strategy
decisions, trade plans, OrderIntent, orders, or approvals.

## Result Models And JSON Output

Strict output models include:

- per-module feature evidence
- component scores
- setup taxonomy, grade, reasons, warnings
- ticker, evidence timestamp, fixture checksum, and safety metadata
- a top-level technical evidence pack result

`technical-evidence-run --fixture-file <path> [--output-file <path>]` reads the
explicit fixture and calculates evidence. Without an output file it prints the
strict JSON result. With an output file it writes the strict JSON result and
prints a safe summary containing output path, ticker count, and grades.

`technical-evidence-show --output-file <path>` reads exactly the selected
result JSON, validates it against the strict output model, and prints it. It
does not discover files or read SQLite.

## Safety And Testing

Source-level tests prove technical evidence core modules have no DB,
repository, provider, realtime, broker, Kiwoom, account, order,
StrategyDecision, credential, token, or network imports. The service reads
only explicit local fixture/result files.

Focused tests cover deterministic fixtures, strict validation, insufficient
data, known MACD/RSI/MA/HMA/ATR values, volume features, divergence, taxonomy,
component scoring, grade thresholds and caps, timestamp and as-of validation,
CLI JSON safety, and no-network system smoke.

System smoke creates a temporary timezone-aware OHLCV fixture and verifies
technical evidence calculation without DB/provider/realtime input or network
access. `external_network_calls=false` remains required.

## Future Boundaries

v3.2 intentionally excludes true CVD or trade-direction order flow, intrabar
execution, configurable indicator periods, SQLite audit, strategy integration,
trade-plan integration, order integration, broker or account paths, PROD, and
LIVE.

Future releases may separately define true order-flow data, configurable
calculation policies, evidence persistence, or strategy consumption without
weakening the pure evidence boundary.
