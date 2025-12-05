#!/usr/bin/env bash
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "=============================================="
echo "     ADA-Pi Systems Installer v1.0"
echo "     Professional Fleet Management"
echo "=============================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}ERROR: Please run as root (use sudo)${NC}"
    exit 1
fi

# Get actual user (not root)
INSTALL_USER="${SUDO_USER:-$USER}"
INSTALL_HOME="$(getent passwd "$INSTALL_USER" | cut -d: -f6)"

if [ "$INSTALL_USER" == "root" ]; then
    echo -e "${RED}ERROR: Don't run this as root user directly. Use 'sudo' with your normal user.${NC}"
    exit 1
fi

echo -e "${BLUE}Installing for user: $INSTALL_USER${NC}"
echo -e "${BLUE}Home directory: $INSTALL_HOME${NC}"
echo ""

# ============================================
# USER CONFIGURATION
# ============================================

# Ask display mode
MODE=""
while [[ "$MODE" != "1" && "$MODE" != "2" ]]; do
    echo "Choose display mode:"
    echo "  1) Headless (no display, server mode)"
    echo "  2) Kiosk (auto-start Chromium fullscreen)"
    read -r -p "Enter 1 or 2: " MODE
    if [[ "$MODE" != "1" && "$MODE" != "2" ]]; then
        echo -e "${YELLOW}Please enter 1 or 2${NC}"
    fi
done
echo ""

# Ask ADA Systems API base URL
read -r -p "ADA Systems API base URL (ex: https://ada.impulsive.ro) [default: http://127.0.0.1:8000]: " ADA_API_BASE_URL
ADA_API_BASE_URL=${ADA_API_BASE_URL:-http://127.0.0.1:8000}
echo ""

# Ask device name (Pi name in dashboard)
DEFAULT_DEVICE_NAME="$(hostname)"
read -r -p "Device name (Pi name in ADA dashboard) [default: $DEFAULT_DEVICE_NAME]: " DEVICE_NAME
DEVICE_NAME=${DEVICE_NAME:-$DEFAULT_DEVICE_NAME}
echo ""

echo -e "${GREEN}Configuration:${NC}"
echo "  Display Mode: $([ "$MODE" == "1" ] && echo "Headless" || echo "Kiosk")"
echo "  ADA API URL:  $ADA_API_BASE_URL"
echo "  Device name:  $DEVICE_NAME"
echo ""
read -p "Press Enter to continue or Ctrl+C to abort..."
echo ""

# ============================================
# STEP 1: UPDATE SYSTEM
# ============================================
echo -e "${BLUE}[1/11] Updating system...${NC}"
apt update -y
apt upgrade -y
echo -e "${GREEN}✓ System updated${NC}"
echo ""

# ============================================
# STEP 2: INSTALL DEPENDENCIES
# ============================================
echo -e "${BLUE}[2/11] Installing system dependencies...${NC}"

apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-full \
    git \
    curl \
    wget \
    build-essential \
    python3-serial \
    python3-websocket \
    python3-requests \
    modemmanager \
    usb-modeswitch \
    i2c-tools \
    python3-smbus \
    python3-dbus \
    python3-gi \
    bluez \
    bluetooth \
    pkg-config \
    libgirepository1.0-dev \
    network-manager \
    net-tools \
    iproute2

# Install display dependencies if kiosk mode
if [ "$MODE" == "2" ]; then
    echo -e "${BLUE}Installing display dependencies for kiosk mode...${NC}"
    apt install -y \
        xdotool \
        unclutter \
        chromium \
        xserver-xorg \
        xinit
fi

echo -e "${GREEN}✓ System dependencies installed${NC}"
echo ""

# ============================================
# STEP 3: ENABLE HARDWARE INTERFACES
# ============================================
echo -e "${BLUE}[3/11] Enabling hardware interfaces...${NC}"

# Enable I2C & Serial on Raspberry Pi (if raspi-config exists)
if command -v raspi-config >/dev/null 2>&1; then
    raspi-config nonint do_i2c 0 || true
    raspi-config nonint do_serial_hw 0 || true
    echo -e "${GREEN}✓ I2C and Serial enabled via raspi-config${NC}"
else
    echo -e "${YELLOW}⚠ raspi-config not found (not a Raspberry Pi?)${NC}"
fi

# Add user to required groups
usermod -aG dialout,i2c,bluetooth,gpio "$INSTALL_USER" 2>/dev/null || true
echo -e "${GREEN}✓ User added to hardware groups${NC}"
echo ""

# ============================================
# STEP 4: CREATE DIRECTORIES
# ============================================
echo -e "${BLUE}[4/11] Creating installation directories...${NC}"

# Main installation directory
mkdir -p /opt/ada-pi
chown "$INSTALL_USER":"$INSTALL_USER" /opt/ada-pi

# Copy application files
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo -e "${RED}ERROR: backend/ and frontend/ directories not found!${NC}"
    echo "Make sure you're running this from the ADA-Pi-Systems directory"
    exit 1
fi

cp -r backend /opt/ada-pi/
cp -r frontend /opt/ada-pi/
chown -R "$INSTALL_USER":"$INSTALL_USER" /opt/ada-pi

# Runtime data directories (used by StorageManager)
mkdir -p /opt/ada-pi/data/{logs,tacho,ota,tmp}
chown -R "$INSTALL_USER":"$INSTALL_USER" /opt/ada-pi/data

echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# ============================================
# STEP 5: CREATE DEFAULT CONFIGURATION
# ============================================
echo -e "${BLUE}[5/11] Creating default configuration...${NC}"

# Create config directory
mkdir -p /etc/ada_pi
chown "$INSTALL_USER":"$INSTALL_USER" /etc/ada_pi

# Get local IP
LOCAL_IP=$(hostname -I | awk '{print $1}')

# Create config.json
cat > /etc/ada_pi/config.json <<CONFIG
{
    "device_id": "$DEVICE_NAME",
    "api_url": "http://${LOCAL_IP}:8000",
    "ws_url": "ws://${LOCAL_IP}:9000",
    "auth": {
        "username": "admin",
        "password": "changeme"
    },
    "cloud": {
        "upload_url": "https://www.adasystems.uk/api/telemetry/upload",
        "logs_url": "https://www.adasystems.uk/api/logs/upload"
    },
    "gps": {
        "unit_mode": "auto",
        "port": "/dev/ttyUSB0",
        "baudrate": 9600
    },
    "ups": {
        "shutdown_pct": 10,
        "i2c_address": "0x36"
    },
    "modem": {
        "port": "/dev/ttyUSB2",
        "baudrate": 115200
    },
    "obd": {
        "enabled": true,
        "bluetooth_mac": ""
    },
    "tacho": {
        "enabled": false,
        "upload_interval": 300
    },
    "network": {
        "wifi_country": "GB"
    }
}
CONFIG

chown "$INSTALL_USER":"$INSTALL_USER" /etc/ada_pi/config.json
chmod 600 /etc/ada_pi/config.json

echo -e "${GREEN}✓ Configuration created${NC}"
echo -e "${YELLOW}⚠ Default password is 'changeme' - change it after installation!${NC}"
echo ""

# ============================================
# STEP 6: CREATE PYTHON VIRTUAL ENVIRONMENT
# ============================================
echo -e "${BLUE}[6/11] Creating Python virtual environment...${NC}"

cd /opt/ada-pi
sudo -u "$INSTALL_USER" python3 -m venv --system-site-packages venv

echo -e "${GREEN}✓ Virtual environment created at /opt/ada-pi/venv${NC}"
echo ""

# ============================================
# STEP 7: INSTALL PYTHON DEPENDENCIES
# ============================================
echo -e "${BLUE}[7/11] Installing Python dependencies...${NC}"

# Upgrade pip first
sudo -u "$INSTALL_USER" /opt/ada-pi/venv/bin/pip install --upgrade pip

# Install requirements
if [ -f "/opt/ada-pi/backend/requirements.txt" ]; then
    sudo -u "$INSTALL_USER" /opt/ada-pi/venv/bin/pip install -r /opt/ada-pi/backend/requirements.txt
else
    echo -e "${RED}ERROR: requirements.txt not found!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python dependencies installed${NC}"
echo ""

# ============================================
# STEP 8: CREATE SYSTEMD SERVICE
# ============================================
echo -e "${BLUE}[8/11] Creating systemd service...${NC}"

cat > /etc/systemd/system/ada-pi.service <<SERVICE
[Unit]
Description=ADA-Pi Backend Service
Documentation=https://www.adasystems.uk
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$INSTALL_USER
Group=$INSTALL_USER
WorkingDirectory=/opt/ada-pi/backend
Environment=PYTHONUNBUFFERED=1
Environment=HOME=$INSTALL_HOME
Environment=ADA_API_BASE_URL=$ADA_API_BASE_URL
ExecStart=/opt/ada-pi/venv/bin/python3 /opt/ada-pi/backend/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable ada-pi.service

echo -e "${GREEN}✓ Systemd service created and enabled${NC}"
echo ""

# ============================================
# STEP 9: CONFIGURE KIOSK MODE (if selected)
# ============================================
if [ "$MODE" == "2" ]; then
    echo -e "${BLUE}[9/11] Configuring kiosk mode...${NC}"
    
    cat > /etc/systemd/system/ada-pi-kiosk.service <<KIOSK
[Unit]
Description=ADA-Pi Kiosk Display
After=ada-pi.service graphical.target
Requires=ada-pi.service

[Service]
Type=simple
User=$INSTALL_USER
Environment=DISPLAY=:0
Environment=XAUTHORITY=$INSTALL_HOME/.Xauthority
ExecStartPre=/bin/sleep 10
ExecStart=/usr/bin/chromium --kiosk --noerrdialogs --disable-infobars --no-first-run --check-for-update-interval=31536000 http://localhost:8000
Restart=always
RestartSec=5

[Install]
WantedBy=graphical.target
KIOSK
    
    systemctl enable ada-pi-kiosk.service
    echo -e "${GREEN}✓ Kiosk mode configured${NC}"
else
    echo -e "${BLUE}[9/11] Skipping kiosk mode (headless selected)${NC}"
fi
echo ""

# ============================================
# STEP 10: START SERVICE
# ============================================
echo -e "${BLUE}[10/11] Starting ADA-Pi service...${NC}"

systemctl start ada-pi.service || true
sleep 3

STATUS=$(systemctl is-active ada-pi.service || true)
if [ "$STATUS" == "active" ]; then
    echo -e "${GREEN}✓ ada-pi.service is running${NC}"
else
    echo -e "${RED}⚠ ada-pi.service is not running. Check logs with:${NC}"
    echo "  sudo journalctl -u ada-pi -e"
    echo ""
fi

echo ""
echo -e "${BLUE}Quick service commands:${NC}"
echo "  sudo systemctl status ada-pi"
echo "  sudo systemctl restart ada-pi"
echo "  sudo journalctl -u ada-pi -f"
echo ""

# ============================================
# STEP 11: VERIFY INSTALLATION
# ============================================
echo -e "${BLUE}[11/11] Verifying installation...${NC}"

# Check if ports are listening
sleep 2
PORT_8000=$(netstat -tuln 2>/dev/null | grep ":8000 " || ss -tuln 2>/dev/null | grep ":8000 " || echo "")
PORT_9000=$(netstat -tuln 2>/dev/null | grep ":9000 " || ss -tuln 2>/dev/null | grep ":9000 " || echo "")

if [ -n "$PORT_8000" ]; then
    echo -e "${GREEN}✓ REST API listening on port 8000${NC}"
else
    echo -e "${YELLOW}⚠ REST API not detected on port 8000${NC}"
fi

if [ -n "$PORT_9000" ]; then
    echo -e "${GREEN}✓ WebSocket listening on port 9000${NC}"
else
    echo -e "${YELLOW}⚠ WebSocket not detected on port 9000${NC}"
fi

# Simple API health check (does not check auth)
if curl -s http://localhost:8000/api/system/info >/dev/null 2>&1; then
    echo -e "${GREEN}✓ API responding to requests${NC}"
else
    echo -e "${YELLOW}⚠ API not responding yet (may take a few seconds)${NC}"
fi

echo ""

# ============================================
# INSTALLATION COMPLETE
# ============================================
echo ""
echo "=============================================="
echo -e "${GREEN}  INSTALLATION COMPLETE!${NC}"
echo "=============================================="
echo ""
echo -e "${GREEN}Dashboard Access:${NC}"
echo "  Local:    http://${LOCAL_IP}:8000"
echo "  Hostname: http://$(hostname).local:8000"
echo ""
echo -e "${GREEN}Service Management:${NC}"
echo "  Status:   sudo systemctl status ada-pi"
echo "  Stop:     sudo systemctl stop ada-pi"
echo "  Start:    sudo systemctl start ada-pi"
echo "  Restart:  sudo systemctl restart ada-pi"
echo "  Logs:     sudo journalctl -u ada-pi -f"
echo ""
echo -e "${GREEN}Configuration:${NC}"
echo "  Device ID: $DEVICE_NAME"
echo "  Config:    /etc/ada_pi/config.json"
echo "  Data:      /opt/ada-pi/data/"
echo ""
echo -e "${YELLOW}IMPORTANT:${NC}"
echo "  1. Default password is 'changeme' - CHANGE IT NOW!"
echo "  2. Login via: http://${LOCAL_IP}:8000"
echo "  3. Use your www.adasystems.uk credentials to login"
echo ""
echo "=============================================="
echo -e "${GREEN}Installation successful! 🎉${NC}"
echo "=============================================="
echo ""

# Offer to reboot
read -p "Reboot now to apply all changes? (recommended) (y/n): " REBOOT
if [ "$REBOOT" == "y" ] || [ "$REBOOT" == "Y" ]; then
    echo "Rebooting in 5 seconds... (Ctrl+C to cancel)"
    sleep 5
    reboot
fi
