#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="${ROOT_DIR}/local_data/logs"
TOKEN_ROOT="${ROOT_DIR}/local_data/kiwoom_tokens"
STORE_ROOT="${ROOT_DIR}/local_data/historical_market_data/watchlist_store"
RAW_LAKE_ROOT="${ROOT_DIR}/local_data/historical_market_data/raw_lake"
TRAINING_ROOT="${ROOT_DIR}/local_data/offline_strategy"
STATE_ROOT="${ROOT_DIR}/local_data/historical_market_data/watchlist_capture_state"

mkdir -p "${LOG_DIR}" "${TOKEN_ROOT}" "${STORE_ROOT}" "${RAW_LAKE_ROOT}" "${TRAINING_ROOT}" "${STATE_ROOT}" "${ROOT_DIR}/local_data/watchlists"

: "${KIWOOM_ENVIRONMENT:=MOCK}"
: "${KIWOOM_SYMBOLS_FILE:=local_data/watchlists/kiwoom_v15_watchlist.txt}"
: "${KIWOOM_SYMBOLS:=}"
: "${KIWOOM_BATCH_SIZE:=2}"
: "${KIWOOM_BATCH_INDEX:=1}"
: "${KIWOOM_MAX_BATCHES:=}"
: "${KIWOOM_RESUME_STATE:=}"
: "${KIWOOM_REQUEST_SLEEP_SECONDS:=0.25}"
: "${KIWOOM_SYMBOL_SLEEP_SECONDS:=0.50}"

OUTPUT_FILE="${LOG_DIR}/kiwoom_watchlist_capture_train_${KIWOOM_ENVIRONMENT}_${TIMESTAMP}.json"

if [[ ! -f "${KIWOOM_SYMBOLS_FILE}" ]]; then
  cp "${ROOT_DIR}/examples/kiwoom_watchlist_sample.txt" "${KIWOOM_SYMBOLS_FILE}"
fi

CMD=(
  python3.11 -m stock_risk_mcp.cli kiwoom-ka10081-capture-and-train-run
  --kiwoom-environment "${KIWOOM_ENVIRONMENT}"
  --credential-ref "/home/yoonkeun/.secrets/kiwoom_mock_chart"
  --token-store-root "${TOKEN_ROOT}"
  --api-id "KA10081"
  --symbols-file "${KIWOOM_SYMBOLS_FILE}"
  --start-date "2020-01-01"
  --end-date "2026-06-27"
  --store-root "${STORE_ROOT}"
  --raw-lake-root "${RAW_LAKE_ROOT}"
  --training-output-root "${TRAINING_ROOT}"
  --strategy-families "MACD_RSI,RSI_OVERSOLD_REBOUND,VOLUME_LONG_CANDLE_PULLBACK,RANGE_BREAKOUT,ADX_TREND_SCALPING"
  --search-mode "SMOKE_SEARCH"
  --walk-forward-mode "ANCHORED_CHRONOLOGICAL_WALK_FORWARD"
  --promotion-profile "STABILITY_FIRST"
  --fill-policy "CONSERVATIVE_NEXT_BAR_FILL"
  --direction "LONG_ONLY"
  --batch-size "${KIWOOM_BATCH_SIZE}"
  --batch-index "${KIWOOM_BATCH_INDEX}"
  --capture-state-root "${STATE_ROOT}"
  --request-sleep-seconds "${KIWOOM_REQUEST_SLEEP_SECONDS}"
  --symbol-sleep-seconds "${KIWOOM_SYMBOL_SLEEP_SECONDS}"
  --reuse-existing-raw-lake
  --backfill-cache-gaps
  --prefer-full-coverage-training
  --stop-on-provider-limit
  --no-allow-training-on-partial-capture
  --training-handoff-mode "persisted_manifest"
  --upd-stkpc-tp "1"
  --allow-real-chart-capture
  --acknowledge-readonly-only
  --acknowledge-no-orders
  --acknowledge-user-initiated
  --acknowledge-rate-limit-and-capacity
  --acknowledge-credential-redaction
  --output-file "${OUTPUT_FILE}"
)

if [[ -n "${KIWOOM_SYMBOLS}" ]]; then
  CMD+=(--symbols "${KIWOOM_SYMBOLS}")
fi
if [[ -n "${KIWOOM_MAX_BATCHES}" ]]; then
  CMD+=(--max-batches "${KIWOOM_MAX_BATCHES}")
fi
if [[ -n "${KIWOOM_RESUME_STATE}" ]]; then
  CMD+=(--resume-from-capture-state "${KIWOOM_RESUME_STATE}")
fi

echo "Running:"
printf ' %q' "${CMD[@]}"
echo

"${CMD[@]}"

echo "Output log path: ${OUTPUT_FILE}"
echo 'Capture state find command:'
echo 'find local_data -name "kiwoom_capture_state.json" -print'

if command -v jq >/dev/null 2>&1; then
  STATUS="$(jq -r '.status // ""' "${OUTPUT_FILE}")"
  NEXT_RESUME="$(jq -r '.next_resume_command // ""' "${OUTPUT_FILE}")"
  if [[ -n "${NEXT_RESUME}" && "${NEXT_RESUME}" != "null" ]]; then
    echo "Next resume command:"
    echo "${NEXT_RESUME}"
  fi
  echo "Status: ${STATUS}"
fi
