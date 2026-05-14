#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${SMOKE_BASE_URL:-http://127.0.0.1:${API_PORT:-5001}}"

curl -fsS "${BASE_URL}/health"
