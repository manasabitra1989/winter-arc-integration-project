#!/usr/bin/env bash

set -u

PROJECT_DIR="$HOME/winter-arc-integration-project"
LOG_FILE="$PROJECT_DIR/logs/server-health.log"
APP_URL="http://localhost:8080/health"
THRESHOLD=80

mkdir -p "$PROJECT_DIR/logs"

# Colors for terminal output
GREEN='\033[1;32m'
RED='\033[1;31m'
YELLOW='\033[1;33m'
RESET='\033[0m'

# Calculate CPU usage over 1 second
read -r _ u n s idle wait irq sirq steal _ < /proc/stat
total1=$((u+n+s+idle+wait+irq+sirq+steal))
idle1=$((idle+wait))

sleep 1

read -r _ u n s idle wait irq sirq steal _ < /proc/stat
total2=$((u+n+s+idle+wait+irq+sirq+steal))
idle2=$((idle+wait))

delta_total=$((total2-total1))
delta_idle=$((idle2-idle1))

if (( delta_total > 0 )); then
    CPU=$((100*(delta_total-delta_idle)/delta_total))
else
    CPU=0
fi

# Memory usage
MEMORY=$(free | awk '/^Mem:/ {printf "%.0f", $3/$2*100}')

# Root filesystem disk usage
DISK=$(df -P / | awk 'NR==2 {gsub("%","",$5); print $5}')

# Flask health check
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$APP_URL")

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "=========================================="
echo " OpsPulse Server Health Report"
echo "=========================================="
echo "Timestamp      : $TIMESTAMP"
echo "CPU Usage      : $CPU%"
echo "Memory Usage   : $MEMORY%"
echo "Disk Usage     : $DISK%"
echo "Application    : HTTP $HTTP_CODE"
echo "=========================================="

{
  echo "[$TIMESTAMP] CPU=$CPU% MEMORY=$MEMORY% DISK=$DISK% HTTP=$HTTP_CODE"
} >> "$LOG_FILE"

if (( CPU >= THRESHOLD || MEMORY >= THRESHOLD || DISK >= THRESHOLD )); then
    printf "${YELLOW}WARNING: Resource threshold exceeded!\n${RESET}"
fi

if [[ "$HTTP_CODE" == "200" ]]; then
    printf "${GREEN}Application Status: HEALTHY\n${RESET}"
else
    printf "${RED}Application Status: UNHEALTHY\n${RESET}"
    exit 1
fi
