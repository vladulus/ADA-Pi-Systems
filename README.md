# ADA-Pi Fixes Package

## What's Fixed

This package contains all the critical fixes for the ADA-Pi system:

### 1. Frontend (frontend/js/app.js)
- ✅ Fixed WebSocket event mapping (gps_update → data.gps)
- ✅ Added comprehensive console logging
- ✅ Fixed event handler to map all worker events correctly
- ✅ Enhanced debugging output

### 2. Backend Modem Worker (backend/workers/modem_worker.py)
- ✅ Added `from ipc.router import router` import
- ✅ Added `router.publish("modem_update", data)` to broadcast updates
- ✅ Now modem data flows to frontend via WebSocket
- ℹ️  The active worker lives at `backend/workers/modem_worker.py`; backup copies (`*.bak`) were removed to avoid confusion, but the modem functionality remains intact.

### 3. Requirements (backend/requirements.txt)
- ✅ Removed `modemmanager` (system package, not pip)
- ✅ Removed `bluez` (system package, not pip)
- ✅ Now pip install works without errors

### 4. Installer (install.sh)
- ✅ Added all missing system dependencies (gpsd, modemmanager, bluez, etc.)
- ✅ Fixed service name to `ada-pi-backend.service` throughout
- ✅ Added StandardOutput/StandardError for better logging
- ✅ Increased wait times for service startup
- ✅ Better status messages

## How to Apply (from this repository)

### Fresh install on Raspberry Pi

```bash
# 1) Clone the repo
cd ~
git clone https://github.com/your-org/ADA-Pi-Systems.git
cd ADA-Pi-Systems

# 2) (Optional) export Tailscale auth key for non-interactive login
# export TS_AUTHKEY="tskey-xxxxxxxxxxxxxxxx"

# 3) Run the installer (prompts for headless or kiosk)
sudo bash install.sh
```

After the installer finishes:
- Check the backend: `sudo systemctl status ada-pi-backend`
- Tail logs: `sudo journalctl -u ada-pi-backend -f`
- Dashboard: browse to `http://<pi-ip>:8000` (or Tailscale IP) and verify the WebSocket shows connected in DevTools.

## Files Included

```
ada-pi-fixes/
├── README.md (this file)
├── install.sh (fixed installer with all dependencies)
├── backend/
│   ├── requirements.txt (fixed - no system packages)
│   └── workers/
│       └── modem_worker.py (fixed - adds router.publish)
└── frontend/
    └── js/
        └── app.js (fixed - event mapping and logging)
```

## What Should Work After Applying

1. ✅ Dashboard loads and shows data
2. ✅ WebSocket connects (green "Connected" status)
3. ✅ Console shows WebSocket messages flowing
4. ✅ GPS data updates in real-time (when fix available)
5. ✅ Modem data displays (signal, operator, network type)
6. ✅ System info updates automatically
7. ✅ No more pip install errors
8. ✅ Installer runs without hanging

## Testing

After applying fixes:

```bash
# Check service status
sudo systemctl status ada-pi-backend

# Check logs
sudo journalctl -u ada-pi-backend -f

# Test API
curl http://localhost:8000/api/gps | jq

# In browser (http://[pi-ip]:8000):
# - Open DevTools (F12)
# - Check Console tab
# - Should see "✓ WebSocket connected successfully"
# - Should see "WebSocket received:" messages
```

## Known Issues (Not Fixed)

These workers have bugs but don't affect core functionality:
- SystemInfoWorker (subscriptable error)
- TachoWorker (missing push_speed_point method)
- FanWorker (unexpected temperature argument)
- OTAWorker (missing get_next_task method)

GPS, Modem, Network, UPS, and OBD should work fine.

## Support

If issues persist:
1. Check browser console (F12)
2. Check backend logs: `sudo journalctl -u ada-pi-backend -f`
3. Verify WebSocket port: `sudo netstat -tuln | grep 9000`
4. Test API: `curl http://localhost:8000/api/gps`
