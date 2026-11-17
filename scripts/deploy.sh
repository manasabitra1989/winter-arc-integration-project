#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT="$HOME/winter-arc-integration-project"
APP="$PROJECT/app/app.py"
PYTHON="$PROJECT/app/.venv/bin/python"
RELEASE="$PROJECT/releases/app-v2.py"
BACKUP_DIR="$PROJECT/backups"
HEALTH_URL="http://127.0.0.1:8080/health"
SERVICE="opspulse"

mkdir -p "$BACKUP_DIR"

# Check required files
[[ -f "$APP" ]] || { echo "ERROR: Application missing"; exit 1; }
[[ -f "$RELEASE" ]] || { echo "ERROR: Release missing"; exit 1; }
[[ -x "$PYTHON" ]] || { echo "ERROR: Python missing"; exit 1; }

# Validate Python syntax
"$PYTHON" -m py_compile "$RELEASE"

# Ensure current application is healthy
if ! systemctl is-active --quiet "$SERVICE"; then
    echo "ERROR: Service is not running."
    exit 1
fi

if ! curl -fsS --max-time 5 "$HEALTH_URL" > /dev/null; then
    echo "ERROR: Current application is unhealthy."
    exit 1
fi

# Backup current application
BACKUP="$BACKUP_DIR/app-$(date +%Y%m%d-%H%M%S)-$$.py"
cp -p "$APP" "$BACKUP"

echo "Backup created: $BACKUP"
echo "Deploying OpsPulse..."

# Function to verify application health
check_health() {
    local attempt http_code

    for attempt in {1..10}; do
        http_code=$(curl -s -o /dev/null -w '%{http_code}' \
            --max-time 3 "$HEALTH_URL" || true)

        if systemctl is-active --quiet "$SERVICE" &&
           [[ "$http_code" == "200" ]]; then
            return 0
        fi

        echo "Health check $attempt/10: HTTP $http_code"
        sleep 2
    done

    return 1
}

# Deploy release
cp "$RELEASE" "$APP"

if ! sudo systemctl restart "$SERVICE"; then
    echo "WARNING: Deployment restart failed."
fi

# Verify new release
if check_health; then
    echo "SUCCESS: OpsPulse deployment completed!"
    echo "Backup: $BACKUP"
    exit 0
fi

# Automatic rollback
echo "FAILED: Deployment unhealthy. Rolling back..."
cp "$BACKUP" "$APP"

if ! sudo systemctl restart "$SERVICE"; then
    echo "WARNING: Rollback restart failed."
fi

if check_health; then
    echo "ROLLBACK SUCCESSFUL: Previous version restored."
else
    echo "CRITICAL: Rollback verification failed!"
    sudo journalctl -u "$SERVICE" -n 15 --no-pager
fi

exit 1
