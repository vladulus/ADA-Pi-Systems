# ADA-Pi - Quick Start Guide

**Get your vehicle telematics dashboard running with ONE COMMAND!**

---

## Installation (ONE COMMAND!)

```bash
# Extract and run installer
unzip ada-pi-complete.zip
cd ada-pi-complete
sudo bash install.sh
```

**That's it!** The installer does EVERYTHING:
- ✅ Installs all dependencies
- ✅ Installs Python packages  
- ✅ Installs Tailscale
- ✅ Configures firewall
- ✅ Creates service
- ✅ Starts everything

**No additional steps needed!** 🎉

---

## Remote Access (2 Minutes)

Installer already installed Tailscale! Just connect:

```bash
# Connect to Tailscale
sudo tailscale up

# Get your Tailscale IP
tailscale ip -4

# Access from anywhere!
# http://100.x.x.x:8000
```

---

## What You Get

- 📊 Dashboard with system overview
- 🗺️ GPS tracking (speed, location)
- 🚗 OBD diagnostics (RPM, temp)
- 💻 System monitoring
- 🔋 Battery status
- 🌐 Network info
- Plus: Logs, Settings, and more

---

## Default Login

**Username:** `admin`  
**Password:** `admin`

⚠️ Change in: `/opt/ada-pi/backend/config.json`

---

## Useful Commands

```bash
# Status
sudo systemctl status ada-pi

# Logs
sudo journalctl -u ada-pi -f

# Restart
sudo systemctl restart ada-pi
```

---

**Happy tracking! 🚗💨**
