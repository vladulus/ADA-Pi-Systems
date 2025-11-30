#!/bin/bash
set -e

# ========================================
# ADA-Pi Installer v2.0 (Fully Rewritten)
# ========================================

INSTALL_DIR="/opt/ada-pi"
BACKEND_DIR="$INSTALL_DIR/backend"
FRONTEND_DIR="$INSTALL_DIR/frontend"
SERVICE_FILE="/etc/systemd/system/ada-pi-backend.service"
USER_VLAD="vlad"

cyan() { echo -e "\e[36m$1\e[0m"; }
green() { echo -e "\e[32m$1\e[0m"; }
yellow() { echo -e "\e[33m$1\e[0m"; }
red() { echo -e "\e[31m$1\e[0m"; }


# ----------------------------------------
# CHECK OS COMPATIBILITY
# ----------------------------------------
check_os() {
    OS=$(lsb_release -cs)
    if [[ "$OS" != "bookworm" && "$OS" != "bullseye" ]]; then
        yellow "Warning: OS reported as '$OS'. Forcing bookworm for Cloudflare."
    fi

    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv curl git
}


# ----------------------------------------
# CLEANUP OLD INSTALLATIONS
# ----------------------------------------
cleanup_old() {
    yellow "Cleaning old ADA-Pi installation..."

    sudo systemctl stop ada-pi-backend 2>/dev/null || true
    sudo systemctl disable ada-pi-backend 2>/dev/null || true
    sudo rm -f "$SERVICE_FILE"

    sudo rm -rf "$INSTALL_DIR"
    sudo rm -rf /etc/cloudflared
    sudo rm -rf /root/.cloudflared
    sudo rm -rf /var/log/ada-pi

    sudo systemctl daemon-reload

    green "Old installation removed!"
}


# ----------------------------------------
# SUPER UNINSTALL (From Upgraded Script)
# ----------------------------------------
super_uninstall() {
    echo "=============================================="
    echo "      ADA-PI SYSTEMS — UNINSTALL SCRIPT"
    echo "=============================================="
    echo ""

    echo "[1/7] Stopping backend service..."
    if systemctl is-active --quiet "ada-pi-backend.service"; then
        sudo systemctl stop "ada-pi-backend.service"
    fi

    echo "Disabling backend service..."
    sudo systemctl disable "ada-pi-backend.service" >/dev/null 2>&1
    sudo rm -f "/etc/systemd/system/ada-pi-backend.service"

    echo ""
    echo "[2/7] Removing ADA-PI installation..."
    if [ -d "$INSTALL_DIR" ]; then
        sudo rm -rf "$INSTALL_DIR"
        echo "✔ Deleted $INSTALL_DIR"
    else
        echo "Skipping — install directory not found."
    fi

    echo ""
    echo "[3/7] Removing logs..."
    if [ -d "/var/log/ada-pi" ]; then
        sudo rm -rf "/var/log/ada-pi"
        echo "✔ Logs removed"
    else
        echo "Skipping — no logs found."
    fi

    echo ""
    echo "=============================================="
    echo "       Cloudflare Tunnel Removal (Optional)"
    echo "=============================================="

    read -p "Remove Cloudflare Tunnel config? (yes/no): " REMOVE_CF
    if [[ "$REMOVE_CF" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo "Removing Cloudflare config..."

        sudo systemctl stop cloudflared.service 2>/dev/null || true
        sudo systemctl disable cloudflared.service 2>/dev/null || true
        sudo rm -rf /etc/cloudflared
        sudo rm -rf /root/.cloudflared

        echo "✔ Cloudflare removed"
    else
        echo "Skipping Cloudflare removal."
    fi

    echo ""
    echo "=============================================="
    echo "       Tailscale Removal (Optional)"
    echo "=============================================="

    read -p "Remove Tailscale? (yes/no): " REMOVE_TS
    if [[ "$REMOVE_TS" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        sudo systemctl stop tailscaled 2>/dev/null || true
        sudo systemctl disable tailscaled 2>/dev/null || true
        sudo apt purge -y tailscale >/dev/null 2>&1
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

    read -p "Remove global Python packages? (yes/no): " REMOVE_PY
    if [[ "$REMOVE_PY" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        sudo pip3 uninstall -y paho-mqtt requests python-dotenv pyserial psutil websocket-client >/dev/null 2>&1
        echo "✔ Python deps removed"
    else
        echo "Skipping Python cleanup."
    fi

    echo ""
    echo "✔ ADA-PI FULL UNINSTALL COMPLETE"
    echo ""
}


# ----------------------------------------
# INSTALL BACKEND
# ----------------------------------------
install_backend() {
    cyan "Installing Backend..."

    sudo mkdir -p "$BACKEND_DIR"
    sudo cp -r backend/* "$BACKEND_DIR"

    cd "$BACKEND_DIR"
    python3 -m venv venv
    source venv/bin/activate

    pip install --upgrade pip
    pip install -r requirements.txt

    create_backend_service
    green "Backend installed!"
}


create_backend_service() {
sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=ADA-Pi Backend
After=network.target

[Service]
WorkingDirectory=$BACKEND_DIR
ExecStart=$BACKEND_DIR/venv/bin/python $BACKEND_DIR/main.py
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable ada-pi-backend
    sudo systemctl restart ada-pi-backend

    green "Backend service installed & started!"
}


# ----------------------------------------
# INSTALL KIOSK MODE
# ----------------------------------------
install_kiosk() {
    cyan "Installing kiosk mode..."

    sudo mkdir -p "$FRONTEND_DIR"
    sudo cp -r frontend/* "$FRONTEND_DIR"

    sudo apt install -y chromium-browser xserver-xorg x11-xserver-utils unclutter

    sudo mkdir -p /etc/systemd/system/getty@tty1.service.d
sudo bash -c "cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf" <<EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin $USER_VLAD --noclear %I \$TERM
EOF

sudo bash -c "cat > /home/$USER_VLAD/.bash_profile" <<EOF
chromium-browser --noerrdialogs --disable-infobars --kiosk http://localhost:8000
EOF

    green "Kiosk mode installed!"
}


# ----------------------------------------
# CLOUDFLARE INSTALL
# ----------------------------------------
install_cloudflare() {
    cyan "Installing Cloudflare Tunnel..."

    sudo mkdir -p /usr/share/keyrings
    curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null

sudo bash -c "cat > /etc/apt/sources.list.d/cloudflared.list" <<EOF
deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared bookworm main
EOF

    sudo apt update
    sudo apt install -y cloudflared

    read -p "Enter hostname (example: pi01): " PIHOST

    sudo cloudflared tunnel login
    sudo cloudflared tunnel create "$PIHOST"

    CF_JSON=$(ls /root/.cloudflared/*.json | head -n1)
    TUNNEL_ID=$(basename "$CF_JSON" .json)

sudo bash -c "cat > /etc/cloudflared/config.yml" <<EOF
tunnel: $TUNNEL_ID
credentials-file: $CF_JSON

ingress:
  - hostname: $PIHOST.adasystems.uk
    service: http://localhost:8000
  - service: http_status:404
EOF

    sudo cloudflared service install
    sudo systemctl enable cloudflared
    sudo systemctl restart cloudflared

    green "Cloudflare Tunnel installed!"
}


# ----------------------------------------
# INSTALL TAILSCALE
# ----------------------------------------
install_tailscale() {
    cyan "Installing Tailscale..."
    curl -fsSL https://tailscale.com/install.sh | sh

    yellow "Run this to authenticate:"
    echo "sudo tailscale up"
}


# ----------------------------------------
# NETWORK MENU
# ----------------------------------------
networking_menu() {
clear
cyan "Networking Options"
echo ""
echo "1) Cloudflare Tunnel"
echo "2) Tailscale"
echo "3) Both"
echo "4) None"
echo "0) Back"
read -p "Choose: " NET

case $NET in
    1) install_cloudflare ;;
    2) install_tailscale ;;
    3) install_cloudflare; install_tailscale ;;
    4) yellow "No networking selected." ;;
    0) main_menu ;;
    *) red "Invalid choice!"; networking_menu ;;
esac
}


# ----------------------------------------
# MAIN MENU
# ----------------------------------------
main_menu() {
clear
cyan "====================================="
cyan "         ADA-Pi Installer"
cyan "====================================="
echo ""
echo "1) Install Backend Only"
echo "2) Install Full System (Backend + Kiosk)"
echo "3) Networking Options"
echo "4) Cleanup Old Installation"
echo "5) Uninstall ADA-Pi Completely"
echo "0) Exit"
echo ""
read -p "Choose option: " CHOICE

case $CHOICE in
    1) cleanup_old; install_backend ;;
    2) cleanup_old; install_backend; install_kiosk ;;
    3) networking_menu ;;
    4) cleanup_old ;;
    5) super_uninstall ;;
    0) exit 0 ;;
    *) red "Invalid choice!"; sleep 1; main_menu ;;
esac
}


# Run installer
check_os
main_menu

