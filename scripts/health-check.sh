#!/usr/bin/env bash

set -u

APP_URL="http://localhost:8080/health"
PROJECT_DIR="$HOME/winter-arc-integration-project"
LOG_FILE="$PROJECT_DIR/logs/health-check.log"

mkdir -p "$(dirname "$LOG_FILE")"

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

HTTP_CODE=$(curl -s -o /dev/null \
    -w "%{http_code}" \
    --connect-timeout 3 \
    --max-time 5 \
    "$APP_URL")

if [[ "$HTTP_CODE" == "200" ]]; then
    MESSAGE="[$TIMESTAMP] SUCCESS: OpsPulse is HEALTHY (HTTP $HTTP_CODE)"
    echo "$MESSAGE" | tee -a "$LOG_FILE"
    exit 0
else
    MESSAGE="[$TIMESTAMP] ERROR: OpsPulse is UNHEALTHY (HTTP $HTTP_CODE)"
    echo "$MESSAGE" | tee -a "$LOG_FILE"
    exit 1
fi
