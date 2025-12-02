#!/bin/bash
# ADA-Pi Dashboard Stop Script

echo "=========================================="
echo "ADA-Pi Dashboard Shutdown"
echo "=========================================="
echo ""

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  This script requires sudo privileges"
    echo "Restarting with sudo..."
    sudo "$0" "$@"
    exit $?
fi

# Check if backend is running
if ! pgrep -f "python3.*main.py" > /dev/null; then
    echo "ℹ️  Backend is not running"
    exit 0
fi

# Show current process
echo "Current backend process:"
ps aux | grep "python3.*main.py" | grep -v grep
echo ""

# Kill the process
echo "Stopping backend..."
pkill -f "python3.*main.py"

# Wait a moment
sleep 2

# Verify it stopped
if pgrep -f "python3.*main.py" > /dev/null; then
    echo "⚠️  Process still running, forcing stop..."
    pkill -9 -f "python3.*main.py"
    sleep 1
fi

# Final check
if pgrep -f "python3.*main.py" > /dev/null; then
    echo "❌ Failed to stop backend"
    exit 1
else
    echo "✓ Backend stopped successfully"
    echo ""
fi

# Check ports
echo "Checking if ports are released..."
sleep 1

if netstat -tuln 2>/dev/null | grep -q ":8000 " || ss -tuln 2>/dev/null | grep -q ":8000 "; then
    echo "⚠️  Port 8000 still in use"
else
    echo "✓ Port 8000 released"
fi

if netstat -tuln 2>/dev/null | grep -q ":9000 " || ss -tuln 2>/dev/null | grep -q ":9000 "; then
    echo "⚠️  Port 9000 still in use"
else
    echo "✓ Port 9000 released"
fi

echo ""
echo "=========================================="
echo "Dashboard stopped"
echo "=========================================="
echo ""
echo "To start again:"
echo "  sudo bash start_dashboard.sh"
echo ""
