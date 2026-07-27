#!/bin/bash
# Activate the Gmail OAuth client (project: gmail-api-for-chat-llm).
# Run from the repo root, then restart the app.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/credentials_gmail.json" "$SCRIPT_DIR/credentials.json"
echo "Active OAuth client: GMAIL (gmail-api-for-chat-llm)"
echo "Restart the app to pick up the change."
