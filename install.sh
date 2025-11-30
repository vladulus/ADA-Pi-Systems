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

    sudo systemctl daemon-reload

    green "Old installation removed!"
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

    green "Backend systemd service installed & started!"
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

    read -p "Enter Cloudflare hostname (example: pi01): " PIHOST

    sudo cloudflared tunnel login
    sudo cloudflared tunnel create "$PIHOST"

    TUNNEL_ID=$(sudo ls /root/.cloudflared/*.json | head -n 1 | sed 's/[^0-9a-zA-Z]//g')

sudo bash -c "cat > /etc/cloudflared/config.yml" <<EOF
tunnel: $TUNNEL_ID
credentials-file: /root/.cloudflared/$TUNNEL_ID.json

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

    yellow "Run this manually to authenticate:"
    echo "sudo tailscale up"
}



# ----------------------------------------
# UNINSTALL EVERYTHING
# ----------------------------------------
uninstall_all() {
    red "Uninstalling ADA-Pi completely..."
    cleanup_old
    sudo apt purge -y tailscale cloudflared || true
    sudo apt autoremove -y
    green "ADA-Pi fully uninstalled."
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
echo "3) Networking Options (Cloudflare / Tailscale / Both / None)"
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
    5) uninstall_all ;;
    0) exit 0 ;;
    *) red "Invalid choice!"; sleep 1; main_menu ;;
esac
}


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

# Start
check_os
main_menu

