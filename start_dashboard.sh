#!/bin/bash
# ADA-Pi Dashboard Quick Start Script

echo "=========================================="
echo "ADA-Pi Dashboard Startup"
echo "=========================================="
echo ""

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  This script requires sudo privileges"
    echo "Restarting with sudo..."
    sudo "$0" "$@"
    exit $?
fi

# Define paths
ADA_PI_DIR="/home/pi/ADA-Pi-Systems"
BACKEND_DIR="$ADA_PI_DIR/backend"
MAIN_SCRIPT="$BACKEND_DIR/main.py"

# Check if ADA-Pi directory exists
if [ ! -d "$ADA_PI_DIR" ]; then
    echo "❌ ADA-Pi directory not found at: $ADA_PI_DIR"
    echo ""
    echo "Please copy the fixed ADA-Pi-Systems directory to /home/pi/"
    exit 1
fi

# Check if main.py exists
if [ ! -f "$MAIN_SCRIPT" ]; then
    echo "❌ main.py not found at: $MAIN_SCRIPT"
    exit 1
fi

# Check if already running
if pgrep -f "python3.*main.py" > /dev/null; then
    echo "⚠️  Backend is already running!"
    echo ""
    echo "Current process:"
    ps aux | grep "python3.*main.py" | grep -v grep
    echo ""
    echo "To restart, first stop it:"
    echo "  sudo pkill -f 'python3.*main.py'"
    echo "  sudo bash start_dashboard.sh"
    echo ""
    exit 1
fi

# Check Python dependencies
echo "Checking dependencies..."
cd "$BACKEND_DIR"

MISSING_DEPS=0
for pkg in flask websockets psutil requests pyserial smbus2; do
    if ! python3 -c "import $pkg" 2>/dev/null; then
        echo "  ❌ Missing: $pkg"
        MISSING_DEPS=1
    fi
done

if [ $MISSING_DEPS -eq 1 ]; then
    echo ""
    echo "⚠️  Missing dependencies detected"
    echo "Installing dependencies..."
    pip3 install -r requirements.txt --break-system-packages
    echo ""
fi

echo "✓ Dependencies OK"
echo ""

# Start the backend
echo "Starting ADA-Pi backend..."
cd "$BACKEND_DIR"

# Run in background with output to log file
nohup python3 main.py > /tmp/ada-pi-dashboard.log 2>&1 &
PID=$!

echo "✓ Backend started with PID: $PID"
echo ""

# Wait a moment for startup
echo "Waiting for services to initialize..."
sleep 3

# Check if process is still running
if ps -p $PID > /dev/null; then
    echo "✓ Backend is running"
    echo ""
    
    # Get IP address
    LOCAL_IP=$(ip addr show | grep "inet " | grep -v "127.0.0.1" | head -1 | awk '{print $2}' | cut -d'/' -f1)
    
    echo "=========================================="
    echo "Dashboard Access Information"
    echo "=========================================="
    echo ""
    echo "✓ REST API: http://${LOCAL_IP}:8000"
    echo "✓ WebSocket: ws://${LOCAL_IP}:9000"
    echo ""
    echo "🌐 Open dashboard at:"
    echo "   http://${LOCAL_IP}:8000"
    echo ""
    echo "📋 View logs:"
    echo "   tail -f /tmp/ada-pi-dashboard.log"
    echo ""
    echo "🛑 Stop dashboard:"
    echo "   sudo pkill -f 'python3.*main.py'"
    echo ""
    echo "=========================================="
    echo ""
    echo "🔐 Login Required"
    echo "=========================================="
    echo ""
    echo "When you open the dashboard, you will see"
    echo "a login screen. This is NORMAL."
    echo ""
    echo "Login with your ADA Systems credentials:"
    echo "  • Username or Email from www.adasystems.uk"
    echo "  • Password from www.adasystems.uk"
    echo ""
    echo "=========================================="
    echo ""
else
    echo "❌ Backend failed to start!"
    echo ""
    echo "Check the log for errors:"
    echo "  cat /tmp/ada-pi-dashboard.log"
    echo ""
    exit 1
fi
