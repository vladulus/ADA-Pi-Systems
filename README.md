# ADA-Pi - Vehicle Telematics System

**Modern web-based dashboard for Raspberry Pi vehicle telematics**

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.9+-green)
![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi-red)

---

## ✨ Features

### 📊 Real-Time Dashboard
- Live vehicle data streaming via WebSocket
- Modern, responsive web interface
- Works on desktop, tablet, and mobile
- Dark theme optimized for night driving

### 🚗 Vehicle Data
- **GPS Tracking**: Speed, position, satellites
- **OBD-II**: Engine RPM, speed, coolant temp, throttle
- **Tachograph**: Driver hours tracking (EU compliance)
- **CAN Bus**: Vehicle network data

### 🔧 System Monitoring
- **Raspberry Pi**: CPU, memory, disk, temperature
- **UPS**: Battery level, voltage, charging status
- **Network**: Ethernet/Wi-Fi status, data usage
- **LTE Modem**: Signal strength, operator, data connection

### 🌐 Remote Access
- Access from anywhere via Tailscale VPN
- Works over LTE in moving vehicles
- Secure encrypted connections
- Mobile-friendly interface

---

## 🚀 Quick Start

### 1. Flash Raspberry Pi OS

Download and flash [Raspberry Pi OS Lite](https://www.raspberrypi.com/software/)

### 2. Install ADA-Pi

```bash
# Extract files
unzip ada-pi-complete.zip
cd ada-pi-complete

# Copy to /opt
sudo cp -r . /opt/ada-pi

# Install dependencies
cd /opt/ada-pi/backend
sudo pip3 install -r requirements.txt --break-system-packages

# Start system
sudo python3 main.py
```

### 3. Access Dashboard

Open browser: **http://raspberry-pi-ip:8000**

That's it! 🎉

---

## 📱 Remote Access (For Vehicle Use)

Since the Pi will be in a car with LTE, install Tailscale:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Now access from anywhere: **http://100.x.x.x:8000**

---

## 📖 Documentation

- **[Installation Guide](INSTALLATION.md)** - Complete setup instructions
- **[API Documentation](#api-endpoints)** - REST API reference
- **[Configuration](#configuration)** - System settings

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│         Web Browser (Any Device)        │
│    http://tailscale-ip:8000             │
└──────────────┬──────────────────────────┘
               │
               ├─── HTTP (REST API)
               └─── WebSocket (Live Data)
               │
┌──────────────▼──────────────────────────┐
│       Raspberry Pi (In Vehicle)         │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │   ADA-Pi Backend Engine            │ │
│  │   - REST API (Port 8000)           │ │
│  │   - WebSocket (Port 9000)          │ │
│  │   - Data Processing                │ │
│  └────────────────────────────────────┘ │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │   Hardware Modules                 │ │
│  │   - GPS (USB/UART)                 │ │
│  │   - UPS (I2C)                      │ │
│  │   - OBD-II (ELM327)                │ │
│  │   - LTE Modem (USB)                │ │
│  │   - CAN Bus (SPI)                  │ │
│  └────────────────────────────────────┘ │
└──────────────────────────────────────────┘
```

---

## 🔌 Hardware Requirements

### Minimum
- Raspberry Pi 3B+ or newer
- 8GB+ SD card
- 5V 2.5A+ power supply
- LTE USB modem (for remote access)

### Optional
- GPS module (USB or UART)
- UPS/Battery HAT (I2C)
- ELM327 OBD-II adapter
- CAN Bus HAT
- Tachograph smart card reader

### Tested Hardware
- ✅ Raspberry Pi 4B
- ✅ Raspberry Pi 3B+
- ✅ Geekworm X1202 UPS
- ✅ u-blox NEO-6M GPS
- ✅ Quectel EC25 LTE Modem
- ✅ ELM327 Bluetooth OBD

---

## 📡 API Endpoints

### System
- `GET /api/system/info` - CPU, memory, disk, temperature
- `GET /api/system/reboot` - Reboot system

### GPS
- `GET /api/gps` - Current position, speed, satellites

### OBD
- `GET /api/obd` - Engine data (RPM, speed, temp, etc.)
- `POST /api/obd/connect` - Connect to vehicle

### UPS
- `GET /api/ups` - Battery level, voltage, charging

### Network
- `GET /api/network` - Connection status, IP, interfaces

### Modem
- `GET /api/modem` - Signal, operator, connection

### Logs
- `GET /api/logs/recent?limit=100` - Recent system logs

### Settings
- `GET /api/settings` - Current configuration
- `POST /api/settings` - Update configuration

---

## ⚙️ Configuration

Edit `/opt/ada-pi/backend/config.json`:

```json
{
  "device_id": "ada-pi-001",
  "auth": {
    "username": "admin",
    "password": "your-password"
  },
  "gps": {
    "port": "/dev/ttyUSB1",
    "baud": 9600
  },
  "obd": {
    "port": "/dev/rfcomm0",
    "protocol": "auto"
  },
  "modem": {
    "apn": "internet",
    "pin": ""
  },
  "cloud": {
    "enabled": false,
    "url": "https://your-server.com/api"
  }
}
```

---

## 🛠️ Development

### Project Structure

```
ada-pi-complete/
├── backend/
│   ├── main.py              # Entry point
│   ├── config.json          # Configuration
│   ├── api/
│   │   ├── server.py        # Flask REST API
│   │   └── helpers.py       # Auth, utils
│   ├── modules/
│   │   ├── gps.py           # GPS module
│   │   ├── ups.py           # UPS module
│   │   ├── obd.py           # OBD module
│   │   └── ...
│   ├── workers/
│   │   ├── gps_worker.py    # GPS background worker
│   │   └── ...
│   └── requirements.txt     # Python dependencies
│
└── frontend/
    ├── index.html           # Main page
    ├── css/
    │   └── style.css        # Modern dark theme
    └── js/
        └── app.js           # Dashboard logic
```

### Run in Development

```bash
cd /opt/ada-pi/backend
sudo python3 main.py
```

Changes to frontend files are served immediately (no rebuild needed).

---

## 🔒 Security

**Default credentials:**
- Username: `admin`
- Password: `admin`

**⚠️ CHANGE THESE IMMEDIATELY!**

```bash
sudo nano /opt/ada-pi/backend/config.json
# Update auth section
sudo systemctl restart ada-pi
```

**Best practices:**
- Use Tailscale for remote access (encrypted)
- Don't expose ports directly to internet
- Use strong passwords
- Keep system updated

---

## 📊 Dashboard Pages

### 🏠 Dashboard
Overview of all systems at a glance

### 🗺️ GPS Tracker
Real-time location, speed, and satellite data

### 🚗 OBD Diagnostics
Engine RPM, speed, coolant temp, throttle position

### 💻 System Info
Raspberry Pi CPU, memory, disk, temperature

### 🔋 UPS Monitor
Battery level, voltage, charging status

### 🌐 Network
Ethernet/Wi-Fi connectivity and data usage

### 📡 Modem
LTE signal strength, operator, connection status

### 📱 Bluetooth
Device pairing and connections

### 📈 Tachograph
Driver hours tracking (EU compliance)

### 📝 System Logs
Recent events and errors

### ⚙️ Settings
System configuration

---

## 🤝 Contributing

This is a complete working system. Feel free to:
- Add new hardware modules
- Improve the UI
- Add features
- Fix bugs

---

## 📝 License

This project is provided as-is for personal and commercial use.

---

## 🙏 Acknowledgments

Built for modern vehicle telematics with a focus on:
- Ease of installation
- Remote accessibility
- Mobile-friendly interface
- Real-time data streaming
- Professional appearance

---

## 📞 Support

**Check logs:**
```bash
sudo journalctl -u ada-pi -f
```

**Test API:**
```bash
curl http://localhost:8000/api/system/info
```

**Test WebSocket:**
```bash
wscat -c ws://localhost:9000
```

---

## 🎯 Roadmap

- [ ] Map view with route history
- [ ] Trip statistics and reporting
- [ ] Push notifications
- [ ] Mobile app (React Native)
- [ ] Cloud data sync
- [ ] Fleet management dashboard
- [ ] Driver behavior analysis
- [ ] Fuel consumption tracking

---

**Built with ❤️ for vehicle telematics**

🚗💨 Happy tracking!
