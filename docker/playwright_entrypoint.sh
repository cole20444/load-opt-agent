#!/bin/bash

# Playwright-based browser worker entrypoint for Azure distributed load testing

set -e

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

# Set up logging
LOG_FILE="/tmp/results/worker.log"
mkdir -p /tmp/results

# Parse environment variables
WORKER_INDEX=${WORKER_INDEX:-0}
WORKER_COUNT=${WORKER_COUNT:-1}
TOTAL_VUS=${TOTAL_VUS:-10}
DURATION=${DURATION:-2m}
RUN_ID=${RUN_ID:-test}
TARGET_URL=${TARGET_URL:-https://example.com}

# Calculate VUs for this worker
K6_VUS=$((TOTAL_VUS / WORKER_COUNT))
if [ $WORKER_INDEX -eq $((WORKER_COUNT - 1)) ]; then
    # Last worker gets any remaining VUs
    K6_VUS=$((TOTAL_VUS - (WORKER_INDEX * K6_VUS)))
fi

# Convert duration to minutes
DURATION_MINUTES=2
if [[ "$DURATION" == *"m" ]]; then
    DURATION_MINUTES=${DURATION%m}
elif [[ "$DURATION" == *"s" ]]; then
    DURATION_SECONDS=${DURATION%s}
    DURATION_MINUTES=$((DURATION_SECONDS / 60))
    if [ $DURATION_MINUTES -eq 0 ]; then
        DURATION_MINUTES=1
    fi
fi

# Set output file
OUTPUT_FILE="/tmp/results/playwright_results_${WORKER_INDEX}.json"

log "=== Playwright Browser Worker Started ==="
log "Worker Index: ${WORKER_INDEX}"
log "Worker Count: ${WORKER_COUNT}"
log "Total VUs: ${TOTAL_VUS}"
log "Duration: ${DURATION} (${DURATION_MINUTES} minutes)"
log "Run ID: ${RUN_ID}"
log "VUs for this worker: ${K6_VUS}"
log "Target URL: ${TARGET_URL}"
log "Output file: ${OUTPUT_FILE}"

# Upload function
upload_to_blob() {
    local file_path="$1"
    local blob_name="$2"
    
    if [ -f "$file_path" ]; then
        log "Uploading $file_path to $blob_name"
        az storage blob upload \
            --account-name "${STORAGE_ACCOUNT}" \
            --container-name "${CONTAINER_NAME}" \
            --file "$file_path" \
            --name "$blob_name" \
            --connection-string "${AZURE_STORAGE_CONNECTION_STRING}" \
            --overwrite || log "WARNING: Upload failed for $blob_name"
    else
        log "WARNING: File $file_path not found for upload"
    fi
}

# Cleanup function
cleanup() {
    log "=== Cleanup Started ==="
    upload_to_blob "${LOG_FILE}" "${RUN_ID}/worker_${WORKER_INDEX}.log" || true
    log "=== Cleanup Completed ==="
}

# Set up cleanup trap
trap cleanup EXIT

log "=== Starting Playwright Browser Test ==="

# Set environment variables for the Python script
export TARGET_URL="${TARGET_URL}"
export DURATION_MINUTES="${DURATION_MINUTES}"
export VUS="${K6_VUS}"
export OUTPUT_FILE="${OUTPUT_FILE}"

# Run the Playwright test
log "Running Playwright test with ${K6_VUS} VUs for ${DURATION_MINUTES} minutes"
set +e
python3 /app/playwright_browser_test.py
EXIT_CODE=$?
set -e

log "Playwright test completed with exit code: ${EXIT_CODE}"

# Upload results
if [ -f "${OUTPUT_FILE}" ]; then
    log "✅ Playwright results generated: ${OUTPUT_FILE}"
    upload_to_blob "${OUTPUT_FILE}" "${RUN_ID}/playwright_results_${WORKER_INDEX}.json"
    
    # Also create a completion marker
    echo "completed" > "/tmp/results/completion_${WORKER_INDEX}.txt"
    upload_to_blob "/tmp/results/completion_${WORKER_INDEX}.txt" "${RUN_ID}/completion_${WORKER_INDEX}.txt"
else
    log "❌ Playwright test failed to generate results"
    exit 1
fi

log "=== Playwright Browser Worker Completed ==="
exit ${EXIT_CODE}
