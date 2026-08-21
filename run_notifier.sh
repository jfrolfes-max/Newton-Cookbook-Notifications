#!/bin/bash
# Wrapper for cron: loads credentials from a secrets file (not committed to git) and runs the notifier.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_FILE="$SCRIPT_DIR/secrets.env"

if [[ -f "$SECRETS_FILE" ]]; then
    set -a
    source "$SECRETS_FILE"
    set +a
fi

exec python3 "$SCRIPT_DIR/cookbook_notifier.py"
