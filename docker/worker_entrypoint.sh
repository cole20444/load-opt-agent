#!/bin/bash
# Worker Container Entrypoint for Azure Distributed Load Testing
# Protocol (HTTP) or Browser tests. Logs go to stdout (ACI logs) AND /tmp/results/worker.log.

set -euo pipefail

# ---------- Paths & Logging ----------
OUTPUT_DIR="/tmp/results"
LOG_FILE="${OUTPUT_DIR}/worker.log"
K6_CONSOLE_LOG="${OUTPUT_DIR}/k6.console.log"

mkdir -p "${OUTPUT_DIR}"
# Create files up front so you can ls/cat them even if the test crashes early
touch "${LOG_FILE}" "${K6_CONSOLE_LOG}"

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $*" | tee -a "${LOG_FILE}"; }

log "=== SCRIPT STARTED ==="
log "whoami=$(whoami) uid=$(id -u) gid=$(id -g)"
log "pwd=$(pwd)"
log "ENTRYPOINT SHA=$(sha256sum /app/worker_entrypoint.sh 2>/dev/null || echo 'n/a')"

# ---------- Environment ----------
WORKER_INDEX=${WORKER_INDEX:-0}
WORKER_COUNT=${WORKER_COUNT:-1}
TOTAL_VUS=${TOTAL_VUS:-10}
DURATION=${DURATION:-1m}
RUN_ID=${RUN_ID:-test}
TEST_TYPE=${TEST_TYPE:-protocol}     # protocol | browser
VUS=${VUS:-10}
TARGET_URL=${TARGET_URL:-https://example.com}

# Azure Blob Storage configuration
STORAGE_ACCOUNT=${STORAGE_ACCOUNT:-}
CONTAINER_NAME=${CONTAINER_NAME:-results}
AZURE_STORAGE_CONNECTION_STRING=${AZURE_STORAGE_CONNECTION_STRING:-}

# Test env (⚠️ K6_* can override scenarios; we will avoid them for browser runs)
K6_VUS=${K6_VUS:-$VUS}
K6_DURATION=${K6_DURATION:-$DURATION}
K6_OUT=${K6_OUT:-summary_${WORKER_INDEX}.json}

# Browser env (not heavily used here but kept for future)
BROWSER_TIMEOUT=${BROWSER_TIMEOUT:-30s}
BROWSER_VIEWPORT_WIDTH=${BROWSER_VIEWPORT_WIDTH:-1920}
BROWSER_VIEWPORT_HEIGHT=${BROWSER_VIEWPORT_HEIGHT:-1080}

log "=== Worker Container Started ==="
log "Worker Index: ${WORKER_INDEX}/${WORKER_COUNT}  Run ID: ${RUN_ID}"
log "Test Type: ${TEST_TYPE}  Target URL: ${TARGET_URL}"
log "Total VUs: ${TOTAL_VUS}  Duration: ${DURATION}  VUs(this worker): ${VUS}"
log "Storage: account='${STORAGE_ACCOUNT}' container='${CONTAINER_NAME}'"
log "OUTPUT_DIR: ${OUTPUT_DIR}"

# Show K6_* envs (helps debug unexpected overrides)
log "K6_* envs:"
env | grep -E '^K6_' | tee -a "${LOG_FILE}" || true

# ---------- Validation ----------
if [ -z "${STORAGE_ACCOUNT}" ] && [ -z "${AZURE_STORAGE_CONNECTION_STRING}" ]; then
  log "ERROR: STORAGE_ACCOUNT or AZURE_STORAGE_CONNECTION_STRING is required"
  exit 1
fi
if [ -z "${CONTAINER_NAME}" ]; then
  log "ERROR: CONTAINER_NAME is required"
  exit 1
fi

cd "${OUTPUT_DIR}"
log "ls -la ${OUTPUT_DIR}:"
ls -la "${OUTPUT_DIR}" | tee -a "${LOG_FILE}"

# ---------- Upload helper ----------
upload_to_blob() {
  local file_path="$1"
  local blob_name="$2"

  if [ ! -f "$file_path" ]; then
    log "WARNING: File not found: $file_path"
    return 1
  fi

  log "Uploading '$file_path' -> '${blob_name}'"
  if [ -n "${AZURE_STORAGE_CONNECTION_STRING}" ]; then
    az storage blob upload \
      --connection-string "${AZURE_STORAGE_CONNECTION_STRING}" \
      --container-name "${CONTAINER_NAME}" \
      --name "${blob_name}" \
      --file "${file_path}" \
      --overwrite | tee -a "${LOG_FILE}"
  else
    az storage blob upload \
      --account-name "${STORAGE_ACCOUNT}" \
      --container-name "${CONTAINER_NAME}" \
      --name "${blob_name}" \
      --file "${file_path}" \
      --auth-mode login \
      --overwrite | tee -a "${LOG_FILE}"
  fi
}

# ---------- Always upload logs on exit ----------
cleanup() {
  log "=== CLEANUP (EXIT) ==="
  if [ -s "${LOG_FILE}" ]; then
    upload_to_blob "${LOG_FILE}" "${RUN_ID}/worker_${WORKER_INDEX}.log" || true
  fi
  if [ -s "${K6_CONSOLE_LOG}" ]; then
    upload_to_blob "${K6_CONSOLE_LOG}" "${RUN_ID}/k6_console_${WORKER_INDEX}.log" || true
  fi
  if [ -f "${OUTPUT_DIR}/${K6_OUT}" ]; then
    local sz
    sz=$(wc -c < "${OUTPUT_DIR}/${K6_OUT}" 2>/dev/null || echo 0)
    log "Result present: ${K6_OUT} (${sz} bytes)"
  fi
}
trap cleanup EXIT

# ---------- Protocol test ----------
run_protocol_test() {
  log "=== Running Protocol Test ==="

  if [ ! -f /app/load_test.js ]; then
    log "ERROR: /app/load_test.js not found in image"
    return 1
  fi
  cp /app/load_test.js /tmp/load_test.js

  # Replace all occurrences of hardcoded values with environment variables
  sed -i "s|__ENV.TARGET_URL|'${TARGET_URL}'|g" /tmp/load_test.js || true
  
  # Replace simple VU and duration configuration
  sed -i "s|vus: [0-9]\+|vus: ${K6_VUS}|g" /tmp/load_test.js || true
  sed -i "s|duration: '[0-9]\+[sm]'|duration: '${K6_DURATION}'|g" /tmp/load_test.js || true

  # Extract filename from K6_OUT (remove json= prefix if present)
  local output_file
  if [[ "${K6_OUT}" == json=* ]]; then
    output_file="${K6_OUT#json=}"
  else
    output_file="${K6_OUT}"
  fi

  log "About to run: k6 run --out json=${output_file} /tmp/load_test.js"
  set +e
  k6 run --out json="${output_file}" /tmp/load_test.js | tee -a "${K6_CONSOLE_LOG}"
  local exit_code=${PIPESTATUS[0]}
  set -e
  log "k6 exit code (protocol): ${exit_code}"

  if [ -f "${output_file}" ]; then
    log "✅ Protocol output exists: ${output_file}"
    upload_to_blob "${output_file}" "${RUN_ID}/summary_${WORKER_INDEX}.json" || log "WARNING: upload failed"
    [ -f "k6-summary.json" ] && upload_to_blob "k6-summary.json" "${RUN_ID}/metrics_${WORKER_INDEX}.json" || true
    return ${exit_code}
  else
    log "❌ Protocol test produced no output file"
    log "Current directory: $(pwd)"
    log "Files in current directory:"
    ls -la | tee -a "${LOG_FILE}"
    log "Looking for file: ${output_file}"
    return 1
  fi
}

# ---------- Browser test ----------
run_browser_test() {
  log "=== Running Browser Test ==="

  if [ ! -f /app/browser_load_test.js ]; then
    log "ERROR: /app/browser_load_test.js not found in image"
    return 1
  fi
  cp /app/browser_load_test.js /tmp/browser_test.js

  # Replace hardcoded values with environment variables
  sed -i "s|__ENV.TARGET_URL|'${TARGET_URL}'|g" /tmp/browser_test.js || true
  sed -i "s|vus: [0-9]\+|vus: ${K6_VUS}|g" /tmp/browser_test.js || true
  sed -i "s|duration: '[0-9]\+[sm]'|duration: '${K6_DURATION}'|g" /tmp/browser_test.js || true
  sed -i "s|iterations: [0-9]\+|iterations: ${K6_VUS}|g" /tmp/browser_test.js || true

  # Extract filename from K6_OUT (remove json= prefix if present)
  local output_file
  if [[ "${K6_OUT}" == json=* ]]; then
    output_file="${K6_OUT#json=}"
  else
    output_file="${K6_OUT}"
  fi

  log "About to run: k6 run --out json=${output_file} /tmp/browser_test.js"
  set +e
  k6 run --out json="${output_file}" /tmp/browser_test.js | tee -a "${K6_CONSOLE_LOG}"
  local exit_code=${PIPESTATUS[0]}
  set -e
  log "k6 exit code (browser): ${exit_code}"

  if [ -f "${output_file}" ]; then
    log "✅ Browser output exists: ${output_file}"
    upload_to_blob "${output_file}" "${RUN_ID}/summary_${WORKER_INDEX}.json" || log "WARNING: upload failed"
    [ -f "k6-summary.json" ] && upload_to_blob "k6-summary.json" "${RUN_ID}/metrics_${WORKER_INDEX}.json" || true
    return ${exit_code}
  else
    log "❌ Browser test produced no output file"
    log "Current directory: $(pwd)"
    log "Files in current directory:"
    ls -la | tee -a "${LOG_FILE}"
    log "Looking for file: ${output_file}"
    return 1
  fi
}

# ---------- Main ----------
log "Starting test execution…"
case "${TEST_TYPE}" in
  protocol) run_protocol_test; exit_code=$? ;;
  browser)  run_browser_test;  exit_code=$? ;;
  *)
    log "ERROR: Unknown TEST_TYPE='${TEST_TYPE}' (expected 'protocol' or 'browser')"
    exit_code=1
    ;;
esac

# Completion marker
echo "completed" > "${OUTPUT_DIR}/completion_${WORKER_INDEX}.txt"
upload_to_blob "${OUTPUT_DIR}/completion_${WORKER_INDEX}.txt" "${RUN_ID}/completion_${WORKER_INDEX}.txt" || true

log "=== Worker Container Finished === (exit ${exit_code})"
exit ${exit_code}
