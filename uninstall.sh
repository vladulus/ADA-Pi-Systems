#!/bin/bash

echo "=============================================="
echo "        ADA-PI SYSTEMS — UNINSTALLER"
echo "=============================================="
echo ""

SERVICE_NAME="ada-pi-backend.service"
INSTALL_PATH="/opt/ada-pi"
LOG_PATH="/var/log/ada-pi"
CF_CONFIG_DIR="/etc/cloudflared"
CF_RUN_DIR="/root/.cloudflared"
CF_SERVICE="/etc/systemd/system/cloudflared.service"

echo "[1/7] Stopping backend service..."
if systemctl is-active --quiet "$SERVICE_NAME"; then
    sudo systemctl stop "$SERVICE_NAME"
fi

echo "Disabling backend service..."
sudo systemctl disable "$SERVICE_NAME" >/dev/null 2>&1
sudo rm -f "/etc/systemd/system/$SERVICE_NAME"

echo ""
echo "[2/7] Removing ADA-PI installation..."
if [ -d "$INSTALL_PATH" ]; then
    sudo rm -rf "$INSTALL_PATH"
    echo "✔ Deleted $INSTALL_PATH"
else
    echo "Skipping — install directory not found."
fi

echo ""
echo "[3/7] Removing logs..."
if [ -d "$LOG_PATH" ]; then
    sudo rm -rf "$LOG_PATH"
    echo "✔ Logs removed ($LOG_PATH)"
else
    echo "Skipping — no logs found."
fi

echo ""
echo "=============================================="
echo "      Cloudflare Tunnel Removal (Optional)"
echo "=============================================="
echo ""

REMOVE_CF=false

if [ -d "$CF_CONFIG_DIR" ]; then
    echo "Cloudflare configuration detected."
fi

read -p "Do you want to remove Cloudflare Tunnel config? (yes/no): " REMOVE_CF_ANSWER
if [[ "$REMOVE_CF_ANSWER" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    REMOVE_CF=true
fi

if [ "$REMOVE_CF" = true ]; then
    echo "[4/7] Removing Cloudflare tunnel + config..."

    sudo systemctl stop cloudflared.service >/dev/null 2>&1 || true
    sudo systemctl disable cloudflared.service >/dev/null 2>&1 || true

    # Delete local Cloudflare configuration safely
    sudo rm -rf "$CF_CONFIG_DIR"
    sudo rm -rf "$CF_RUN_DIR"

    echo "✔ Cloudflare config removed"
else
    echo "Skipping Cloudflare removal."
fi

echo ""
echo "=============================================="
echo "       Tailscale Removal (Optional)"
echo "=============================================="
echo ""

read -p "Do you want to remove Tailscale? (yes/no): " REMOVE_TS_ANSWER
if [[ "$REMOVE_TS_ANSWER" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo "[5/7] Removing Tailscale..."
    sudo systemctl stop tailscaled 2>/dev/null || true
    sudo systemctl disable tailscaled 2>/dev/null || true
    sudo apt purge -y tailscale >/dev/null 2>&1 || true
    sudo rm -rf /var/lib/tailscale
    sudo rm -rf /etc/tailscale
    echo "✔ Tailscale removed"
else
    echo "Skipping Tailscale removal."
fi

echo ""
echo "[6/7] Reloading systemd..."
sudo systemctl daemon-reload

echo ""
echo "=============================================="
echo " OPTIONAL — Remove global Python packages?"
echo "=============================================="
echo ""
echo "Most ADA-PI dependencies are installed in a venv."
echo "Removing system-wide pip packages is usually not needed."
echo ""

read -p "Do you still want to remove old global Python deps? (yes/no): " REMOVE_PY
if [[ "$REMOVE_PY" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo "[7/7] Removing old global Python packages..."
    sudo pip3 uninstall -y paho-mqtt requests python-dotenv pyserial psutil websocket-client >/dev/null 2>&1
    echo "✔ Python dependencies removed"
else
    echo "Skipping — Python packages kept."
fi

echo ""
echo "=============================================="
echo "      ADA-PI SYSTEMS — UNINSTALL COMPLETE ✔"
echo "=============================================="
echo ""
