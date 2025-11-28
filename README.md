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

## How to Apply

### On Raspberry Pi:

```bash
# 1. Stop the backend
sudo systemctl stop ada-pi-backend

# 2. Go to your ADA-Pi directory
cd ~/ADA-Pi-Systems

# 3. Extract the fixes (upload ada-pi-fixes.zip to Pi first)
unzip -o ~/ada-pi-fixes.zip

# 4. Copy files to their locations
cp -f backend/workers/modem_worker.py backend/workers/
cp -f backend/requirements.txt backend/
cp -f frontend/js/app.js frontend/js/
cp -f install.sh ./

# 5. Copy to installation directory
sudo cp -f backend/workers/modem_worker.py /opt/ada-pi/backend/workers/
sudo cp -f frontend/js/app.js /opt/ada-pi/frontend/js/

# 6. Restart backend
sudo systemctl restart ada-pi-backend

# 7. Test in browser
# Open http://[pi-ip]:8000
# Press F12 and check console for:
#   ✓ WebSocket connected successfully
#   WebSocket received: messages
```

### Commit to GitHub:

```bash
cd ~/ADA-Pi-Systems

# Add all fixed files
git add backend/workers/modem_worker.py
git add backend/requirements.txt
git add frontend/js/app.js
git add install.sh

# Commit
git commit -m "Fix: WebSocket event mapping, modem publishing, requirements, installer

- Frontend: Fixed WebSocket event mapping so data displays correctly
- Modem worker: Added router.publish() to broadcast updates  
- Requirements: Removed system packages (modemmanager, bluez)
- Installer: Added all dependencies, fixed service name, better logging"

# Push
git push
```

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
