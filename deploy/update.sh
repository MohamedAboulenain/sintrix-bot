#!/usr/bin/env bash
# Sintrix KNX Bot — Zero-downtime update script
# Pull latest code and rebuild the container.
# Usage: bash deploy/update.sh
set -euo pipefail

echo "=== Pulling latest changes ==="
git pull

echo "=== Rebuilding container ==="
docker compose up -d --build

echo "=== Pruning old images ==="
docker image prune -f

echo "=== Done. App status ==="
docker compose ps
