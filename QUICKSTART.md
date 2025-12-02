# ADA-Pi - Quick Start Guide

**Get your ADA-Pi dashboard running from a fresh clone.**

---

## Step-by-step install on Raspberry Pi

```bash
# 1) Clone the repo
cd ~
git clone https://github.com/your-org/ADA-Pi-Systems.git
cd ADA-Pi-Systems

# 2) (Optional) provide a Tailscale auth key for non-interactive login
# export TS_AUTHKEY="tskey-xxxxxxxxxxxxxxxx"

# 3) Run the installer (prompts for headless vs. kiosk)
sudo bash install.sh
```

What the installer does for you:
- Installs system dependencies (Python toolchain, modem/I²C/Bluetooth support, kiosk prerequisites)
- Builds the virtualenv from `backend/requirements.txt`
- Seeds `/etc/ada_pi/config.json` and runtime directories
- Enables and starts `ada-pi-backend.service` (and kiosk service when selected)
- Installs and optionally logs into Tailscale (interactive or with `TS_AUTHKEY`)

---

## Verify it’s running

```bash
# Backend service status
sudo systemctl status ada-pi-backend

# Tail the backend logs
sudo journalctl -u ada-pi-backend -f

# Check HTTP API locally
curl http://localhost:8000/api/gps
```

From another device on the same network, open:
- `http://<pi-ip>:8000` (dashboard)
- DevTools Console should show a connected WebSocket and live updates

---

## Remote access with Tailscale

If you exported `TS_AUTHKEY`, the installer logs in automatically. Otherwise:

```bash
sudo tailscale up  # interactive login

tailscale ip -4    # get the Pi's Tailscale IP
```

Then browse to `http://<tailscale-ip>:8000` from any Tailscale-connected device.

---

## Default credentials

- **Username:** `admin`
- **Password:** `admin`

Change them in `/etc/ada_pi/config.json` after installation.

---

## Useful commands

```bash
# Restart backend
sudo systemctl restart ada-pi-backend

# Restart kiosk (if enabled)
sudo systemctl restart ada-pi-kiosk
```

**Happy tracking! 🚗💨**
