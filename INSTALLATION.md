# ADA-Pi System - Complete Installation Guide

**Vehicle Telematics System with Web Dashboard**

---

## What You Get

- **Backend Engine**: Python-based system managing all vehicle sensors and data
- **Web Dashboard**: Modern responsive interface accessible from any browser
- **REST API**: Port 8000 - HTTP endpoints for all modules
- **WebSocket Server**: Port 9000 - Real-time data streaming
- **Remote Access**: Works over LTE with Tailscale VPN

---

## Quick Start (5 Minutes)

```bash
# 1. Extract files
cd ~
unzip ada-pi-complete.zip
cd ada-pi-complete

# 2. Install dependencies
sudo apt update
sudo apt install -y python3-pip

# 3. Install Python packages
cd backend
sudo pip3 install -r requirements.txt --break-system-packages

# 4. Start the system
sudo python3 main.py
```

**Access the dashboard:**
- Open browser: `http://raspberry-pi-ip:8000`
- Default view: Dashboard with live data

---

## Full Installation (Production)

### Step 1: System Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y \
    python3 \
    python3-pip \
    git \
    i2c-tools

# Enable I2C (for UPS)
sudo raspi-config
# → Interface Options → I2C → Enable
```

### Step 2: Install ADA-Pi

```bash
# Create installation directory
sudo mkdir -p /opt/ada-pi
cd /opt/ada-pi

# Extract files
sudo unzip /path/to/ada-pi-complete.zip
sudo mv ada-pi-complete/* .
sudo rmdir ada-pi-complete

# Install Python dependencies
cd /opt/ada-pi/backend
sudo pip3 install -r requirements.txt --break-system-packages
```

### Step 3: Create Systemd Service

```bash
# Create service file
sudo nano /etc/systemd/system/ada-pi.service
```

Paste this:

```ini
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
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Save and enable:

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable ada-pi
sudo systemctl start ada-pi

# Check status
sudo systemctl status ada-pi
```

### Step 4: Configure Data Storage

```bash
# Create data directories
sudo mkdir -p /var/lib/ada-pi/{logs,storage,tacho}
sudo chown -R root:root /var/lib/ada-pi

# Create default config
sudo nano /opt/ada-pi/backend/config.json
```

Paste this:

```json
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
  "cloud": {
    "enabled": false,
    "url": ""
  }
}
```

---

## Remote Access Setup (LTE Connection)

Since your Pi will be in a vehicle with LTE, you need remote access.

### Option 1: Tailscale (RECOMMENDED)

**Easiest and most secure way to access your Pi remotely**

```bash
# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# Connect to your Tailscale network
sudo tailscale up

# Get your Pi's Tailscale IP
tailscale ip -4
```

**Result:** Access dashboard from anywhere at `http://100.x.x.x:8000`

**On your phone/laptop:**
1. Install Tailscale app
2. Login to same account
3. Access Pi: `http://100.x.x.x:8000`

### Option 2: Cloud Relay Server

Set up a VPS that Pi connects to, you access the VPS.

```bash
# On your VPS
ssh -R 8080:localhost:8000 user@your-vps.com -N

# Access: http://your-vps.com:8080
```

### Option 3: Dynamic DNS

If your LTE provider gives you a public IP:

```bash
# Install ddclient
sudo apt install ddclient

# Configure with your DDNS provider
```

---

## Testing the Installation

### 1. Check Backend Status

```bash
# Service running?
sudo systemctl status ada-pi

# Check logs
sudo journalctl -u ada-pi -f

# Test API
curl http://localhost:8000/api/system/info
```

### 2. Check WebSocket

```bash
# Install wscat
npm install -g wscat

# Test WebSocket
wscat -c ws://localhost:9000
```

### 3. Access Web Dashboard

Open browser:
- Local: `http://localhost:8000`
- Network: `http://pi-ip:8000`
- Tailscale: `http://100.x.x.x:8000`

You should see the modern dashboard!

---

## Configuration

### Change Admin Password

```bash
sudo nano /opt/ada-pi/backend/config.json
```

Change:
```json
"auth": {
  "username": "admin",
  "password": "your-secure-password"
}
```

Restart:
```bash
sudo systemctl restart ada-pi
```

### Configure GPS Port

Find your GPS device:
```bash
ls /dev/ttyUSB*
ls /dev/ttyACM*
```

Update config:
```json
"gps": {
  "port": "/dev/ttyUSB1"
}
```

### Configure Modem APN

```json
"modem": {
  "apn": "your-carrier-apn",
  "username": "",
  "password": ""
}
```

---

## File Locations

```
/opt/ada-pi/
├── backend/               # Python backend
│   ├── main.py           # Entry point
│   ├── config.json       # Configuration
│   ├── api/              # REST API
│   ├── modules/          # Hardware modules
│   └── workers/          # Background workers
├── frontend/             # Web dashboard
│   ├── index.html        # Main page
│   ├── css/              # Stylesheets
│   └── js/               # JavaScript

/var/lib/ada-pi/
├── logs/                 # System logs
├── storage/              # Data storage
└── tacho/                # Tachograph files
```

---

## Troubleshooting

### Backend Won't Start

```bash
# Check logs
sudo journalctl -u ada-pi -n 50

# Common issues:
# - Missing dependencies: reinstall requirements.txt
# - Permission errors: check /var/lib/ada-pi ownership
# - Port conflict: check if 8000/9000 already in use
```

### Can't Access Dashboard

```bash
# Check if backend is running
sudo systemctl status ada-pi

# Check if ports are listening
sudo netstat -tlnp | grep -E '(8000|9000)'

# Test locally first
curl http://localhost:8000

# Check firewall
sudo ufw status
sudo ufw allow 8000
sudo ufw allow 9000
```

### WebSocket Not Connecting

```bash
# Check WebSocket server
wscat -c ws://localhost:9000

# Check browser console (F12) for errors
# Common: Mixed content (HTTP page loading WS)
```

### GPS Not Working

```bash
# Check device exists
ls -la /dev/ttyUSB*

# Check permissions
sudo usermod -a -G dialout root

# Test GPS directly
cat /dev/ttyUSB1
```

### UPS Not Detected

```bash
# Check I2C enabled
sudo raspi-config

# Check I2C devices
sudo i2cdetect -y 1

# Should show device at 0x36
```

---

## Mobile Access

### On Your Phone

1. Install Tailscale app
2. Login
3. Open browser: `http://100.x.x.x:8000`
4. Dashboard works on mobile!

**Pro tip:** Add to home screen for app-like experience:
- Chrome: Menu → Add to Home Screen
- Safari: Share → Add to Home Screen

---

## Updating ADA-Pi

```bash
# Stop service
sudo systemctl stop ada-pi

# Backup config
sudo cp /opt/ada-pi/backend/config.json ~/config.json.backup

# Extract new version
sudo unzip ada-pi-complete-new.zip
sudo cp -r ada-pi-complete/* /opt/ada-pi/

# Restore config
sudo cp ~/config.json.backup /opt/ada-pi/backend/config.json

# Restart
sudo systemctl start ada-pi
```

---

## Performance Tips

### Reduce Logging

Edit `backend/logger.py`:
```python
LOG_LEVEL = "WARNING"  # Instead of "INFO"
```

### Optimize for Raspberry Pi Zero

```bash
# Disable unused modules in config.json
"bluetooth": { "enabled": false },
"obd": { "enabled": false }
```

### SD Card Optimization

```bash
# Move logs to RAM
sudo nano /etc/fstab
# Add:
tmpfs /var/lib/ada-pi/logs tmpfs defaults,noatime,size=50M 0 0
```

---

## Support

**Check logs:**
```bash
sudo journalctl -u ada-pi -f
```

**API documentation:**
All endpoints: `http://your-pi:8000/api/`

**Dashboard features:**
- 📊 Dashboard: Overview
- 🗺️ GPS: Real-time tracking  
- 🚗 OBD: Vehicle diagnostics
- 💻 System: Pi resources
- 🔋 UPS: Battery status
- 🌐 Network: Connectivity
- 📡 Modem: LTE status

---

## Security Notes

**IMPORTANT:**
1. **Change default password** immediately
2. **Use Tailscale** for remote access (encrypted)
3. **Don't expose port 8000** directly to internet
4. **Keep system updated**: `sudo apt update && sudo apt upgrade`

---

## Next Steps

1. ✅ Install and test locally
2. ✅ Configure your hardware (GPS, UPS, etc.)
3. ✅ Set up Tailscale for remote access
4. ✅ Install in vehicle
5. ✅ Access dashboard from anywhere!

**Enjoy your ADA-Pi system! 🚗💨**
