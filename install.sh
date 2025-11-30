#!/usr/bin/env bash
set -e

echo "-------------------------------------------"
echo " ADA-Pi Installer (Tailscale version)"
echo "-------------------------------------------"

# Ask headless or kiosk
echo "Choose mode:"
echo "1) Headless (no display)"
echo "2) Kiosk (autostart Chromium)"
read -p "Enter 1 or 2: " MODE

# Ensure system is updated
echo "[1/10] Updating system…"
sudo apt update -y
sudo apt upgrade -y

# Install system dependencies
echo "[2/10] Installing system dependencies…"
sudo apt install -y \
    python3 python3-pip python3-venv python3-full \
    git curl wget \
    libatlas-base-dev \
    libffi-dev build-essential \
    python3-serial python3-websocket python3-requests \
    xdotool unclutter chromium-browser

# Setup ADA-Pi folders
echo "[3/10] Preparing directories…"
sudo mkdir -p /opt/ada-pi
sudo chown $USER:$USER /opt/ada-pi
cp -r backend frontend /opt/ada-pi/

# Create Python virtual environment
echo "[4/10] Creating Python virtual environment…"
python3 -m venv /opt/ada-pi/venv

# Install Python backend dependencies
echo "[5/10] Installing backend dependencies in venv…"
/opt/ada-pi/venv/bin/pip install --upgrade pip
/opt/ada-pi/venv/bin/pip install flask flask-cors requests pyserial python-dotenv psutil websocket-client websockets

# Create systemd service for backend
echo "[6/10] Creating systemd service…"
sudo tee /etc/systemd/system/ada-pi.service > /dev/null <<EOF
[Unit]
Description=ADA-Pi Backend
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/ada-pi/backend
ExecStart=/opt/ada-pi/venv/bin/python3 /opt/ada-pi/backend/main.py
Restart=always
User=$USER

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ada-pi.service
sudo systemctl restart ada-pi.service

echo "[7/10] Installing Tailscale…"
curl -fsSL https://tailscale.com/install.sh | sh

echo "[8/10] Logging into Tailscale..."
sudo tailscale up

# Enable funnel for ports
echo "[9/10] Enabling Tailscale Funnel (8000 + 9000)…"
sudo tailscale funnel 8000 --yes
sudo tailscale funnel 9000 --yes

# Optional Kiosk mode
if [ "$MODE" == "2" ]; then
  echo "[10/10] Setting kiosk mode…"

  sudo tee /etc/systemd/system/kiosk.service > /dev/null <<EOF
[Unit]
Description=Chromium Kiosk
After=network.target

[Service]
User=$USER
Environment=XAUTHORITY=/home/$USER/.Xauthority
Environment=DISPLAY=:0
ExecStart=/usr/bin/chromium-browser --kiosk http://localhost:8000
Restart=always

[Install]
WantedBy=graphical.target
EOF

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
echo " --> $(tailscale ip -4):8000"
echo " --> $(tailscale ip -4):9000"
echo ""
echo " Your public Funnel URL:"
tailscale funnel status
echo "-----------------------------------------------------------"
