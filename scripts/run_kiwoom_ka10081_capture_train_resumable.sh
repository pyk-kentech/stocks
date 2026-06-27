#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="${ROOT_DIR}/local_data/logs"
TOKEN_ROOT="${ROOT_DIR}/local_data/kiwoom_tokens"
STORE_ROOT="${ROOT_DIR}/local_data/historical_market_data/store"
RAW_LAKE_ROOT="${ROOT_DIR}/local_data/historical_market_data/raw_lake"
TRAINING_ROOT="${ROOT_DIR}/local_data/offline_strategy"

mkdir -p "${LOG_DIR}" "${TOKEN_ROOT}" "${STORE_ROOT}" "${RAW_LAKE_ROOT}" "${TRAINING_ROOT}"

: "${KIWOOM_ENVIRONMENT:=MOCK}"
: "${KIWOOM_CREDENTIAL_REF:=/home/yoonkeun/.secrets/kiwoom_mock_chart}"
: "${KIWOOM_SYMBOLS:=005930,000660}"
: "${KIWOOM_MAX_SYMBOLS_PER_RUN:=2}"
: "${KIWOOM_REQUEST_SLEEP_SECONDS:=0.25}"
: "${KIWOOM_SYMBOL_SLEEP_SECONDS:=0.50}"
: "${KIWOOM_API_ID:=KA10081}"
: "${KIWOOM_START_DATE:=2020-01-01}"
: "${KIWOOM_END_DATE:=2026-06-27}"
: "${KIWOOM_RESUME_STATE:=}"

OUTPUT_FILE="${LOG_DIR}/kiwoom_capture_train_${KIWOOM_ENVIRONMENT}_${TIMESTAMP}.json"

CMD=(
  python3.11 -m stock_risk_mcp.cli kiwoom-ka10081-capture-and-train-run
  --kiwoom-environment "${KIWOOM_ENVIRONMENT}"
  --credential-ref "${KIWOOM_CREDENTIAL_REF}"
  --token-store-root "${TOKEN_ROOT}"
  --api-id "${KIWOOM_API_ID}"
  --symbols "${KIWOOM_SYMBOLS}"
  --start-date "${KIWOOM_START_DATE}"
  --end-date "${KIWOOM_END_DATE}"
  --store-root "${STORE_ROOT}"
  --raw-lake-root "${RAW_LAKE_ROOT}"
  --training-output-root "${TRAINING_ROOT}"
  --strategy-families "MACD_RSI,RSI_OVERSOLD_REBOUND,VOLUME_LONG_CANDLE_PULLBACK,RANGE_BREAKOUT,ADX_TREND_SCALPING"
  --search-mode SMOKE_SEARCH
  --walk-forward-mode ANCHORED_CHRONOLOGICAL_WALK_FORWARD
  --promotion-profile STABILITY_FIRST
  --fill-policy CONSERVATIVE_NEXT_BAR_FILL
  --direction LONG_ONLY
  --max-request-count 500
  --max-continuation-pages 20
  --max-symbols-per-run "${KIWOOM_MAX_SYMBOLS_PER_RUN}"
  --request-sleep-seconds "${KIWOOM_REQUEST_SLEEP_SECONDS}"
  --symbol-sleep-seconds "${KIWOOM_SYMBOL_SLEEP_SECONDS}"
  --training-handoff-mode persisted_manifest
  --upd-stkpc-tp 1
  --allow-real-chart-capture
  --acknowledge-readonly-only
  --acknowledge-no-orders
  --acknowledge-user-initiated
  --acknowledge-rate-limit-and-capacity
  --acknowledge-credential-redaction
  --reuse-existing-raw-lake
  --stop-on-provider-limit
  --output-file "${OUTPUT_FILE}"
)

if [[ -n "${KIWOOM_RESUME_STATE}" ]]; then
  CMD+=(--resume-from-capture-state "${KIWOOM_RESUME_STATE}")
fi

echo "Running:"
printf ' %q' "${CMD[@]}"
echo

"${CMD[@]}"

if command -v jq >/dev/null 2>&1; then
  STATUS="$(jq -r '.status // ""' "${OUTPUT_FILE}")"
  STATE_PATH="$(jq -r '.capture_state_path // ""' "${OUTPUT_FILE}")"
else
  STATUS=""
  STATE_PATH=""
fi

if [[ "${STATUS}" == "COMPLETED_WITH_PROVIDER_LIMIT" || "${STATUS}" == "COMPLETED_WITH_PROVIDER_LIMIT_AND_PARTIAL_CACHE" || "${STATUS}" == "COMPLETED_WITH_PARTIAL_CACHE" || "${STATUS}" == "PARTIAL_CAPTURE_NO_TRAINING" ]]; then
  echo "Provider limit or partial capture detected."
  if [[ -n "${STATE_PATH}" && "${STATE_PATH}" != "null" ]]; then
    echo "Next resume command:"
    printf 'KIWOOM_RESUME_STATE=%q %q\n' "${STATE_PATH}" "${BASH_SOURCE[0]}"
  fi
  echo 'State lookup command:'
  echo 'find local_data -name "kiwoom_capture_state.json" -print'
fi
