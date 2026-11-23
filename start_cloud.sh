#!/bin/bash
# Startup script for cloud deployment
# Ensures data directories exist and copies cloud-index metadata if needed

set -e

echo "=== Mufti AI Cloud Startup ==="
echo "DEPLOY_MODE: ${DEPLOY_MODE:-local}"
echo "EMBEDDING_PROVIDER: ${EMBEDDING_PROVIDER:-ollama}"

# Create required directories
mkdir -p /app/data/books /app/data/feedback /app/data/saved

# If cloud-index has book-metadata, link it
if [ -d "/app/data/cloud-index/book-metadata" ] && [ ! -d "/app/data/book-metadata" ]; then
    ln -sf /app/data/cloud-index/book-metadata /app/data/book-metadata
    echo "Linked book-metadata from cloud-index"
fi

echo "Starting server on port ${PORT:-786}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-786}"
