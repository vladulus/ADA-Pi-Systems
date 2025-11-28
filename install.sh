#!/bin/bash
# ADA-Pi Complete Automated Installer
# Installs everything: system, backend, frontend, Tailscale, optional kiosk mode

set -e

echo "╔════════════════════════════════════════════════╗"
echo "║  ADA-Pi Complete Automated Installer          ║"
echo "║  This will install EVERYTHING                  ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run as root: sudo bash install.sh"
    exit 1
fi

# Get actual user (not root)
ACTUAL_USER=${SUDO_USER:-$USER}

echo "📋 Step 1/11: Checking system..."

# Check if on Raspberry Pi
if [ -f /proc/device-tree/model ]; then
    PI_MODEL=$(cat /proc/device-tree/model)
    echo "✓ Detected: $PI_MODEL"
else
    echo "⚠️  Warning: Not running on Raspberry Pi"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "❓ Display Mode Selection"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "How will you access the dashboard?"
echo ""
echo "1) Headless - Access via web browser (phone/laptop)"
echo "   └─ Recommended for vehicle installations"
echo "   └─ No display needed on Pi"
echo "   └─ Access from anywhere via Tailscale"
echo ""
echo "2) Kiosk Mode - Auto-start on connected display"
echo "   └─ Fullscreen dashboard on Pi display"
echo "   └─ Also accessible remotely"
echo "   └─ Requires monitor/touchscreen"
echo ""
read -p "Enter choice (1 or 2): " DISPLAY_CHOICE

INSTALL_KIOSK=false
if [ "$DISPLAY_CHOICE" = "2" ]; then
    INSTALL_KIOSK=true
    echo "✓ Will install kiosk mode"
else
    echo "✓ Headless mode selected"
fi

echo ""
echo "📦 Step 2/11: Updating system packages..."
apt-get update -qq > /dev/null 2>&1
echo "✓ System updated"
echo ""

echo "📦 Step 3/11: Installing system dependencies..."
echo "   (This may take a few minutes...)"
if [ "$INSTALL_KIOSK" = true ]; then
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        i2c-tools \
        python3-smbus \
        git \
        curl \
        wget \
        jq \
        gpsd \
        gpsd-clients \
        libgps-dev \
        modemmanager \
        network-manager \
        bluez \
        bluez-tools \
        chromium-browser \
        xserver-xorg \
        x11-xserver-utils \
        xinit \
        unclutter \
        > /dev/null 2>&1
    echo "✓ Dependencies installed (with display support)"
else
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        i2c-tools \
        python3-smbus \
        git \
        curl \
        wget \
        jq \
        gpsd \
        gpsd-clients \
        libgps-dev \
        modemmanager \
        network-manager \
        bluez \
        bluez-tools \
        > /dev/null 2>&1
    echo "✓ Dependencies installed"
fi
echo ""

echo "📂 Step 4/11: Creating installation directory..."
mkdir -p /opt/ada-pi
cp -r backend frontend /opt/ada-pi/
chown -R root:root /opt/ada-pi
echo "✓ Files copied to /opt/ada-pi"
echo ""

echo "🐍 Step 5/11: Installing Python packages..."
echo "   (This may take a minute...)"
cd /opt/ada-pi/backend
pip3 install -r requirements.txt --break-system-packages -q > /dev/null 2>&1
echo "✓ Python packages installed"
echo ""

echo "📁 Step 6/11: Creating data directories..."
mkdir -p /var/lib/ada-pi/{logs,storage,tacho}
chown -R root:root /var/lib/ada-pi

# Create default config
if [ ! -f /opt/ada-pi/backend/config.json ]; then
    cat > /opt/ada-pi/backend/config.json << 'CONFIG_EOF'
{
  "device_id": "ada-pi-001",
  "api": {
    "host": "0.0.0.0",
    "port": 8000
  },
  "websocket": {
    "host": "0.0.0.0",
    "port": 9000
  },
  "auth": {
    "username": "admin",
    "password": "admin"
  },
  "gps": {
    "unit_mode": "auto",
    "port": "/dev/ttyUSB1"
  },
  "ups": {
    "enabled": true,
    "i2c_address": "0x36"
  },
  "modem": {
    "enabled": true,
    "apn": "internet"
  },
  "cloud": {
    "enabled": false,
    "url": ""
  }
}
CONFIG_EOF
    echo "✓ Created default config.json"
fi
echo "✓ Data directories created"
echo ""

echo "⚙️  Step 7/11: Creating systemd service..."
cat > /etc/systemd/system/ada-pi-backend.service << 'SERVICE_EOF'
[Unit]
Description=ADA-Pi Backend Engine
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/ada-pi/backend
ExecStart=/usr/bin/python3 /opt/ada-pi/backend/main.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
SERVICE_EOF

systemctl daemon-reload
systemctl enable ada-pi-backend > /dev/null 2>&1
echo "✓ Service created and enabled (ada-pi-backend.service)"
echo ""

if [ "$INSTALL_KIOSK" = true ]; then
    echo "🖥️  Step 8/11: Setting up kiosk mode..."

    # Create kiosk script
    cat > /usr/local/bin/ada-pi-kiosk << 'KIOSK_EOF'
#!/bin/bash
# Disable screen blanking
xset s off
xset -dpms
xset s noblank

# Hide cursor
unclutter -idle 0.5 -root &

# Wait for backend to start
sleep 10

# Launch Chromium in kiosk mode
chromium-browser \
    --kiosk \
    --noerrdialogs \
    --disable-infobars \
    --no-first-run \
    --disable-session-crashed-bubble \
    --disable-component-update \
    --check-for-update-interval=31536000 \
    http://localhost:8000 &

# Keep script running
wait
KIOSK_EOF

    chmod +x /usr/local/bin/ada-pi-kiosk

    # Create autostart directory
    mkdir -p /home/${ACTUAL_USER}/.config/autostart

    # Create autostart file
    cat > /home/${ACTUAL_USER}/.config/autostart/ada-pi-kiosk.desktop << 'AUTOSTART_EOF'
[Desktop Entry]
Type=Application
Name=ADA-Pi Kiosk
Exec=/usr/local/bin/ada-pi-kiosk
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
AUTOSTART_EOF

    chown -R ${ACTUAL_USER}:${ACTUAL_USER} /home/${ACTUAL_USER}/.config

    # Set default to graphical mode
    systemctl set-default graphical.target > /dev/null 2>&1

    echo "✓ Kiosk mode configured"
    echo ""
else
    echo "🖥️  Step 8/11: Skipping kiosk mode..."
    echo "✓ Headless mode (no display setup)"
    echo ""
fi

echo "🌐 Step 9/11: Installing Tailscale..."
if command -v tailscale &> /dev/null; then
    echo "✓ Tailscale already installed"
else
    echo "   (This may take a minute...)"
    curl -fsSL https://tailscale.com/install.sh | sh > /dev/null 2>&1
    echo "✓ Tailscale installed"
fi
echo ""

echo "🔧 Step 10/11: Configuring firewall..."
# Check if UFW is installed
if command -v ufw &> /dev/null; then
    ufw allow 8000/tcp > /dev/null 2>&1 || true
    ufw allow 9000/tcp > /dev/null 2>&1 || true
    echo "✓ Firewall configured (ports 8000, 9000 allowed)"
else
    echo "✓ No firewall detected (skipped)"
fi
echo ""

echo "🚀 Step 11/11: Starting services..."
systemctl start ada-pi-backend
sleep 3

# Check if service started
if systemctl is-active --quiet ada-pi-backend; then
    echo "✓ ADA-Pi backend service started successfully"
else
    echo "⚠️  Service may have issues - check logs with: sudo journalctl -u ada-pi-backend -f"
fi
echo ""

# Get IP addresses
LOCAL_IP=$(hostname -I | awk '{print $1}')
TAILSCALE_IP=""

# Try to get Tailscale IP if already connected
if command -v tailscale &> /dev/null; then
    if tailscale status > /dev/null 2>&1; then
        TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "")
    fi
fi

echo "╔════════════════════════════════════════════════╗"
echo "║  ✅ Installation Complete!                     ║"
echo "╚════════════════════════════════════════════════╝"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 SERVICE STATUS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✓ Backend: Running on ports 8000 (HTTP) and 9000 (WebSocket)"
echo "✓ Frontend: Web dashboard ready"
echo "✓ Systemd: Service enabled (auto-starts on boot)"
echo "✓ Service name: ada-pi-backend.service"

if [ "$INSTALL_KIOSK" = true ]; then
    echo "✓ Kiosk: Will auto-start on display after reboot"
fi
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📱 ACCESS YOUR DASHBOARD"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ "$INSTALL_KIOSK" = true ]; then
    echo "On Connected Display:"
    echo "   • Reboot to see dashboard in kiosk mode"
    echo "   • Fullscreen, no menus"
    echo ""
fi

echo "Web Browser (Local Network):"
echo "   http://$LOCAL_IP:8000"
echo ""

if [ -n "$TAILSCALE_IP" ]; then
    echo "Remote Access (Tailscale):"
    echo "   http://$TAILSCALE_IP:8000"
    echo ""
    echo "✓ Tailscale is connected!"
    echo "  Access from anywhere using this URL"
else
    echo "⚠️  Tailscale Setup Required for Remote Access:"
    echo ""
    echo "1. Connect to Tailscale:"
    echo "   sudo tailscale up"
    echo ""
    echo "2. Follow the link to authenticate"
    echo ""
    echo "3. Get your Tailscale IP:"
    echo "   tailscale ip -4"
    echo ""
    echo "4. Access from anywhere:"
    echo "   http://[tailscale-ip]:8000"
    echo ""
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔒 SECURITY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⚠️  IMPORTANT: Change default password!"
echo ""
echo "Default Login:"
echo "   Username: admin"
echo "   Password: admin"
echo ""
echo "To change:"
echo "   sudo nano /opt/ada-pi/backend/config.json"
echo "   sudo systemctl restart ada-pi-backend"
echo ""

if [ "$INSTALL_KIOSK" = true ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🖥️  KIOSK MODE"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "✓ Kiosk mode installed"
    echo "✓ Will auto-start on boot"
    echo "✓ Dashboard shows fullscreen"
    echo ""
    echo "Reboot to activate:"
    echo "   sudo reboot"
    echo ""
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 USEFUL COMMANDS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Check status:"
echo "   sudo systemctl status ada-pi-backend"
echo ""
echo "View logs (live):"
echo "   sudo journalctl -u ada-pi-backend -f"
echo ""
echo "View recent logs:"
echo "   sudo journalctl -u ada-pi-backend -n 100"
echo ""
echo "Restart service:"
echo "   sudo systemctl restart ada-pi-backend"
echo ""
echo "Stop service:"
echo "   sudo systemctl stop ada-pi-backend"
echo ""
echo "Test API:"
echo "   curl http://localhost:8000/api/system/info | jq"
echo ""
echo "Test WebSocket (check ports):"
echo "   sudo netstat -tuln | grep -E '8000|9000'"
echo ""

if [ -z "$TAILSCALE_IP" ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🚗 NEXT STEP FOR VEHICLE USE"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Connect to Tailscale now:"
    echo "   sudo tailscale up"
    echo ""
    echo "Then access your dashboard from anywhere!"
    echo ""
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 All done! Happy tracking! 🚗💨"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
