#!/usr/bin/env bash
set -euo pipefail

echo "-------------------------------------------"
echo " ADA-Pi Installer (Tailscale version)"
echo "-------------------------------------------"

INSTALL_USER="${SUDO_USER:-$USER}"
INSTALL_HOME="$(getent passwd "$INSTALL_USER" | cut -d: -f6)"

# Ask headless or kiosk with validation
MODE=""
while [[ "$MODE" != "1" && "$MODE" != "2" ]]; do
  echo "Choose mode:"
  echo "1) Headless (no display)"
  echo "2) Kiosk (autostart Chromium)"
  read -r -p "Enter 1 or 2: " MODE
  if [[ "$MODE" != "1" && "$MODE" != "2" ]]; then
    echo "Please enter 1 for Headless or 2 for Kiosk."
  fi
done

# Ensure system is updated
echo "[1/11] Updating system…"
sudo apt update -y
sudo apt upgrade -y

# Install system dependencies
echo "[2/11] Installing system dependencies…"
sudo apt install -y \
    python3 python3-pip python3-venv python3-full \
    git curl wget \
    libatlas-base-dev \
    libffi-dev build-essential \
    python3-serial python3-websocket python3-requests \
    xdotool unclutter chromium-browser \
    modemmanager usb-modeswitch \
    i2c-tools python3-smbus \
    python3-dbus python3-gi \
    bluez bluetooth \
    pkg-config libgirepository1.0-dev

# Enable interfaces and permissions if available
echo "[3/11] Enabling hardware interfaces and permissions…"
if command -v raspi-config >/dev/null 2>&1; then
  sudo raspi-config nonint do_i2c 0 || true
fi
sudo usermod -aG dialout,i2c "$INSTALL_USER"

# Setup ADA-Pi folders
echo "[4/11] Preparing directories…"
sudo mkdir -p /opt/ada-pi
sudo chown "$INSTALL_USER":"$INSTALL_USER" /opt/ada-pi
cp -r backend frontend /opt/ada-pi/

echo "[4b/11] Writing default config…"
sudo mkdir -p /etc/ada_pi
sudo tee /etc/ada_pi/config.json > /dev/null <<'CONFIG'
{
    "network": {
        "wifi_country": "GB"
    },
    "ups": {
        "shutdown_enabled": true,
        "shutdown_threshold": 20
    },
    "tacho": {
        "enabled": false,
        "upload_interval": 5
    }
}
CONFIG
sudo chown "$INSTALL_USER":"$INSTALL_USER" /etc/ada_pi/config.json

# Create Python virtual environment
echo "[5/11] Creating Python virtual environment…"
python3 -m venv /opt/ada-pi/venv

# Install Python backend dependencies
echo "[6/11] Installing backend dependencies in venv…"
/opt/ada-pi/venv/bin/pip install --upgrade pip
/opt/ada-pi/venv/bin/pip install -r /opt/ada-pi/backend/requirements.txt

# Prepare runtime data directories
echo "[7/11] Creating data directories…"
sudo mkdir -p /var/lib/ada-pi/{logs,storage,tacho}
sudo chown -R "$INSTALL_USER":"$INSTALL_USER" /var/lib/ada-pi

# Create systemd service for backend
echo "[8/11] Creating systemd service…"
sudo tee /etc/systemd/system/ada-pi.service > /dev/null <<SERVICE
[Unit]
Description=ADA-Pi Backend
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/ada-pi/backend
ExecStart=/opt/ada-pi/venv/bin/python3 /opt/ada-pi/backend/main.py
Restart=always
User=$INSTALL_USER
Environment=PYTHONUNBUFFERED=1
Environment=HOME=$INSTALL_HOME

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable ada-pi.service
sudo systemctl restart ada-pi.service

# Install and configure Tailscale
echo "[9/11] Installing Tailscale…"
curl -fsSL https://tailscale.com/install.sh | sh

TAILSCALE_ARGS=()
if [[ -n "${TS_AUTHKEY:-}" ]]; then
  echo "[10/11] Logging into Tailscale with provided auth key…"
  TAILSCALE_ARGS=(--authkey "$TS_AUTHKEY")
else
  echo "[10/11] Logging into Tailscale (interactive) – run with TS_AUTHKEY to automate"
fi

TAILSCALE_READY=false
if sudo tailscale up "${TAILSCALE_ARGS[@]}"; then
  TAILSCALE_READY=true
else
  echo "Tailscale login failed or was skipped; continuing without funnel setup."
fi

# Enable funnel for ports if logged in
if [ "$TAILSCALE_READY" = true ]; then
  echo "[11/11] Enabling Tailscale Funnel (8000 + 9000)…"
  sudo tailscale funnel 8000 --yes
  sudo tailscale funnel 9000 --yes
else
  echo "[11/11] Skipping Tailscale Funnel because login is not active."
fi

# Optional Kiosk mode
if [ "$MODE" == "2" ]; then
  echo "[Kiosk] Setting kiosk mode…"

  sudo tee /etc/systemd/system/kiosk.service > /dev/null <<KIOSK
[Unit]
Description=Chromium Kiosk
After=network.target

[Service]
User=$INSTALL_USER
Environment=XAUTHORITY=$INSTALL_HOME/.Xauthority
Environment=DISPLAY=:0
ExecStart=/usr/bin/chromium-browser --kiosk http://localhost:8000
Restart=always

[Install]
WantedBy=graphical.target
KIOSK

  sudo systemctl enable kiosk.service
  sudo systemctl start kiosk.service
fi

echo ""
echo "-----------------------------------------------------------"
echo " INSTALL COMPLETE!"
echo "-----------------------------------------------------------"
echo " Backend running on:       http://localhost:8000"
echo " WebSocket running on:     ws://localhost:9000"
echo ""
echo " Remote access via Tailscale Funnel:"
TS_IP=$(tailscale ip -4 2>/dev/null || true)
if [ -n "$TS_IP" ]; then
  echo " --> ${TS_IP}:8000"
  echo " --> ${TS_IP}:9000"
else
  echo " --> Tailscale not logged in yet"
fi
echo ""
echo " Your public Funnel URL:"
tailscale funnel status || true
echo "-----------------------------------------------------------"

