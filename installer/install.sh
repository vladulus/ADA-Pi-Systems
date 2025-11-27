#!/bin/bash
echo ""
echo "===================================="
echo "      ADA-Pi Unified Installer"
echo "===================================="
echo ""

INSTALL_DIR="/opt/ada-pi"
VENV_DIR="$INSTALL_DIR/venv"
SERVICE_FILE="/etc/systemd/system/ada-pi-backend.service"
PROJECT_ROOT="$(dirname $(realpath $0))/.."
BACKEND_SRC="$PROJECT_ROOT/backend"

# --------------------------------------
# ROOT CHECK
# --------------------------------------
if [ "$EUID" -ne 0 ]; then
  echo "❌ Please run as root: sudo ./install.sh"
  exit 1
fi

# --------------------------------------
# SYSTEM DEPENDENCIES
# --------------------------------------
echo "==> Installing system dependencies..."
apt update
apt install -y \
  python3 python3-pip python3-venv \
  python3-smbus python3-serial \
  modemmanager \
  bluez bluez-tools \
  i2c-tools \
  network-manager \
  rfkill \
  jq \
  curl \
  git \
  python3-gi python3-dbus python3-psutil

# --------------------------------------
# ENABLE HARDWARE INTERFACES
# --------------------------------------
if grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
  echo "==> Raspberry Pi detected — enabling I2C/SPI/UART..."
  raspi-config nonint do_i2c 0
  raspi-config nonint do_spi 0
  raspi-config nonint do_serial 0
  modprobe i2c-dev
else
  echo "==> Not a Raspberry Pi. Skipping raspi-config setup."
fi

# --------------------------------------
# CREATE INSTALL DIR
# --------------------------------------
echo "==> Preparing installation directory..."
mkdir -p "$INSTALL_DIR/backend"

# --------------------------------------
# COPY BACKEND FILES
# --------------------------------------
echo "==> Copying backend source..."
rsync -av --delete --exclude="__pycache__" "$BACKEND_SRC/" "$INSTALL_DIR/backend/"

# --------------------------------------
# CREATE PYTHON VENV
# --------------------------------------
echo "==> Creating Python virtual environment..."
python3 -m venv "$VENV_DIR"

echo "==> Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# --------------------------------------
# INSTALL PYTHON DEPENDENCIES
# --------------------------------------
REQ_FROZEN="$BACKEND_SRC/requirements-frozen.txt"

echo "==> Installing Python dependencies inside virtual environment..."
pip install --upgrade pip

if [ -f "$REQ_FROZEN" ]; then
    pip install -r "$REQ_FROZEN"
else
    pip install -r "$BACKEND_SRC/requirements.txt"
fi

# --------------------------------------
# FIX PERMISSIONS
# --------------------------------------
echo "==> Adjusting user permissions..."
usermod -aG dialout "$SUDO_USER"
usermod -aG bluetooth "$SUDO_USER"
usermod -aG i2c "$SUDO_USER"

# --------------------------------------
# RESTART MODEMMANAGER
# --------------------------------------
echo "==> Restarting ModemManager..."
systemctl restart ModemManager 2>/dev/null

# --------------------------------------
# REMOVE OLD SERVICES
# --------------------------------------
echo "==> Removing legacy ADA-Pi service units..."
rm -f /etc/systemd/system/ada-pi-*.service

# --------------------------------------
# INSTALL SYSTEMD SERVICE
# --------------------------------------
echo "==> Installing systemd service..."
cat << EOF > "$SERVICE_FILE"
[Unit]
Description=ADA-Pi Backend Engine
After=network.target

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR/backend
ExecStart=$VENV_DIR/bin/python $INSTALL_DIR/backend/main.py
Restart=always
RestartSec=3
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

chmod 644 "$SERVICE_FILE"

# --------------------------------------
# ENABLE SERVICE
# --------------------------------------
systemctl daemon-reload
systemctl enable ada-pi-backend.service
systemctl restart ada-pi-backend.service

# --------------------------------------
# DONE
# --------------------------------------
echo ""
echo "============================================"
echo " ADA-Pi Backend installation completed!"
echo " Using virtual environment at: $VENV_DIR"
echo "============================================"
echo ""
systemctl status ada-pi-backend.service --no-pager
