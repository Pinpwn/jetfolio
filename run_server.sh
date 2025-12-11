#!/bin/bash
# Stock Dashboard Server Startup Script

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Stock Dashboard Server...${NC}"

# Check if we're in the right directory
if [ ! -f "backend/main.py" ]; then
    echo -e "${RED}Error: backend/main.py not found. Please run this script from the project root.${NC}"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source venv/bin/activate
fi

# Auto-install/Update dependencies
if [ -f "requirements.txt" ]; then
    echo -e "${YELLOW}Checking dependencies...${NC}"
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to install dependencies.${NC}"
        # We don't exit here strictly, or maybe we should? 
        # If pip fails (e.g. network), maybe we can try running anyway?
        # But safest is to warn.
        echo -e "${YELLOW}Attempting to start server anyway...${NC}"
    fi
fi

# Kill any existing uvicorn processes on port 8000
echo -e "${YELLOW}Checking for existing server instances...${NC}"
pkill -f "uvicorn backend.main:app" 2>/dev/null
sleep 1

# Start the server
echo -e "${GREEN}Starting server on http://127.0.0.1:8000${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

# Run uvicorn with auto-reload
python -m uvicorn backend.main:app --reload --port 8000 --host 127.0.0.1
