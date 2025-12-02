#!/bin/bash
# ADA-Pi Dashboard Health Check Script

echo "=========================================="
echo "ADA-Pi Dashboard Health Check"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if backend process is running
echo -n "Checking if backend is running... "
if pgrep -f "python3.*main.py" > /dev/null; then
    echo -e "${GREEN}✓ Running${NC}"
    BACKEND_PID=$(pgrep -f "python3.*main.py")
    echo "  PID: $BACKEND_PID"
else
    echo -e "${RED}✗ Not running${NC}"
    echo ""
    echo -e "${YELLOW}To start the backend:${NC}"
    echo "  cd /home/pi/ADA-Pi-Systems/backend"
    echo "  sudo python3 main.py"
    echo ""
    exit 1
fi

echo ""

# Check if port 8000 is listening
echo -n "Checking if port 8000 is open... "
if netstat -tuln 2>/dev/null | grep -q ":8000 " || ss -tuln 2>/dev/null | grep -q ":8000 "; then
    echo -e "${GREEN}✓ Open${NC}"
else
    echo -e "${RED}✗ Not open${NC}"
    echo "  Port 8000 should be listening for the web dashboard"
fi

# Check if port 9000 is listening
echo -n "Checking if port 9000 is open... "
if netstat -tuln 2>/dev/null | grep -q ":9000 " || ss -tuln 2>/dev/null | grep -q ":9000 "; then
    echo -e "${GREEN}✓ Open${NC}"
else
    echo -e "${RED}✗ Not open${NC}"
    echo "  Port 9000 should be listening for WebSocket connections"
fi

echo ""

# Test HTTP connectivity to dashboard
echo -n "Testing HTTP connection to dashboard... "
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ | grep -q "200"; then
    echo -e "${GREEN}✓ HTTP 200 OK${NC}"
else
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/)
    echo -e "${RED}✗ HTTP $HTTP_CODE${NC}"
fi

# Test static CSS file
echo -n "Testing CSS file... "
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/static/css/style.css | grep -q "200"; then
    echo -e "${GREEN}✓ CSS loads${NC}"
else
    echo -e "${RED}✗ CSS not loading${NC}"
fi

# Test static JS file
echo -n "Testing JS file... "
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/static/js/app.js | grep -q "200"; then
    echo -e "${GREEN}✓ JS loads${NC}"
else
    echo -e "${RED}✗ JS not loading${NC}"
fi

echo ""
echo "=========================================="
echo "Network Information"
echo "=========================================="

# Get IP addresses
echo "Local IP addresses:"
ip addr show | grep "inet " | grep -v "127.0.0.1" | awk '{print "  " $2}' | cut -d'/' -f1

echo ""
echo -e "${GREEN}Dashboard URL:${NC}"
LOCAL_IP=$(ip addr show | grep "inet " | grep -v "127.0.0.1" | head -1 | awk '{print $2}' | cut -d'/' -f1)
echo "  http://${LOCAL_IP}:8000"
echo "  http://localhost:8000 (local only)"

echo ""
echo "=========================================="
echo "Quick Diagnostics"
echo "=========================================="

# Check Python dependencies
echo -n "Checking Flask installation... "
if python3 -c "import flask" 2>/dev/null; then
    echo -e "${GREEN}✓ Installed${NC}"
else
    echo -e "${RED}✗ Not installed${NC}"
    echo "  Run: pip3 install -r /home/pi/ADA-Pi-Systems/backend/requirements.txt"
fi

echo -n "Checking websockets installation... "
if python3 -c "import websockets" 2>/dev/null; then
    echo -e "${GREEN}✓ Installed${NC}"
else
    echo -e "${RED}✗ Not installed${NC}"
    echo "  Run: pip3 install -r /home/pi/ADA-Pi-Systems/backend/requirements.txt"
fi

echo ""
echo "=========================================="
echo "Authentication Note"
echo "=========================================="
echo ""
echo "The dashboard requires login via www.adasystems.uk"
echo "If you see a login screen, this is NORMAL and expected."
echo ""
echo "Login with your ADA Systems credentials:"
echo "  - Username or Email"
echo "  - Password"
echo ""
echo "=========================================="
echo ""

# Show recent logs if backend is running
if pgrep -f "python3.*main.py" > /dev/null; then
    echo "Recent backend activity (last 10 lines of logs):"
    echo "=========================================="
    if [ -d "/home/pi/ADA-Pi-Systems/backend/storage/logs" ]; then
        LATEST_LOG=$(ls -t /home/pi/ADA-Pi-Systems/backend/storage/logs/*.txt 2>/dev/null | head -1)
        if [ -f "$LATEST_LOG" ]; then
            tail -10 "$LATEST_LOG"
        else
            echo "No log files found"
        fi
    else
        echo "Log directory not found"
    fi
    echo "=========================================="
fi

echo ""
echo -e "${GREEN}Health check complete!${NC}"
echo ""
