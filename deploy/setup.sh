#!/usr/bin/env bash
# Sintrix KNX Bot — First-time server setup script
# Run as root (or with sudo) on the production host.
# Usage: bash deploy/setup.sh
set -euo pipefail

echo "=== Sintrix KNX Bot — Server Setup ==="

# 1. Install Docker if missing
if ! command -v docker &>/dev/null; then
    echo "[1/5] Installing Docker…"
    curl -fsSL https://get.docker.com | sh
    systemctl enable --now docker
else
    echo "[1/5] Docker already installed."
fi

# 2. Install Docker Compose plugin if missing
if ! docker compose version &>/dev/null; then
    echo "[2/5] Installing Docker Compose plugin…"
    apt-get install -y docker-compose-plugin
else
    echo "[2/5] Docker Compose already installed."
fi

# 3. Install Nginx if missing
if ! command -v nginx &>/dev/null; then
    echo "[3/5] Installing Nginx…"
    apt-get update && apt-get install -y nginx
    systemctl enable nginx
else
    echo "[3/5] Nginx already installed."
fi

# 4. Verify .env exists
if [ ! -f .env ]; then
    echo "[4/5] ERROR: .env file not found. Copy .env.example → .env and fill in secrets."
    exit 1
else
    echo "[4/5] .env found."
fi

# 5. Authenticate NotebookLM (one-time browser login for Google)
echo "[5/5] NotebookLM authentication…"
if [ -f "$HOME/.notebooklm/storage_state.json" ]; then
    echo "      Auth token already present at ~/.notebooklm/storage_state.json — skipping login."
else
    echo "      Running 'notebooklm login' — a browser window will open for Google sign-in."
    echo "      If running headless, use SSH X11 forwarding: ssh -X user@server"
    pip install notebooklm-py playwright --quiet
    playwright install chromium
    notebooklm login
fi

echo ""
echo "=== Setup complete. Starting application ==="
docker compose up -d --build

echo ""
echo "App is running at http://localhost:8000"
echo "Configure Nginx: cp deploy/nginx.conf /etc/nginx/sites-available/sintrix-knx"
echo "                 ln -s /etc/nginx/sites-available/sintrix-knx /etc/nginx/sites-enabled/"
echo "                 nginx -t && systemctl reload nginx"
echo "Add SSL:         certbot --nginx -d sintrix.io -d www.sintrix.io"
