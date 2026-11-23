#!/bin/bash
set -e

echo "=== Mufti AI Cloud Startup ==="
echo "DEPLOY_MODE: ${DEPLOY_MODE:-local}"

# Ensure writable data directories exist
mkdir -p /app/data/feedback /app/data/saved

echo "Starting server on port ${PORT:-786}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-786}"
