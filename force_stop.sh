#!/bin/bash
# Force stop script for home temperature control application
# This script finds and kills any Python processes running the application

# Color formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Home Temperature Control System Force Stop ===${NC}"

# Check for running application processes
echo "Looking for application processes..."

# Look for specific Python scripts
APP_SCRIPTS=("home_topology_api.py" "home_temperature_control.py")
FOUND=0

for script in "${APP_SCRIPTS[@]}"; do
    echo -e "Searching for processes running ${YELLOW}$script${NC}..."
    
    # Find process IDs (works on macOS and Linux)
    if [[ "$OSTYPE" == "darwin"* || "$OSTYPE" == "linux-gnu"* ]]; then
        PIDS=$(ps aux | grep "python.*$script" | grep -v grep | awk '{print $2}')
    else
        echo -e "${RED}Unsupported OS type: $OSTYPE${NC}"
        echo "Please manually kill the Python process running the home temperature control application."
        exit 1
    fi
    
    # Kill each process found
    if [ ! -z "$PIDS" ]; then
        for PID in $PIDS; do
            FOUND=1
            echo -e "Found process: ${GREEN}$PID${NC} running $script"
            
            # Try SIGTERM first
            echo -e "Sending ${YELLOW}SIGTERM${NC} to process $PID..."
            kill $PID 2>/dev/null
            
            # Wait a moment and check if process is still running
            sleep 2
            if ps -p $PID > /dev/null 2>&1; then
                echo -e "Process $PID ${RED}did not terminate${NC} with SIGTERM, trying SIGKILL..."
                kill -9 $PID 2>/dev/null
                
                # Check if SIGKILL worked
                sleep 1
                if ps -p $PID > /dev/null 2>&1; then
                    echo -e "${RED}Failed to kill process $PID. You may need to kill it manually.${NC}"
                else
                    echo -e "Process $PID ${GREEN}successfully terminated${NC} with SIGKILL."
                fi
            else
                echo -e "Process $PID ${GREEN}successfully terminated${NC} with SIGTERM."
            fi
        done
    fi
done

# Also look for any process listening on port 8000
echo -e "\nChecking for processes on default port 8000..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    PORT_PIDS=$(lsof -i :8000 -sTCP:LISTEN -t 2>/dev/null)
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PORT_PIDS=$(fuser 8000/tcp 2>/dev/null)
fi

if [ ! -z "$PORT_PIDS" ]; then
    FOUND=1
    for PID in $PORT_PIDS; do
        echo -e "Found process: ${GREEN}$PID${NC} using port 8000"
        echo -e "Sending ${YELLOW}SIGTERM${NC} to process $PID..."
        kill $PID 2>/dev/null
        
        # Wait a moment and check if process is still running
        sleep 2
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "Process $PID ${RED}did not terminate${NC} with SIGTERM, trying SIGKILL..."
            kill -9 $PID 2>/dev/null
            
            # Check if SIGKILL worked
            sleep 1
            if ps -p $PID > /dev/null 2>&1; then
                echo -e "${RED}Failed to kill process $PID. You may need to kill it manually.${NC}"
            else
                echo -e "Process $PID ${GREEN}successfully terminated${NC} with SIGKILL."
            fi
        else
            echo -e "Process $PID ${GREEN}successfully terminated${NC} with SIGTERM."
        fi
    done
fi

if [ $FOUND -eq 0 ]; then
    echo -e "${YELLOW}No running application processes found.${NC}"
    echo "If the application is still running, try:"
    echo "  1. Find the process ID: ps aux | grep python"
    echo "  2. Kill it manually: kill -9 <PID>"
else
    echo -e "\n${GREEN}Force stop completed.${NC}"
fi
