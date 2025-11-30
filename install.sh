#!/bin/bash

set -e

# =======================================
# ADA-Pi Full System Installer (Enhanced)
# With optional Cloudflare / Tailscale / Both / None
# =======================================

echo ""
echo "======================================="
echo "   ADA-Pi Full System Installer"
echo "======================================="
echo ""

# ---------------------------------------
# INSTALL MODE
# ---------------------------------------
echo "Select installation mode:"
echo "  1) Headless (Backend only)"
echo "  2) Kiosk (Backend + UI)"
read -p "Choose 1 or 2: " MODE

if [[ "$MODE" != "1" && "$MODE" != "2" ]]; then
    echo "Invalid selection."
    exit 1
fi

echo ""
echo "Cloud Access Options:"
echo "  1) Cloudflare Tunnel"
echo "  2) Tailscale VPN"
echo "  3) Both Cloudflare + Tailscale"
echo "  4) None (no remote access setup)"
read -p "Choose 1–4: " NETOPT

if ! [[ "$NETOPT" =~ ^[1-4]$ ]]; then
    echo "Invalid selection."
    exit 1
fi

echo "Selected network option: $NETOPT"

# ---------------------------------------
# DETECT PROJECT ROOT
# ---------------------------------------
if [[ -d "./backend" && -d "./installer" ]]; then
    PROJECT_ROOT=$(pwd)
else
    echo "ERROR: Run this installer from ADA-Pi-Systems folder."
    exit 1
fi

echo "Project root detected: $PROJECT_ROOT"

# ---------------------------------------
# SYSTEM DEPENDENCIES
# ---------------------------------------
echo ""
echo "→ Installing core system dependencies..."
sudo apt update
sudo apt install -y python3 python3-pip python3-venv curl

# ---------------------------------------
# OPTIONAL: CLOUDLFARED INSTALL
# ---------------------------------------
if [[ "$NETOPT" == "1" || "$NETOPT" == "3" ]]; then
    echo ""
    echo "→ Installing Cloudflared..."

    sudo mkdir -p --mode=0755 /usr/share/keyrings
    curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null

    echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflared.list

    sudo apt update
    sudo apt install -y cloudflared
else
    echo "Skipping Cloudflare installation"
fi

# ---------------------------------------
# OPTIONAL: TAILSCALE INSTALL
# ---------------------------------------
if [[ "$NETOPT" == "2" || "$NETOPT" == "3" ]]; then
    echo ""
    echo "→ Installing Tailscale..."
    curl -fsSL https://tailscale.com/install.sh | sh
else
    echo "Skipping Tailscale installation"
fi

# ---------------------------------------
# BACKEND SETUP
# ---------------------------------------
echo ""
echo "→ Creating virtual environment..."
sudo mkdir -p /opt/ada-pi/backend
sudo cp -r "$PROJECT_ROOT/backend/"* /opt/ada-pi/backend/
cd /opt/ada-pi/backend

python3 -m venv venv
source venv/bin/activate

echo "→ Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# ---------------------------------------
# BACKEND SYSTEMD SERVICE
# ---------------------------------------
echo ""
echo "→ Installing backend service..."

SERVICE_FILE="/etc/systemd/system/ada-pi-backend.service"

sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=Ada-Pi Backend
After=network.target

[Service]
WorkingDirectory=/opt/ada-pi/backend
ExecStart=/opt/ada-pi/backend/venv/bin/python /opt/ada-pi/backend/main.py
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ada-pi-backend
sudo systemctl restart ada-pi-backend

echo "✓ Backend service installed"

# ---------------------------------------
# FRONTEND SETUP
# ---------------------------------------
if [[ "$MODE" == "2" ]]; then
    echo ""
    echo "→ Installing Kiosk frontend..."

    sudo mkdir -p /opt/ada-pi/frontend
    sudo cp -r "$PROJECT_ROOT/frontend/"* /opt/ada-pi/frontend/

    sudo apt install -y chromium-browser xserver-xorg x11-xserver-utils unclutter

    echo "→ Enabling autologin + kiosk mode..."

    sudo mkdir -p /etc/systemd/system/getty@tty1.service.d
    sudo bash -c "cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf" <<EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin pi --noclear %I $TERM
EOF

    sudo bash -c "cat > /home/pi/.bash_profile" <<EOF
chromium-browser --noerrdialogs --disable-infobars --kiosk http://localhost:8000
EOF
fi

# ---------------------------------------
# CLOUDLFARE TUNNEL CONFIG (OPTIONAL)
# ---------------------------------------
if [[ "$NETOPT" == "1" || "$NETOPT" == "3" ]]; then
    echo ""
    echo "======================================="
    echo "     CLOUDLFARE TUNNEL SETUP"
    echo "======================================="

    read -p "Enter Pi hostname (example: pi01): " PIHOST

    if [[ -z "$PIHOST" ]]; then
        echo "Hostname cannot be empty."
        exit 1
    fi

    echo "→ Logging into Cloudflare..."
    sudo cloudflared tunnel login

    echo "→ Creating tunnel..."
    sudo cloudflared tunnel create "$PIHOST"

    TUNNEL_ID=$(sudo cat /root/.cloudflared/*.json | grep -o '"TunnelID":"[^"]*' | cut -d'"' -f4)

    echo "Tunnel ID: $TUNNEL_ID"

    echo "→ Creating Cloudflare config..."
    sudo mkdir -p /etc/cloudflared
    sudo bash -c "cat > /etc/cloudflared/config.yml" <<EOF
tunnel: $TUNNEL_ID
credentials-file: /root/.cloudflared/$TUNNEL_ID.json

ingress:
  - hostname: $PIHOST.adasystems.uk
    service: http://localhost:8000
  - service: http_status:404
EOF

    echo "→ Enabling Cloudflare service..."
    sudo cloudflared service install
    sudo systemctl enable cloudflared
    sudo systemctl restart cloudflared
fi

# ---------------------------------------
# TAILSCALE AUTH NOTICE
# ---------------------------------------
if [[ "$NETOPT" == "2" || "$NETOPT" == "3" ]]; then
    echo ""
    echo "→ IMPORTANT: Tailscale installed"
    echo "Run this on your Pi to authenticate:"
    echo ""
    echo "    sudo tailscale up"
    echo ""
fi

# ---------------------------------------
# FINISHED
# ---------------------------------------
echo ""
echo "======================================="
echo " INSTALLATION COMPLETE "
echo "======================================="
