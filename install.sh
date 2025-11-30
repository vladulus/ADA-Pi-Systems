#!/bin/bash
# ADA-PI SYSTEMS — COMPLETE INSTALLER (HEADLESS / KIOSK)
# Supports: Cloudflare / Tailscale / Both / None
# Updated for Python 3.11 / Raspberry Pi OS Bookworm

# ==================================================================
# GLOBAL VARIABLES
# ==================================================================
REPO_DIR="/home/vlad/ADA-Pi-Systems"
BACKEND_SRC="$REPO_DIR/backend"
FRONTEND_SRC="$REPO_DIR/frontend"
INSTALL_DIR="/opt/ada-pi"
BACKEND_DIR="$INSTALL_DIR/backend"
FRONTEND_DIR="/var/www/ada-pi"
SERVICE_FILE="/etc/systemd/system/ada-pi-backend.service"
DOMAIN="adasystems.uk"
REBOOT_REQUIRED=0

# ==================================================================
# WHIPTAIL CHECK
# ==================================================================
if ! command -v whiptail >/dev/null 2>&1; then
    echo "Installing whiptail..."
    apt-get update
    apt-get install -y whiptail
fi

# ==================================================================
# ROOT CHECK
# ==================================================================
if [[ $EUID -ne 0 ]]; then
   whiptail --title "ADA-Pi Installer" --msgbox "Run with: sudo ./install.sh" 10 60
   exit 1
fi

# ==================================================================
# HELPER — PRINT LOG
# ==================================================================
log() { echo "[ADA-PI] $1"; }

# ==================================================================
# CLEAN OLD INSTALL
# ==================================================================
clean_old_install() {
    log "Cleaning previous ADA-Pi installation..."

    systemctl stop ada-pi-backend 2>/dev/null
    systemctl disable ada-pi-backend 2>/dev/null
    rm -f "$SERVICE_FILE"

    rm -rf "$INSTALL_DIR"
    rm -rf "$FRONTEND_DIR"

    rm -rf /etc/cloudflared
    rm -rf /root/.cloudflared
    rm -f /usr/bin/cloudflared
    rm -f /etc/systemd/system/cloudflared.service

    whiptail --title "Cleanup Complete" --msgbox "Old ADA-Pi removed." 10 60
}

# ==================================================================
# UNINSTALL
# ==================================================================
uninstall_adapi() {
    CHOICE=$(whiptail --title "Uninstall ADA-Pi" --yesno \
        "This removes backend, frontend, Cloudflare, Tailscale, and services.\nContinue?" \
        12 60)
    [[ $? -ne 0 ]] && return
    clean_old_install
}

# ==================================================================
# MAIN MENU
# ==================================================================
main_menu() {
    CHOICE=$(whiptail --title "ADA-Pi Installer" --menu "Choose Option:" 20 60 10 \
        "1" "Headless Installation" \
        "2" "Kiosk Installation" \
        "3" "Uninstall ADA-Pi" \
        "0" "Exit" \
        3>&1 1>&2 2>&3)

    case $CHOICE in
        1) INSTALL_MODE="HEADLESS"; install_backend_full ;;
        2) INSTALL_MODE="KIOSK"; install_backend_full ;;
        3) uninstall_adapi ;;
        0) exit 0 ;;
    esac
}

# ==================================================================
# BACKEND INSTALLATION
# ==================================================================
install_backend_full() {

    whiptail --title "Confirm Installation" --yesno \
    "Install ADA-Pi in $INSTALL_MODE mode?\n\nBackend → $BACKEND_DIR\nFrontend → $FRONTEND_DIR" \
    12 60
    [[ $? -ne 0 ]] && return

    rm -rf "$INSTALL_DIR"
    rm -rf "$FRONTEND_DIR"
    mkdir -p "$BACKEND_DIR"

    log "Installing system packages..."
    apt update
    apt install -y python3-venv python3-dev python3-pip \
        python3-dbus libdbus-1-dev dbus-user-session \
        i2c-tools raspi-config

    log "Creating Python venv..."
    python3 -m venv "$BACKEND_DIR/venv"
    source "$BACKEND_DIR/venv/bin/activate"

    pip install --upgrade pip wheel setuptools
    pip install flask flask-cors requests pyserial python-dotenv psutil websocket-client
    pip install smbus2 dbus-next

    deactivate

    log "Copying backend..."
    cp -r "$BACKEND_SRC/"* "$BACKEND_DIR/"
    chown -R root:root "$BACKEND_DIR"

    # =============================================================
    # PATCH HELPERS.PY (FULL JWT IMPLEMENTATION)
    # =============================================================
    log "Patching helpers.py with full JWT implementation..."

    cat > "$BACKEND_DIR/api/helpers.py" << 'EOF'
import time
import jwt
import requests
from functools import wraps
from flask import request, jsonify

AUTH_API_URL = "https://www.adasystems.uk/api"

token_cache = {}
TOKEN_CACHE_DURATION = 300  # 5 minutes

def validate_jwt_with_api(token):
    cache_key = token[:50]
    if cache_key in token_cache:
        cached_data, timestamp = token_cache[cache_key]
        if time.time() - timestamp < TOKEN_CACHE_DURATION:
            return cached_data

    try:
        response = requests.post(
            f"{AUTH_API_URL}/auth/validate",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5
        )

        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                user = result.get("data", {})
                token_cache[cache_key] = (user, time.time())
                return user

        return None
    except Exception as e:
        print("Token validation error:", e)
        return None


def create_jwt(payload, secret):
    try:
        return jwt.encode(payload, secret, algorithm="HS256")
    except Exception as e:
        print("JWT create error:", e)
        return None


def decode_jwt_locally(token, secret):
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except Exception as e:
        print("JWT decode error:", e)
        return None


def is_local_request():
    return request.remote_addr in ["127.0.0.1", "::1", "localhost"]


def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):

        if is_local_request():
            return f(*args, **kwargs)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "missing_auth"}), 401

        token = auth_header.split(" ", 1)[1]

        user = validate_jwt_with_api(token)
        if not user:
            return jsonify({"error": "invalid_token"}), 401

        request.user = user
        return f(*args, **kwargs)

    return wrapper


def has_permission(perm):
    if is_local_request():
        return True

    return hasattr(request, "user") and \
        perm in request.user.get("permissions", [])


def has_role(role):
    if is_local_request():
        return True

    return hasattr(request, "user") and \
        request.user.get("role") == role


def ok(data=None):
    return jsonify({"status": "ok", "data": data})


def fail(msg):
    return jsonify({"status": "error", "message": msg}), 400
EOF

    log "helpers.py updated successfully."

    # =============================================================
    # CREATE BACKEND SERVICE
    # =============================================================
    log "Creating backend service..."
    cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=ADA-Pi Backend
After=network.target

[Service]
ExecStart=$BACKEND_DIR/venv/bin/python $BACKEND_DIR/main.py
WorkingDirectory=$BACKEND_DIR
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable ada-pi-backend
    systemctl restart ada-pi-backend

    [[ "$INSTALL_MODE" == "KIOSK" ]] && install_frontend || select_network_tools
}

# ==================================================================
# FRONTEND INSTALL
# ==================================================================
install_frontend() {
    log "Installing frontend..."
    mkdir -p "$FRONTEND_DIR"
    cp -r "$FRONTEND_SRC/"* "$FRONTEND_DIR/"
    chown -R vlad:vlad "$FRONTEND_DIR"

    whiptail --title "Frontend Installed" --msgbox "Frontend installed." 10 50
    setup_kiosk_mode
}

# ==================================================================
# KIOSK MODE
# ==================================================================
setup_kiosk_mode() {
    log "Setting up Kiosk Mode..."

    apt install -y chromium-browser xdotool unclutter lightdm

    mkdir -p /etc/systemd/system/getty@tty1.service.d
    cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf <<EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin vlad --noclear %I \$TERM
EOF

    mkdir -p /home/vlad/.config/autostart
    cat > /etc/xdg/autostart/ada-pi-kiosk.desktop <<EOF
[Desktop Entry]
Type=Application
Name=ADA-Pi Kiosk
Exec=chromium-browser --noerrdialogs --disable-session-crashed-bubble --incognito --kiosk http://localhost:8000
EOF

    whiptail --title "Kiosk Ready" --msgbox "Kiosk Mode enabled." 12 60
    select_network_tools
}

# ==================================================================
# NETWORK TOOL MENU
# ==================================================================
select_network_tools() {
    CHOICE=$(whiptail --title "Connectivity" --menu "Choose:" 20 70 10 \
        "1" "Cloudflare Tunnel" \
        "2" "Tailscale" \
        "3" "Both" \
        "4" "None" \
        3>&1 1>&2 2>&3)

    case $CHOICE in
        1) install_cloudflare ;;
        2) install_tailscale ;;
        3) install_cloudflare; install_tailscale ;;
        4) connectivity_done ;;
    esac
}

# ==================================================================
# CLOUDFLARE (INTELLIGENT: REUSE OR NEW)
# ==================================================================
install_cloudflare() {

    CF_CONFIG="/etc/cloudflared/config.yml"
    CF_UUID=""
    CF_HOST=""

    if ls /root/.cloudflared/*.json >/dev/null 2>&1; then
        CF_UUID=$(basename /root/.cloudflared/*.json .json)
    fi

    if [[ -f "$CF_CONFIG" ]]; then
        CF_HOST=$(grep hostname "$CF_CONFIG" | awk '{print $2}')
    fi

    if [[ -n "$CF_UUID" && -n "$CF_HOST" ]]; then

        CHOICE=$(whiptail --title "Cloudflare Detected" --menu \
            "Existing Tunnel:\nUUID: $CF_UUID\nHost: $CF_HOST\n" \
            20 60 10 \
            "1" "Reuse existing tunnel" \
            "2" "Create new tunnel" \
            "3" "Cancel" \
            3>&1 1>&2 2>&3)

        [[ $CHOICE == 1 ]] && {
            systemctl enable cloudflared
            systemctl restart cloudflared
            whiptail --title "Cloudflare Active" --msgbox "$CF_HOST is active." 10 60
            return
        }

        [[ $CHOICE == 3 ]] && return

        rm -rf /etc/cloudflared /root/.cloudflared
        rm -f /etc/systemd/system/cloudflared.service
    fi

    whiptail --msgbox "Installing Cloudflare…" 10 60

    curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg \
        | tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null

    echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] \
https://pkg.cloudflare.com/cloudflared bookworm main" \
        > /etc/apt/sources.list.d/cloudflared.list

    apt update
    apt install -y cloudflared

    HOSTNAME=$(whiptail --inputbox "Enter hostname (must end with .$DOMAIN):" 12 60 "" \
        3>&1 1>&2 2>&3)

    [[ "$HOSTNAME" != *".$DOMAIN" ]] && {
        whiptail --msgbox "Invalid hostname." 10 60
        return
    }

    cloudflared tunnel login
    cloudflared tunnel create "$HOSTNAME"

    UUID=$(cloudflared tunnel list | grep "$HOSTNAME" | awk '{print $1}')

    mkdir -p /etc/cloudflared

    cat > /etc/cloudflared/config.yml <<EOF
tunnel: $UUID
credentials-file: /root/.cloudflared/${UUID}.json

ingress:
  - hostname: $HOSTNAME
    service: http://localhost:8000
  - service: http_status:404
EOF

    cat > /etc/systemd/system/cloudflared.service <<EOF
[Unit]
Description=Cloudflare Tunnel
After=network.target

[Service]
ExecStart=/usr/bin/cloudflared --no-autoupdate --config /etc/cloudflared/config.yml tunnel run
Restart=always

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable cloudflared
    systemctl restart cloudflared

    whiptail --title "Cloudflare Ready" --msgbox "New tunnel created:\nhttps://$HOSTNAME" 12 60
}

# ==================================================================
# TAILSCALE
# ==================================================================
install_tailscale() {
    whiptail --msgbox "Installing Tailscale…" 10 60

    curl -fsSL https://tailscale.com/install.sh | sh
    systemctl enable --now tailscaled
    tailscale up

    IP=$(tailscale ip -4)
    whiptail --msgbox "Tailscale active. IP: $IP" 10 60
}

# ==================================================================
# CONNECTIVITY DONE
# ==================================================================
connectivity_done() {
    enable_interfaces
    final_summary
}

# ==================================================================
# ENABLE PI INTERFACES
# ==================================================================
enable_interfaces() {
    raspi-config nonint do_i2c 0
    raspi-config nonint do_spi 0
    raspi-config nonint do_serial 1
    raspi-config nonint do_serial_hw 0
    REBOOT_REQUIRED=1
}

# ==================================================================
# FINAL SUMMARY
# ==================================================================
final_summary() {

    SUMMARY="Installation Finished\n\nMode: $INSTALL_MODE\n"

    systemctl is-active --quiet cloudflared && SUMMARY+="Cloudflare: Installed\n" || SUMMARY+="Cloudflare: Not installed\n"
    systemctl is-active --quiet tailscaled && SUMMARY+="Tailscale: Installed\n" || SUMMARY+="Tailscale: Not installed\n"

    SUMMARY+="\nBackend: $BACKEND_DIR\n"
    [[ "$INSTALL_MODE" == "KIOSK" ]] && SUMMARY+="Frontend: $FRONTEND_DIR (Kiosk Enabled)\n"

    whiptail --msgbox "$SUMMARY" 20 60
    
    [[ $REBOOT_REQUIRED -eq 1 ]] && {
        whiptail --yesno "Reboot now?" 10 60 && reboot
    }
}

# ==================================================================
# ENTRY POINT
# ==================================================================
clear
whiptail --title "ADA-Pi Installer" --msgbox \
"Welcome to ADA-Pi Installer.\nPress OK to continue." 10 60

while true; do
    main_menu
done
