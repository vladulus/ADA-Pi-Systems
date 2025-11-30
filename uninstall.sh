#!/bin/bash

echo "=============================================="
echo "      ADA-PI SYSTEMS — UNINSTALL SCRIPT"
echo "=============================================="
echo ""

SERVICE_NAME="ada-pi-backend.service"
INSTALL_PATH="/opt/ada-pi"
TUNNEL_NAME_FILE="/etc/cloudflared/ada-pi-tunnel-name"
SYSTEMD_TUNNEL_SERVICE="/etc/systemd/system/cloudflared.service"

# ------------------------------------------------------------
# 1) STOP + DISABLE ADA-PI BACKEND SERVICE
# ------------------------------------------------------------
echo "[1/6] Stopping backend service..."
if systemctl is-active --quiet "$SERVICE_NAME"; then
    sudo systemctl stop "$SERVICE_NAME"
fi

echo "Disabling backend service..."
sudo systemctl disable "$SERVICE_NAME" >/dev/null 2>&1
sudo rm -f "/etc/systemd/system/$SERVICE_NAME"

# ------------------------------------------------------------
# 2) REMOVE INSTALLATION DIRECTORY
# ------------------------------------------------------------
echo "[2/6] Removing installed backend from $INSTALL_PATH..."

if [ -d "$INSTALL_PATH" ]; then
    sudo rm -rf "$INSTALL_PATH"
    echo "✔ Deleted $INSTALL_PATH"
else
    echo "Skipping — Install directory not found."
fi

# ------------------------------------------------------------
# 3) REMOVE LOG DIRECTORY
# ------------------------------------------------------------
LOG_PATH="/var/log/ada-pi"
echo "[3/6] Cleaning logs ($LOG_PATH)..."

if [ -d "$LOG_PATH" ]; then
    sudo rm -rf "$LOG_PATH"
    echo "✔ Logs removed"
else
    echo "Skipping — log directory not found."
fi

# ------------------------------------------------------------
# 4) ASK IF CLOUDFARE TUNNEL SHOULD BE REMOVED
# ------------------------------------------------------------
echo ""
echo "=============================================="
echo "      Cloudflare Tunnel Removal (Optional)"
echo "=============================================="
echo ""

REMOVE_CF=false

if [ -f "$TUNNEL_NAME_FILE" ]; then
    CF_TUNNEL_NAME=$(cat "$TUNNEL_NAME_FILE")
    echo "Cloudflare tunnel detected: $CF_TUNNEL_NAME"
else
    CF_TUNNEL_NAME=""
fi

read -p "Do you want to remove Cloudflare Tunnel? (yes/no): " REMOVE_CF_ANSWER

if [[ "$REMOVE_CF_ANSWER" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    REMOVE_CF=true
fi

if [ "$REMOVE_CF" = true ]; then
    echo "[4/6] Removing Cloudflare tunnel and config..."

    sudo systemctl stop cloudflared.service >/dev/null 2>&1
    sudo systemctl disable cloudflared.service >/dev/null 2>&1
    sudo rm -f "$SYSTEMD_TUNNEL_SERVICE"

    # Tunnel config directory
    if [ -d "/etc/cloudflared" ]; then
        sudo rm -rf /etc/cloudflared
    fi

    # Tunnel binary
    if command -v cloudflared >/dev/null 2>&1; then
        sudo rm -f "$(command -v cloudflared)"
    fi

    echo "✔ Cloudflare Tunnel removed"
else
    echo "Skipping — Cloudflare Tunnel kept."
fi

# ------------------------------------------------------------
# 5) CLEAN SYSTEMD
# ------------------------------------------------------------
echo ""
echo "[5/6] Reloading systemd daemon..."
sudo systemctl daemon-reload

# ------------------------------------------------------------
# 6) OPTIONAL: REMOVE UNUSED PYTHON DEPENDENCIES
# ------------------------------------------------------------
read -p "Do you want to uninstall unused Python packages installed by ADA-PI? (yes/no): " REMOVE_PY

if [[ "$REMOVE_PY" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo "[6/6] Removing Python packages..."

    sudo pip3 uninstall -y websockets aiohttp pyserial requests paho-mqtt python-dotenv pyudev dbus-python > /dev/null 2>&1

    echo "✔ Python dependencies removed"
else
    echo "Skipping — keeping Python packages."
fi

echo ""
echo "=============================================="
echo " ADA-PI SYSTEMS — UNINSTALL COMPLETE ✔"
echo "=============================================="
echo ""
