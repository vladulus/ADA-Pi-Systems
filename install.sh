#!/usr/bin/env bash
set -euo pipefail

# ============================================
# ADA-Pi Systems Installer v2.0
# Supports: Pi 5, Pi Zero 2W, Pi 4
# UPS: X1202, WittyPi 4 L3V7
# ============================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;96m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo "=============================================="
echo -e "${CYAN}     ADA-Pi Systems Installer v2.0${NC}"
echo "     Professional Fleet Management"
echo "=============================================="
echo ""

# ============================================
# ROOT CHECK
# ============================================
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}ERROR: Please run as root (use sudo)${NC}"
    exit 1
fi

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
# HARDWARE DETECTION
# ============================================
echo -e "${BLUE}[AUTO] Detecting hardware...${NC}"
echo ""

# Detect Pi Model
PI_MODEL_RAW=$(cat /proc/device-tree/model 2>/dev/null | tr -d '\0' || echo "Unknown")
echo -e "  Detected: ${GREEN}$PI_MODEL_RAW${NC}"

# Categorize Pi
if echo "$PI_MODEL_RAW" | grep -qi "Pi 5"; then
    PI_TYPE="pi5"
    PI_NAME="Raspberry Pi 5"
elif echo "$PI_MODEL_RAW" | grep -qi "Zero 2"; then
    PI_TYPE="zero2w"
    PI_NAME="Raspberry Pi Zero 2 W"
elif echo "$PI_MODEL_RAW" | grep -qi "Pi 4"; then
    PI_TYPE="pi4"
    PI_NAME="Raspberry Pi 4"
elif echo "$PI_MODEL_RAW" | grep -qi "Zero"; then
    PI_TYPE="zero"
    PI_NAME="Raspberry Pi Zero"
else
    PI_TYPE="other"
    PI_NAME="$PI_MODEL_RAW"
fi

echo -e "  Category: ${GREEN}$PI_TYPE${NC}"
echo ""

# ============================================
# UPS DETECTION (requires i2c-tools)
# ============================================
echo -e "${BLUE}[AUTO] Detecting UPS...${NC}"

# Enable I2C first if possible
if command -v raspi-config >/dev/null 2>&1; then
    raspi-config nonint do_i2c 0 2>/dev/null || true
    sleep 1
fi

# Install i2c-tools if needed
if ! command -v i2cdetect >/dev/null 2>&1; then
    apt-get update -qq
    apt-get install -y -qq i2c-tools
fi

UPS_TYPE="none"
UPS_NAME="None detected"

# Scan I2C bus
if [ -e /dev/i2c-1 ]; then
    I2C_SCAN=$(i2cdetect -y 1 2>/dev/null || echo "")
    
    if echo "$I2C_SCAN" | grep -q " 36 "; then
        UPS_TYPE="x1202"
        UPS_NAME="Geekworm X1202"
    elif echo "$I2C_SCAN" | grep -q " 08 "; then
        UPS_TYPE="wittypi"
        UPS_NAME="WittyPi 4 L3V7"
    fi
fi

echo -e "  Detected: ${GREEN}$UPS_NAME${NC}"
echo ""

# ============================================
# FAN DETECTION
# ============================================
HAS_FAN="no"
if [ -e "/sys/devices/platform/cooling_fan/hwmon/hwmon0/pwm1" ]; then
    HAS_FAN="yes"
    echo -e "${BLUE}[AUTO] Hardware fan: ${GREEN}Detected${NC}"
else
    echo -e "${BLUE}[AUTO] Hardware fan: ${YELLOW}Not present${NC}"
fi
echo ""

# ============================================
# USER CONFIGURATION
# ============================================
echo -e "${CYAN}=== Configuration ===${NC}"
echo ""

# Display mode
MODE=""
while [[ "$MODE" != "1" && "$MODE" != "2" ]]; do
    echo "Display mode:"
    echo "  1) Headless (no display, server mode)"
    echo "  2) Kiosk (auto-start Chromium fullscreen)"
    read -r -p "Enter 1 or 2: " MODE
    if [[ "$MODE" != "1" && "$MODE" != "2" ]]; then
        echo -e "${YELLOW}Please enter 1 or 2${NC}"
    fi
done
echo ""

# Device name
DEFAULT_DEVICE_NAME="$(hostname)"
read -r -p "Device name [default: $DEFAULT_DEVICE_NAME]: " DEVICE_NAME
DEVICE_NAME=${DEVICE_NAME:-$DEFAULT_DEVICE_NAME}
echo ""

# JWT Secret
read -r -p "JWT Secret (from Laravel .env ADA_PI_JWT_SECRET): " JWT_SECRET
JWT_SECRET=${JWT_SECRET:-""}
echo ""

# ============================================
# MODEM / APN CONFIGURATION
# ============================================
echo -e "${CYAN}=== Modem Configuration ===${NC}"
echo "  (Required for 4G connectivity)"
echo ""

read -r -p "Mobile APN (e.g. three.co.uk, giffgaff.com): " MODEM_APN
MODEM_APN=${MODEM_APN:-""}

MODEM_USER=""
MODEM_PASS=""

if [ -n "$MODEM_APN" ]; then
    read -r -p "APN Username (leave empty if none): " MODEM_USER
    MODEM_USER=${MODEM_USER:-""}
    
    read -r -p "APN Password (leave empty if none): " MODEM_PASS
    MODEM_PASS=${MODEM_PASS:-""}
fi
echo ""

# ============================================
# OBD CONFIGURATION
# ============================================
echo -e "${CYAN}=== OBD Configuration ===${NC}"
OBD_TYPE=""
while [[ "$OBD_TYPE" != "1" && "$OBD_TYPE" != "2" && "$OBD_TYPE" != "3" ]]; do
    echo "OBD Connection type:"
    echo "  1) Bluetooth ELM327"
    echo "  2) USB ELM327"
    echo "  3) None / Skip"
    read -r -p "Enter 1, 2 or 3: " OBD_TYPE
done

OBD_BT_MAC=""
OBD_USB_PORT=""

if [ "$OBD_TYPE" == "1" ]; then
    read -r -p "ELM327 Bluetooth MAC (e.g. AA:BB:CC:DD:EE:FF): " OBD_BT_MAC
elif [ "$OBD_TYPE" == "2" ]; then
    read -r -p "ELM327 USB Port [default: /dev/ttyUSB0]: " OBD_USB_PORT
    OBD_USB_PORT=${OBD_USB_PORT:-"/dev/ttyUSB0"}
fi
echo ""

# ============================================
# CONFIRMATION
# ============================================
echo -e "${CYAN}=== Configuration Summary ===${NC}"
echo ""
echo -e "  Pi Model:      ${GREEN}$PI_NAME${NC}"
echo -e "  UPS:           ${GREEN}$UPS_NAME${NC}"
echo -e "  Fan:           ${GREEN}$HAS_FAN${NC}"
echo -e "  Display Mode:  ${GREEN}$([ "$MODE" == "1" ] && echo "Headless" || echo "Kiosk")${NC}"
echo -e "  Device name:   ${GREEN}$DEVICE_NAME${NC}"
echo -e "  JWT Secret:    ${GREEN}${JWT_SECRET:0:10}...${NC}"
echo -e "  APN:           ${GREEN}${MODEM_APN:-"(not set)"}${NC}"
if [ "$OBD_TYPE" == "1" ]; then
    echo -e "  OBD:           ${GREEN}Bluetooth ($OBD_BT_MAC)${NC}"
elif [ "$OBD_TYPE" == "2" ]; then
    echo -e "  OBD:           ${GREEN}USB ($OBD_USB_PORT)${NC}"
else
    echo -e "  OBD:           ${YELLOW}Disabled${NC}"
fi
echo ""
read -p "Press Enter to continue or Ctrl+C to abort..."
echo ""

# ============================================
# STEP 1: UPDATE SYSTEM
# ============================================
echo -e "${BLUE}[1/12] Updating system...${NC}"
apt-get update -y
apt-get upgrade -y
echo -e "${GREEN}✓ System updated${NC}"
echo ""

# ============================================
# STEP 2: INSTALL DEPENDENCIES
# ============================================
echo -e "${BLUE}[2/12] Installing system dependencies...${NC}"

apt-get install -y \
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

# Kiosk mode dependencies
if [ "$MODE" == "2" ]; then
    echo -e "${BLUE}Installing kiosk dependencies...${NC}"
    apt-get install -y \
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
echo -e "${BLUE}[3/12] Enabling hardware interfaces...${NC}"

if command -v raspi-config >/dev/null 2>&1; then
    raspi-config nonint do_i2c 0 || true
    raspi-config nonint do_serial_hw 0 || true
    echo -e "${GREEN}✓ I2C and Serial enabled${NC}"
else
    echo -e "${YELLOW}⚠ raspi-config not found${NC}"
fi

# Disable ModemManager (conflicts with AT commands)
systemctl stop ModemManager 2>/dev/null || true
systemctl disable ModemManager 2>/dev/null || true
echo -e "${GREEN}✓ ModemManager disabled${NC}"

# Add user to groups
usermod -aG dialout,i2c,bluetooth,gpio "$INSTALL_USER" 2>/dev/null || true
echo -e "${GREEN}✓ User added to hardware groups${NC}"
echo ""

# ============================================
# STEP 4: INSTALL WITTYPI SOFTWARE (if detected)
# ============================================
if [ "$UPS_TYPE" == "wittypi" ]; then
    echo -e "${BLUE}[4/12] Installing WittyPi software...${NC}"
    
    # Save current directory
    INSTALL_DIR=$(pwd)
    
    cd /tmp
    wget -q https://www.uugear.com/repo/WittyPi4/install.sh -O wittypi_install.sh
    chmod +x wittypi_install.sh
    bash wittypi_install.sh
    
    # Return to install directory
    cd "$INSTALL_DIR"
    
    rm -f /tmp/wittypi_install.sh
    echo -e "${GREEN}✓ WittyPi software installed${NC}"
else
    echo -e "${BLUE}[4/12] Skipping WittyPi (not detected)${NC}"
fi
echo ""

# ============================================
# STEP 5: CREATE DIRECTORIES
# ============================================
echo -e "${BLUE}[5/12] Creating directories...${NC}"

# Main installation directory
mkdir -p /opt/ada-pi
chown "$INSTALL_USER":"$INSTALL_USER" /opt/ada-pi

# Check source files
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo -e "${RED}ERROR: backend/ and frontend/ directories not found!${NC}"
    echo "Make sure you're running this from the ADA-Pi-Systems directory"
    exit 1
fi

# Copy application files
cp -r backend /opt/ada-pi/
cp -r frontend /opt/ada-pi/
chown -R "$INSTALL_USER":"$INSTALL_USER" /opt/ada-pi

# Runtime directories
mkdir -p /opt/ada-pi/data/{logs,tacho,ota,tmp}
chown -R "$INSTALL_USER":"$INSTALL_USER" /opt/ada-pi/data

# Settings version directory (for settings_handler.py)
mkdir -p /var/lib/ada_pi
chown "$INSTALL_USER":"$INSTALL_USER" /var/lib/ada_pi

echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# ============================================
# STEP 6: CREATE CONFIGURATION
# ============================================
echo -e "${BLUE}[6/12] Creating configuration...${NC}"

mkdir -p /etc/ada_pi
chown "$INSTALL_USER":"$INSTALL_USER" /etc/ada_pi

LOCAL_IP=$(hostname -I | awk '{print $1}')

# Build OBD config section
OBD_ENABLED="false"
if [ "$OBD_TYPE" == "1" ]; then
    OBD_ENABLED="true"
    OBD_CONNECTION="bluetooth"
    OBD_BT_MAC_CFG="$OBD_BT_MAC"
    OBD_USB_PORT_CFG=""
elif [ "$OBD_TYPE" == "2" ]; then
    OBD_ENABLED="true"
    OBD_CONNECTION="usb"
    OBD_BT_MAC_CFG=""
    OBD_USB_PORT_CFG="$OBD_USB_PORT"
else
    OBD_CONNECTION="none"
    OBD_BT_MAC_CFG=""
    OBD_USB_PORT_CFG=""
fi

# Determine I2C address based on UPS type
if [ "$UPS_TYPE" == "x1202" ]; then
    UPS_I2C="0x36"
elif [ "$UPS_TYPE" == "wittypi" ]; then
    UPS_I2C="0x08"
else
    UPS_I2C=""
fi

# Create config.json
cat > /etc/ada_pi/config.json <<CONFIG
{
    "device_id": "$DEVICE_NAME",
    "jwt_secret": "$JWT_SECRET",
    "pi_type": "$PI_TYPE",
    "api_url": "http://${LOCAL_IP}:8000",
    "ws_url": "ws://${LOCAL_IP}:9000",
    "cloud": {
        "upload_url": "https://www.adasystems.uk/api/ada-pi/device/status",
        "logs_url": "https://www.adasystems.uk/api/ada-pi/logs/upload"
    },
    "ups": {
        "type": "$UPS_TYPE",
        "shutdown_pct": 10,
        "i2c_address": "$UPS_I2C"
    },
    "fan": {
        "enabled": $([ "$HAS_FAN" == "yes" ] && echo "true" || echo "false"),
        "mode": "auto",
        "threshold": 50
    },
    "modem": {
        "port": "/dev/ttyUSB2",
        "baudrate": 115200,
        "apn": "$MODEM_APN",
        "apn_username": "$MODEM_USER",
        "apn_password": "$MODEM_PASS",
        "failover_enabled": true,
        "network_mode": "auto",
        "roaming": false
    },
    "gps": {
        "source": "modem",
        "unit_mode": "auto",
        "enabled": true,
        "update_rate": 1
    },
    "obd": {
        "enabled": $OBD_ENABLED,
        "connection": "$OBD_CONNECTION",
        "bluetooth_mac": "$OBD_BT_MAC_CFG",
        "usb_port": "$OBD_USB_PORT_CFG",
        "protocol": "auto",
        "poll_interval": 2
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
echo ""

# ============================================
# STEP 7: CREATE PYTHON VENV
# ============================================
echo -e "${BLUE}[7/12] Creating Python environment...${NC}"

cd /opt/ada-pi
sudo -u "$INSTALL_USER" python3 -m venv --system-site-packages venv

echo -e "${GREEN}✓ Virtual environment created${NC}"
echo ""

# ============================================
# STEP 8: INSTALL PYTHON DEPENDENCIES
# ============================================
echo -e "${BLUE}[8/12] Installing Python dependencies...${NC}"

sudo -u "$INSTALL_USER" /opt/ada-pi/venv/bin/pip install --upgrade pip

if [ -f "/opt/ada-pi/backend/requirements.txt" ]; then
    sudo -u "$INSTALL_USER" /opt/ada-pi/venv/bin/pip install -r /opt/ada-pi/backend/requirements.txt
else
    echo -e "${RED}ERROR: requirements.txt not found!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python dependencies installed${NC}"
echo ""

# ============================================
# STEP 9: CREATE SYSTEMD SERVICE
# ============================================
echo -e "${BLUE}[9/12] Creating systemd service...${NC}"

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
ExecStart=/opt/ada-pi/venv/bin/python3 /opt/ada-pi/backend/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable ada-pi.service

echo -e "${GREEN}✓ Systemd service created${NC}"
echo ""

# ============================================
# STEP 10: CONFIGURE KIOSK MODE
# ============================================
if [ "$MODE" == "2" ]; then
    echo -e "${BLUE}[10/12] Configuring kiosk mode...${NC}"
    
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
    echo -e "${BLUE}[10/12] Skipping kiosk mode (headless selected)${NC}"
fi
echo ""

# ============================================
# STEP 11: START SERVICE
# ============================================
echo -e "${BLUE}[11/12] Starting ADA-Pi service...${NC}"

systemctl start ada-pi.service || true
sleep 3

STATUS=$(systemctl is-active ada-pi.service || true)
if [ "$STATUS" == "active" ]; then
    echo -e "${GREEN}✓ ada-pi.service is running${NC}"
else
    echo -e "${YELLOW}⚠ Service not running yet. Check: sudo journalctl -u ada-pi -e${NC}"
fi
echo ""

# ============================================
# STEP 12: VERIFY
# ============================================
echo -e "${BLUE}[12/12] Verifying installation...${NC}"

sleep 2
PORT_8000=$(ss -tuln 2>/dev/null | grep ":8000 " || echo "")
PORT_9000=$(ss -tuln 2>/dev/null | grep ":9000 " || echo "")

if [ -n "$PORT_8000" ]; then
    echo -e "${GREEN}✓ REST API on port 8000${NC}"
else
    echo -e "${YELLOW}⚠ REST API not detected yet${NC}"
fi

if [ -n "$PORT_9000" ]; then
    echo -e "${GREEN}✓ WebSocket on port 9000${NC}"
else
    echo -e "${YELLOW}⚠ WebSocket not detected yet${NC}"
fi
echo ""

# ============================================
# DONE
# ============================================
echo ""
echo "=============================================="
echo -e "${GREEN}  INSTALLATION COMPLETE!${NC}"
echo "=============================================="
echo ""
echo -e "${GREEN}Hardware Detected:${NC}"
echo "  Pi Model:  $PI_NAME"
echo "  UPS:       $UPS_NAME"
echo "  Fan:       $HAS_FAN"
echo ""
echo -e "${GREEN}Access:${NC}"
echo "  Local:     http://${LOCAL_IP}:8000"
echo "  Hostname:  http://$(hostname).local:8000"
echo ""
echo -e "${GREEN}Service Commands:${NC}"
echo "  Status:    sudo systemctl status ada-pi"
echo "  Restart:   sudo systemctl restart ada-pi"
echo "  Logs:      sudo journalctl -u ada-pi -f"
echo ""
echo -e "${GREEN}Configuration:${NC}"
echo "  Config:    /etc/ada_pi/config.json"
echo "  Data:      /opt/ada-pi/data/"
echo ""

if [ "$UPS_TYPE" == "wittypi" ]; then
    echo -e "${CYAN}WittyPi Commands:${NC}"
    echo "  Status:    cd ~/wittypi && ./wittyPi.sh"
    echo "  Web UI:    http://${LOCAL_IP}:8000/wittypi4/"
    echo ""
fi

echo "=============================================="
echo -e "${GREEN}Installation successful! 🎉${NC}"
echo "=============================================="
echo ""

# Reboot prompt
read -p "Reboot now to apply all changes? (recommended) (y/n): " REBOOT
if [ "$REBOOT" == "y" ] || [ "$REBOOT" == "Y" ]; then
    echo "Rebooting in 5 seconds..."
    sleep 5
    reboot
fi