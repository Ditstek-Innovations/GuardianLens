#!/usr/bin/env bash
# Workaround: run the entire startup with sudo to maintain docker access
set -euo pipefail
cd "$(dirname "$0")"

echo "Attempting to start GuardianLens with Docker (using sudo for full startup)..."
echo ""

# Run the entire startup script with sudo to maintain docker permissions
sudo bash scripts/run_dev.sh
