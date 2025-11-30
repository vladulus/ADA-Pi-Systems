#!/bin/bash
# ADA-PI SYSTEMS — COMPLETE INSTALLER (HEADLESS / KIOSK)
# Supports: Cloudflare / Tailscale / Both / None
# Updated for Python 3.11 / Raspberry Pi OS Bookworm
# Author: ChatGPT (generated for vlad)

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
    sudo apt-get update
    sudo apt-get install -y whiptail
fi

# ==================================================================
# ROOT CHECK
# ==================================================================
if [[ $EUID -ne 0 ]]; then
   whiptail --title "ADA-Pi Installer" --msgbox "Please run this installer with: sudo ./install.sh" 10 60
   exit 1
fi

# ==================================================================
# HELPER — PRINT LOG
# ==================================================================
log() {
    echo "[ADA-PI] $1"
}

# ==================================================================
# HELPER — ENABLE PI INTERFACES
# ==================================================================
enable_interfaces() {
    log "Enabling Raspberry Pi hardware interfaces (I2C, SPI, UART)..."

    raspi-config nonint do_i2c 0
    raspi-config nonint do_spi 0
    raspi-config nonint do_serial 1
    raspi-config nonint do_serial_hw 0

    REBOOT_REQUIRED=1
    log "Interfaces enabled."
}

# ==================================================================
# HELPER — CLEAN OLD INSTALL
# ==================================================================
clean_old_install() {
    log "Removing old ADA-Pi installation..."

    systemctl stop ada-pi-backend 2>/dev/null
    systemctl disable ada-pi-backend 2>/dev/null
    rm -f "$SERVICE_FILE"

    rm -rf "$INSTALL_DIR"
    rm -rf "$FRONTEND_DIR"

    rm -rf /etc/cloudflared
    rm -rf /root/.cloudflared
    rm -f /usr/bin/cloudflared
    rm -f /etc/systemd/system/cloudflared.service

    whiptail --title "Cleanup Complete" --msgbox "Old ADA-Pi installation removed." 10 60
}

# ==================================================================
# UNINSTALL — INSIDE INSTALLER
# ==================================================================
uninstall_adapi() {
    CHOICE=$(whiptail --title "Uninstall ADA-Pi" --yesno "This will REMOVE backend, frontend, Cloudflare, Tailscale and services.\nContinue?" 12 60)
    if [[ $? -ne 0 ]]; then return; fi

    clean_old_install

    whiptail --title "Uninstall Complete" --msgbox "ADA-Pi has been completely uninstalled." 10 60
}

# ==================================================================
# MAIN MENU FUNCTION
# ==================================================================
main_menu() {
    CHOICE=$(whiptail --title "ADA-Pi Installer" --menu "Select an option:" 20 60 10 \
        "1" "Headless Installation" \
        "2" "Kiosk Installation" \
        "3" "Uninstall ADA-Pi" \
        "0" "Exit Installer" \
        3>&1 1>&2 2>&3)

    case $CHOICE in
        1) INSTALL_MODE="HEADLESS"; install_backend_full ;;
        2) INSTALL_MODE="KIOSK"; install_backend_full ;;
        3) uninstall_adapi ;;
        0) exit 0 ;;
    esac
}

# ==================================================================
# INSTALL BACKEND (VENV + REQUIREMENTS + SYSTEMD SERVICE)
# ==================================================================
install_backend_full() {

    # SYSTEM PACKAGES
    log "Installing system dependencies…"
    apt update
    apt install -y python3-venv python3-dev build-essential git \
        libsystemd-dev i2c-tools network-manager policykit-1 \
        python3-pip python3-wheel curl unzip

    mkdir -p "$BACKEND_DIR"

    log "Creating Python virtual environment…"
    python3 -m venv "$BACKEND_DIR/venv"

    log "Activating venv and installing backend dependencies…"
    source "$BACKEND_DIR/venv/bin/activate"

    pip install --upgrade pip setuptools wheel

    pip install \
        flask \
        flask-cors \
        websocket-client \
        requests \
        python-dotenv \
        psutil \
        pyserial \
        smbus2 \
        dbus-next \
        paho-mqtt \
        MarkupSafe==3.0.3

    deactivate

    # COPY BACKEND SOURCE
    log "Copying backend files…"
    rm -rf "$BACKEND_DIR/app"
    mkdir -p "$BACKEND_DIR"
    cp -r "$BACKEND_SRC/"* "$BACKEND_DIR/"

    # PATCH ENGINE & WORKER
    log "Updating NetworkManager engine and worker…"

    # Writing new engine file
    cat > "$BACKEND_DIR/engine/networkmanager_dbus.py" << 'EOF'
#!/usr/bin/env python3
# Modern NetworkManager engine using dbus-next

import asyncio
from dbus_next.aio import MessageBus
from dbus_next import Variant

NM_SERVICE = "org.freedesktop.NetworkManager"
NM_PATH = "/org/freedesktop/NetworkManager"
NM_IFACE = "org.freedesktop.NetworkManager"
NM_DEV_IFACE = "org.freedesktop.NetworkManager.Device"
NM_WIRELESS_IFACE = "org.freedesktop.NetworkManager.Device.Wireless"
NM_AP_IFACE = "org.freedesktop.NetworkManager.AccessPoint"
NM_IP4_IFACE = "org.freedesktop.NetworkManager.IP4Config"

DEVICE_TYPE_ETHERNET = 1
DEVICE_TYPE_WIFI = 2

class NMEngine:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.bus = self.loop.run_until_complete(MessageBus().connect())
            obj = self.loop.run_until_complete(self.bus.introspect(NM_SERVICE, NM_PATH))
            self.nm = self.bus.get_proxy_object(NM_SERVICE, NM_PATH, obj).get_interface(NM_IFACE)
        except Exception as e:
            print("[NMEngine] Failed:", e)
            self.bus = None

    def _run(self, coro):
        return self.loop.run_until_complete(coro)

    async def _get_prop(self, path, iface, prop):
        try:
            obj = await self.bus.introspect(NM_SERVICE, path)
            proxy = self.bus.get_proxy_object(NM_SERVICE, path, obj)
            props = proxy.get_interface("org.freedesktop.DBus.Properties")
            val = await props.call_get(iface, prop)
            return val.value if isinstance(val, Variant) else val
        except:
            return None

    async def _get_devices(self):
        try:
            return await self.nm.call_get_devices()
        except:
            return []

    async def _get_device_type(self, dev):
        return await self._get_prop(dev, NM_DEV_IFACE, "DeviceType")

    async def _get_wifi_device(self):
        for dev in await self._get_devices():
            if await self._get_device_type(dev) == DEVICE_TYPE_WIFI:
                return dev
        return None

    async def _get_eth_device(self):
        for dev in await self._get_devices():
            if await self._get_device_type(dev) == DEVICE_TYPE_ETHERNET:
                return dev
        return None

    # --------------------------- WIFI STATUS -----------------------
    def wifi_status(self):
        return self._run(self._wifi_status())

    async def _wifi_status(self):
        wifi = {"connected": False, "ssid": None, "bssid": None, "strength": None, "frequency": None, "ip": None}
        dev = await self._get_wifi_device()
        if not dev: return wifi

        active = await self._get_prop(dev, NM_DEV_IFACE, "ActiveConnection")
        if active and active != "/": wifi["connected"] = True

        ip4 = await self._get_prop(dev, NM_DEV_IFACE, "Ip4Config")
        if ip4 and ip4 != "/": wifi["ip"] = await self._extract_ip4(ip4)

        ap = await self._get_prop(dev, NM_WIRELESS_IFACE, "ActiveAccessPoint")
        if ap and ap != "/": wifi.update(await self._read_ap(ap))

        return wifi

    # --------------------------- ETHERNET STATUS -------------------
    def ethernet_status(self):
        return self._run(self._ethernet_status())

    async def _ethernet_status(self):
        eth = {"connected": False, "ip": None}
        dev = await self._get_eth_device()
        if not dev: return eth

        active = await self._get_prop(dev, NM_DEV_IFACE, "ActiveConnection")
        if active and active != "/": eth["connected"] = True

        ip4 = await self._get_prop(dev, NM_DEV_IFACE, "Ip4Config")
        if ip4 and ip4 != "/": eth["ip"] = await self._extract_ip4(ip4)

        return eth

    # --------------------------- WIFI SCAN -------------------------
    def scan_wifi(self):
        return self._run(self._scan_wifi())

    async def _scan_wifi(self):
        dev = await self._get_wifi_device()
        if not dev: return []

        obj = await self.bus.introspect(NM_SERVICE, dev)
        proxy = self.bus.get_proxy_object(NM_SERVICE, dev, obj)
        iface = proxy.get_interface(NM_WIRELESS_IFACE)

        try: await iface.call_request_scan({})
        except: pass

        aps = await iface.call_get_access_points()
        nets = []
        for ap in aps:
            info = await self._read_ap(ap)
            if info: nets.append(info)

        return nets

    async def _read_ap(self, ap_path):
        ssid_bytes = await self._get_prop(ap_path, NM_AP_IFACE, "Ssid")
        if not ssid_bytes: return None
        ssid = "".join(chr(b) for b in ssid_bytes)

        return {
            "ssid": ssid,
            "strength": await self._get_prop(ap_path, NM_AP_IFACE, "Strength"),
            "frequency": await self._get_prop(ap_path, NM_AP_IFACE, "Frequency"),
            "bssid": await self._get_prop(ap_path, NM_AP_IFACE, "HwAddress")
        }

    async def _extract_ip4(self, path):
        try:
            obj = await self.bus.introspect(NM_SERVICE, path)
            proxy = self.bus.get_proxy_object(NM_SERVICE, path, obj)
            props = proxy.get_interface("org.freedesktop.DBus.Properties")
            data = await props.call_get(NM_IP4_IFACE, "AddressData")
            if data.value:
                return data.value[0].get("address")
        except:
            return None
        return None
EOF

    # Write new worker
    cat > "$BACKEND_DIR/workers/network_worker.py" << 'EOF'
import threading
import time
from engine.networkmanager_dbus import NMEngine
from logger import logger

class NetworkWorker:
    def __init__(self):
        self.engine = NMEngine()
        self.running = True

    def start(self):
        thread = threading.Thread(target=self.loop, daemon=True)
        thread.start()

    def loop(self):
        while self.running:
            wifi = self.engine.wifi_status()
            eth = self.engine.ethernet_status()

            logger.log("INFO", f"Network: WIFI={wifi}, ETH={eth}")

            time.sleep(10)

EOF

    # SYSTEMD SERVICE
    log "Creating systemd backend service…"

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

    whiptail --title "Backend Installed" --msgbox "Backend installation complete." 10 60

    # Continue to install frontend (if kiosk mode selected)
    if [[ "$INSTALL_MODE" == "KIOSK" ]]; then
        install_frontend
    else
        select_network_tools
    fi
}

# ==================================================================
# INSTALL FRONTEND (STATIC HTML UI)
# ==================================================================
install_frontend() {

    log "Installing frontend into $FRONTEND_DIR ..."
    rm -rf "$FRONTEND_DIR"
    mkdir -p "$FRONTEND_DIR"

    cp -r "$FRONTEND_SRC/"* "$FRONTEND_DIR/"

    chown -R vlad:vlad "$FRONTEND_DIR"
    chmod -R 755 "$FRONTEND_DIR"

    whiptail --title "Frontend Installed" --msgbox "ADA-Pi frontend installed at:\n$FRONTEND_DIR" 10 60

    setup_kiosk_mode
}

# ==================================================================
# SETUP KIOSK MODE (CHROMIUM)
# ==================================================================
setup_kiosk_mode() {
    log "Configuring Chromium Kiosk Mode..."

    apt install -y chromium-browser xdotool unclutter lightdm

    # Ensure vlad auto-login
    log "Enabling auto-login on console for user vlad..."
    mkdir -p /etc/systemd/system/getty@tty1.service.d/
    cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf <<EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin vlad --noclear %I \$TERM
EOF

    # Create autostart directory for vlad
    sudo -u vlad mkdir -p /home/vlad/.config/autostart

    # Create kiosk launch .desktop file
    log "Creating kiosk launcher…"
    cat > /etc/xdg/autostart/ada-pi-kiosk.desktop <<EOF
[Desktop Entry]
Type=Application
Name=ADA-Pi Kiosk
Exec=chromium-browser --noerrdialogs --disable-session-crashed-bubble --incognito --kiosk http://localhost:8000
X-GNOME-Autostart-enabled=true
EOF

    chmod +x /etc/xdg/autostart/ada-pi-kiosk.desktop

    whiptail --title "Kiosk Mode Enabled" --msgbox "Kiosk Mode enabled.\nOn reboot, Chromium will open ADA-Pi in fullscreen." 12 60

    select_network_tools
}

# ==================================================================
# CLOUD/TUNNEL INSTALL MENU
# ==================================================================
select_network_tools() {

    CHOICE=$(whiptail --title "Connectivity Setup" --menu "Choose connectivity option:" 20 70 10 \
        "1" "Install Cloudflare Tunnel" \
        "2" "Install Tailscale" \
        "3" "Install Both Cloudflare & Tailscale" \
        "4" "Install None (Local Only)" \
        3>&1 1>&2 2>&3)

    case $CHOICE in
        1) install_cloudflare ;;
        2) install_tailscale ;;
        3) install_cloudflare; install_tailscale ;;
        4) connectivity_done ;;
    esac
}

# ==================================================================
# INSTALL or REUSE CLOUDflare TUNNEL
# ==================================================================
install_cloudflare() {

    # Detect existing Cloudflare installation
    CF_INSTALLED=false
    CF_TUNNEL_FOUND=false
    CF_UUID=""
    CF_HOST=""
    CF_CONFIG="/etc/cloudflared/config.yml"

    if command -v cloudflared >/dev/null 2>&1; then
        CF_INSTALLED=true
    fi

    # Detect existing tunnel credentials
    if ls /root/.cloudflared/*.json >/dev/null 2>&1; then
        CF_TUNNEL_FOUND=true
        CF_UUID=$(basename /root/.cloudflared/*.json .json)
    fi

    # Detect existing hostname inside config.yml
    if [[ -f "$CF_CONFIG" ]]; then
        CF_HOST=$(grep "hostname:" "$CF_CONFIG" | awk '{print $2}')
    fi

    # If everything already exists, offer reuse
    if $CF_INSTALLED && $CF_TUNNEL_FOUND && [[ -n "$CF_HOST" ]]; then

        CHOICE=$(whiptail --title "Cloudflare Already Installed" --menu \
        "Cloudflare Tunnel detected:\n\nTunnel ID: $CF_UUID\nHostname: $CF_HOST\n\nChoose an action:" \
        20 70 10 \
        "1" "Reuse existing Cloudflare Tunnel (recommended)" \
        "2" "Create NEW Cloudflare Tunnel (overwrite existing)" \
        "3" "Cancel" \
        3>&1 1>&2 2>&3)

        case $CHOICE in
            1)
                log "Reusing existing Cloudflare Tunnel..."
                systemctl enable cloudflared
                systemctl restart cloudflared
                whiptail --title "Cloudflare Active" \
                    --msgbox "Your existing Cloudflare Tunnel is now active.\n\n$CF_HOST" 12 60
                return
                ;;
            2)
                whiptail --title "Warning" --yesno \
                "This will DELETE your existing Cloudflare tunnel & create a new one.\n\nContinue?" \
                12 60
                if [[ $? -ne 0 ]]; then return; fi

                rm -rf /etc/cloudflared
                rm -rf /root/.cloudflared
                rm -f /usr/bin/cloudflared
                rm -f /etc/systemd/system/cloudflared.service
                ;;
            3)
                return
                ;;
        esac

    fi

    # ==================================================================
    # INSTALL NEW CLOUDFLARE — CLEAN INSTALL
    # ==================================================================

    whiptail --title "Cloudflare Tunnel" --msgbox \
    "Cloudflare will now be installed.\n\nYou will be asked to authenticate.\nYou do NOT need to change nameservers." \
    12 60

    # Install Cloudflare signing key + repo
    curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg \
        | tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null

    echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] \
https://pkg.cloudflare.com/cloudflared bookworm main" \
        | tee /etc/apt/sources.list.d/cloudflared.list

    apt update
    apt install -y cloudflared

    # Ask user for hostname
    HOSTNAME=$(whiptail --inputbox "Enter Cloudflare hostname (must end with .$DOMAIN):" 12 60 "" \
        3>&1 1>&2 2>&3)

    if [[ "$HOSTNAME" != *".$DOMAIN" ]]; then
        whiptail --title "Error" --msgbox "Hostname must end with .$DOMAIN" 10 60
        return
    fi

    # Login
    log "Authenticating Cloudflare..."
    cloudflared tunnel login

    # Create tunnel
    log "Creating tunnel..."
    cloudflared tunnel create "$HOSTNAME"

    UUID=$(cloudflared tunnel list | grep "$HOSTNAME" | awk '{print $1}')

    mkdir -p /etc/cloudflared
    cat > "$CF_CONFIG" <<EOF
tunnel: $UUID
credentials-file: /root/.cloudflared/${UUID}.json

ingress:
  - hostname: $HOSTNAME
    service: http://localhost:8000
  - service: http_status:404
EOF

    # systemd service
    cat > /etc/systemd/system/cloudflared.service <<EOF
[Unit]
Description=Cloudflare Tunnel
After=network.target

[Service]
ExecStart=/usr/bin/cloudflared --no-autoupdate --config /etc/cloudflared/config.yml tunnel run
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable cloudflared
    systemctl restart cloudflared

    whiptail --title "Cloudflare Ready" --msgbox \
    "New Cloudflare Tunnel created.\n\nURL: https://$HOSTNAME" \
    12 60
}

# ==================================================================
# INSTALL TAILSCALE
# ==================================================================
install_tailscale() {

    whiptail --title "Tailscale" --msgbox "Tailscale will now be installed.\nYou will be asked to authenticate." 12 60

    curl -fsSL https://tailscale.com/install.sh | sh

    systemctl enable --now tailscaled

    tailscale up

    IP=$(tailscale ip -4 2>/dev/null)

    whiptail --title "Tailscale Installed" --msgbox "Tailscale is active.\nDevice IP: $IP" 12 60
}

# ==================================================================
# CONNECTIVITY DONE
# ==================================================================
connectivity_done() {
    whiptail --title "Install Complete" --msgbox "Connectivity setup finished.\nProceeding to final system configuration…" 12 60
    enable_interfaces
    final_summary
}

# ==================================================================
# SYSTEM CONFIGURATION (Enable I2C / SPI / UART)
# ==================================================================
system_config() {

    log "Configuring Raspberry Pi system..."

    raspi-config nonint do_i2c 0
    raspi-config nonint do_spi 0

    # Enable UART, but disable login shell on serial
    raspi-config nonint do_serial 1
    raspi-config nonint do_serial_hw 0

    REBOOT_REQUIRED=1

    whiptail --title "System Configured" --msgbox \
    "Hardware interfaces enabled:\n\n ✔ I2C\n ✔ SPI\n ✔ UART\n\nThe system will need a reboot after installation." \
    14 60
}

# ==================================================================
# FINAL SUMMARY
# ==================================================================
final_summary() {

    SUMMARY="Installation completed.\n\nMode: $INSTALL_MODE\n"

    if systemctl is-active --quiet cloudflared; then
        SUMMARY+="Cloudflare: Installed\n"
    else
        SUMMARY+="Cloudflare: Not installed\n"
    fi

    if systemctl is-active --quiet tailscaled; then
        SUMMARY+="Tailscale: Installed\n"
    else
        SUMMARY+="Tailscale: Not installed\n"
    fi

    SUMMARY+="\nBackend directory:\n  $BACKEND_DIR\n\n"

    if [[ "$INSTALL_MODE" == "KIOSK" ]]; then
        SUMMARY+="Frontend directory:\n  $FRONTEND_DIR\n\n"
        SUMMARY+="Kiosk Mode: Enabled\n"
    else
        SUMMARY+="Kiosk Mode: Disabled\n"
    fi

    whiptail --title "ADA-Pi Installation Complete" --msgbox "$SUMMARY" 20 70

    if [[ $REBOOT_REQUIRED -eq 1 ]]; then
        if whiptail --title "Reboot Required" --yesno "Hardware interfaces changed.\nReboot now?" 12 60; then
            reboot
        fi
    fi
}

# ==================================================================
# MAIN INSTALL WORKFLOW
# ==================================================================
install_backend_full() {

    whiptail --title "Confirm Installation" --yesno \
    "Install ADA-Pi in $INSTALL_MODE mode?\n\nBackend will be installed to:\n  $BACKEND_DIR\n\nFrontend (kiosk only) to:\n  $FRONTEND_DIR\n\nContinue?" \
    15 65

    if [[ $? -ne 0 ]]; then
        return
    fi

    # CLEAN OLD INSTALL FIRST
    log "Cleaning previous ADA-Pi installation..."
    rm -rf "$INSTALL_DIR"
    rm -rf "$FRONTEND_DIR"

    # CREATE DIRECTORIES
    mkdir -p "$BACKEND_DIR"

    # =============================================================
    # INSTALL BACKEND PYTHON ENVIRONMENT
    # =============================================================
    log "Installing backend..."
    apt update
    apt install -y python3-venv python3-dev python3-pip \
        python3-dbus dbus-user-session libdbus-1-dev i2c-tools

    python3 -m venv "$BACKEND_DIR/venv"
    source "$BACKEND_DIR/venv/bin/activate"

    pip install --upgrade pip wheel setuptools

    # Install required backend modules (dbus-next, smbus2, etc)
    pip install flask flask-cors requests pyserial python-dotenv psutil websocket-client
    pip install smbus2
    pip install dbus-next

    deactivate

    # =============================================================
    # COPY BACKEND FILES
    # =============================================================
    log "Copying backend source files..."
    cp -r "$BACKEND_SRC/"* "$BACKEND_DIR/"
    chown -R root:root "$BACKEND_DIR"

    # =============================================================
    # INSTALL BACKEND SERVICE
    # =============================================================
    log "Creating systemd service..."
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

    # =============================================================
    # FRONTEND (ONLY IN KIOSK MODE)
    # =============================================================
    if [[ "$INSTALL_MODE" == "KIOSK" ]]; then
        install_frontend
    else
        select_network_tools
    fi

    # system_config will be called after connectivity
}

# ==================================================================
# ROUTING LOGIC AFTER FRONTEND / BACKEND INSTALL
# ==================================================================
# This function ensures the correct order:
#   1. Backend install
#   2. (Optional) Kiosk frontend install
#   3. Cloudflare / Tailscale selection
#   4. System configuration
#   5. Final summary

post_install_routing() {

    # STEP 1 — Backend already installed in install_backend_full

    # STEP 2 — Install frontend only in kiosk mode
    if [[ "$INSTALL_MODE" == "KIOSK" ]]; then
        install_frontend
    fi

    # STEP 3 — Select Cloudflare / Tailscale / Both / None
    select_network_tools

    # STEP 4 — Enable Interfaces
    system_config

    # STEP 5 — Show final message
    final_summary
}

