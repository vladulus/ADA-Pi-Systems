# ADA-Pi Dashboard Fix Guide

## What Was Broken

ChatGPT broke the Flask static file serving configuration. The `static_folder` and `static_url_path` settings were conflicting, preventing the CSS and JavaScript files from loading properly.

## What I Fixed

1. **Removed the conflicting static configuration** from Flask initialization
2. **Added a proper `/static/<path:filename>` route** to serve CSS and JS files
3. **Fixed the path calculation** for the frontend directory to use absolute paths consistently

## How to Start the Dashboard

### Method 1: Direct Python Execution (for testing)

```bash
cd /home/pi/ADA-Pi-Systems/backend
sudo python3 main.py
```

This will start:
- REST API on port 8000
- WebSocket server on port 9000

### Method 2: Using the systemd service (if installed)

```bash
sudo systemctl start ada-pi
sudo systemctl status ada-pi
```

### Method 3: Using the installation script

```bash
cd /home/pi/ADA-Pi-Systems
sudo bash install.sh
```

## Accessing the Dashboard

1. **Open your browser** and navigate to:
   - Local: `http://192.168.1.28:8000`
   - Or use: `http://localhost:8000` (if on the Pi itself)

2. **You will see a login screen** - this is normal! The system requires authentication via your ADA Systems account at www.adasystems.uk

3. **Login with your credentials**:
   - Username or Email from your adasystems.uk account
   - Password from your adasystems.uk account

## Troubleshooting

### Dashboard won't load (404 or connection refused)

Check if the backend is running:
```bash
ps aux | grep python3 | grep main.py
```

If not running, start it manually:
```bash
cd /home/pi/ADA-Pi-Systems/backend
sudo python3 main.py
```

### CSS/JS not loading (blank page or unstyled)

Check the browser console (F12) for errors. The fix I applied should resolve this.

### Can't login (authentication error)

The system authenticates against www.adasystems.uk. Make sure:
1. You have internet connectivity
2. Your credentials are correct
3. The external API is accessible

You can check the browser console for specific error messages.

### WebSocket not connecting

Check if port 9000 is accessible:
```bash
sudo netstat -tulpn | grep 9000
```

Make sure your firewall allows connections to port 9000.

### Check Backend Logs

View live logs:
```bash
cd /home/pi/ADA-Pi-Systems/backend
sudo python3 main.py
```

Or if using systemd:
```bash
sudo journalctl -u ada-pi -f
```

## Port Information

- **Port 8000**: REST API and Web Dashboard
- **Port 9000**: WebSocket server for real-time updates

## Quick Health Check

Test if the API is responding:
```bash
curl http://192.168.1.28:8000/api/system/info
```

This should return JSON data or require authentication.

## Dependencies Check

Make sure all Python dependencies are installed:
```bash
cd /home/pi/ADA-Pi-Systems/backend
pip3 install -r requirements.txt
```

## Key Changes Made to server.py

1. **Line 31**: Removed `static_folder=frontend_dir, static_url_path='/static'` from Flask initialization
2. **Line 424-430**: Added new `/static/<path:filename>` route to properly serve static files
3. **Line 418**: Fixed frontend_dir path calculation to use absolute path

## Files Modified

- `/backend/api/server.py` - Fixed static file serving

All other files remain unchanged.

## Next Steps

1. Copy the fixed files to your Raspberry Pi at `/home/pi/ADA-Pi-Systems`
2. Restart the backend service
3. Access the dashboard at http://192.168.1.28:8000
4. Login with your ADA Systems credentials

## Important Notes

- The dashboard **requires authentication** - you must login with valid adasystems.uk credentials
- The login screen is **not an error** - it's the expected first screen
- All sensor data will only appear **after successful login**
- WebSocket connection provides real-time updates once authenticated

If you still have issues after following this guide, check:
1. Backend logs for Python errors
2. Browser console (F12) for JavaScript errors
3. Network connectivity to both the Pi and www.adasystems.uk
