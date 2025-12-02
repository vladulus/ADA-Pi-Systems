# ADA-Pi System - Installation Guide

Vehicle telematics stack with web dashboard, REST API (8000), and WebSocket stream (9000).

---

## Recommended installation (automated)

Prerequisites:
- Raspberry Pi with internet access and sudo privileges
- Optional: `TS_AUTHKEY` environment variable for non-interactive Tailscale login

Steps:
```bash
# 1) Clone the repository
cd ~
git clone https://github.com/your-org/ADA-Pi-Systems.git
cd ADA-Pi-Systems

# 2) (Optional) export your Tailscale auth key
# export TS_AUTHKEY="tskey-xxxxxxxxxxxxxxxx"

# 3) Run the installer (prompts for headless or kiosk)
sudo bash install.sh
```

What the installer configures:
- System packages (Python toolchain, modem/I²C/Bluetooth, kiosk dependencies)
- Virtualenv with `backend/requirements.txt`
- Default config at `/etc/ada_pi/config.json` and runtime directories under `/var/lib/ada-pi`
- Systemd services: `ada-pi-backend.service` and, when selected, `ada-pi-kiosk.service`
- Tailscale install + login (interactive or via `TS_AUTHKEY`), with funnel setup when login succeeds

---

## Post-install checks

```bash
# Backend service health
sudo systemctl status ada-pi-backend

# Live logs
sudo journalctl -u ada-pi-backend -f

# HTTP API probe
curl http://localhost:8000/api/gps
```

From another device:
- Browse to `http://<pi-ip>:8000` for the dashboard
- Open DevTools → Console to confirm WebSocket connects and data flows

---

## Remote access with Tailscale

If `TS_AUTHKEY` was set, the installer logs in automatically. Otherwise:
```bash
sudo tailscale up           # interactive login
tailscale ip -4             # discover the Pi's Tailscale IP
```
Then visit `http://<tailscale-ip>:8000` from any Tailscale-connected device.

---

## Default credentials

- **Username:** `admin`
- **Password:** `admin`

Update them in `/etc/ada_pi/config.json` after installation.

---

## Manual/advanced setup (optional)

If you prefer to provision the system without `install.sh`, ensure you:
- Install base packages: `python3`, `python3-venv`, `python3-pip`, `git`, `i2c-tools`, `modemmanager`, `bluez`, `libatlas-base-dev`, `chromium-browser`, `xdotool`, `unclutter`
- Enable I²C via `sudo raspi-config` when using UPS hardware
- Create `/opt/ada-pi`, copy the repository there, and create a virtualenv with `pip install -r backend/requirements.txt`
- Create `/etc/ada_pi/config.json` and `/var/lib/ada-pi/{logs,storage,tacho}` with ownership for the service user
- Register a systemd unit pointing to `/opt/ada-pi/backend/main.py` (see `install.sh` for reference)
- Install and log into Tailscale if remote access is required

Use the automated installer whenever possible to avoid missing dependencies or permissions.
