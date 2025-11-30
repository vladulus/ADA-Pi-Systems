#!/bin/bash

set -e

echo ""
echo "======================================="
echo "   ADA-Pi Full System Installer"
echo "======================================="
echo ""

# ---------------------------------------
# ASK FOR INSTALL MODE
# ---------------------------------------
echo "Select installation mode:"
echo "  1) Headless (Backend only)"
echo "  2) Kiosk (Backend + UI)"
read -p "Choose 1 or 2: " MODE

if [[ "$MODE" != "1" && "$MODE" != "2" ]]; then
    echo "Invalid selection."
    exit 1
fi

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
# INSTALL DEPENDENCIES
# ---------------------------------------
echo ""
echo "→ Installing system dependencies..."
sudo apt update
sudo apt install -y python3 python3-pip python3-venv

echo ""
echo "→ Installing Cloudflared..."

sudo mkdir -p --mode=0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null

echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflared.list

sudo apt update
sudo apt install -y cloudflared

echo ""
echo "→ Creating virtual environment..."
sudo mkdir -p /opt/ada-pi/backend
sudo cp -r "$PROJECT_ROOT/backend/"* /opt/ada-pi/backend/
cd /opt/ada-pi/backend

python3 -m venv venv
source venv/bin/activate

echo ""
echo "→ Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# ---------------------------------------
# CREATE BACKEND SYSTEMD SERVICE
# ---------------------------------------
echo ""
echo "→ Installing systemd backend service..."

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
# FRONTEND (Kiosk Mode Only)
# ---------------------------------------
if [[ "$MODE" == "2" ]]; then
    echo ""
    echo "→ Installing Kiosk frontend..."

    sudo mkdir -p /opt/ada-pi/frontend
    sudo cp -r "$PROJECT_ROOT/frontend/"* /opt/ada-pi/frontend/

    sudo apt install -y chromium-browser xserver-xorg x11-xserver-utils unclutter

    echo "→ Enabling autologin and kiosk..."

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
# CLOUDFLARE TUNNEL
# ---------------------------------------
echo ""
echo "======================================="
echo "      CLOUDFLARE TUNNEL SETUP"
echo "======================================="

read -p "Enter Pi hostname (example: pi01): " PIHOST

if [[ -z "$PIHOST" ]]; then
    echo "Hostname cannot be empty."
    exit 1
fi

echo ""
echo "→ Logging into Cloudflare..."
echo "Open the link shown and approve access."

sudo cloudflared tunnel login


echo ""
echo "→ Creating tunnel..."
sudo cloudflared tunnel create "$PIHOST"

TUNNEL_ID=$(sudo cat /root/.cloudflared/*.json | grep -o '"TunnelID":"[^"]*' | cut -d'"' -f4)

echo "Tunnel ID: $TUNNEL_ID"

echo ""
echo "→ Creating Cloudflare tunnel config..."

sudo mkdir -p /etc/cloudflared
sudo bash -c "cat > /etc/cloudflared/config.yml" <<EOF
tunnel: $TUNNEL_ID
credentials-file: /root/.cloudflared/$TUNNEL_ID.json

ingress:
  - hostname: $PIHOST.adasystems.uk
    service: http://localhost:8000
  - service: http_status:404
EOF


echo ""
echo "→ Installing systemd service for tunnel..."
sudo cloudflared service install

sudo systemctl enable cloudflared
sudo systemctl restart cloudflared

CF_DOMAIN=$(cloudflared tunnel list | grep "$PIHOST" | awk '{print $NF}')

echo ""
echo "================================================="
echo "CLOUDLFARE SETUP COMPLETE"
echo "Add this DNS record manually:"
echo ""
echo "Type:  CNAME"
echo "Name:  $PIHOST"
echo "Target: $CF_DOMAIN"
echo ""
echo "================================================="
echo ""

echo "Installation complete!"