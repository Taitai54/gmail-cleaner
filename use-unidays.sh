#!/bin/bash
# Activate the UniDays OAuth client (project: totemic-beaker-493705-n2).
# Run from the repo root, then restart the app.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/credentials_unidays.json" "$SCRIPT_DIR/credentials.json"
echo "Active OAuth client: UNIDAYS (totemic-beaker-493705-n2)"
echo "Restart the app to pick up the change."
