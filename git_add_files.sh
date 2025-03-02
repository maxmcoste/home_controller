#!/bin/bash
# Script to add all modified temperature control system files to git

# Color formatting
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Home Temperature Control System - Git Add Files ===${NC}"

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Files to add
FILES=(
  "security_utils.py"
  "config_loader.py"
  "temperature_control.py"
  "home_topology_api.py"
  "home_temperature_control.py"
  "house_topology.yaml"
  "config.yaml"
  "run_test_environment.py"
  "stop_app.py"
  "kill_app.py"
  "force_stop.sh"
  "force_stop.ps1"
)

# Check if we are in a git repository
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
  echo -e "${YELLOW}Not a git repository. Initializing git...${NC}"
  git init
  echo "# Home Temperature Control System" > README.md
  git add README.md
  git commit -m "Initial commit"
fi

# Add each file, checking for existence
for file in "${FILES[@]}"; do
  if [ -f "$file" ]; then
    echo -e "Adding file: ${GREEN}$file${NC}"
    git add "$file"
  else
    echo -e "${YELLOW}Warning: File not found: $file${NC}"
  fi
done

# Also add any new files that might have been created
echo -e "\n${BLUE}Checking for other new/modified files...${NC}"
git add -A

# Show status
echo -e "\n${BLUE}Current git status:${NC}"
git status

# Ask about committing
echo -e "\n${YELLOW}Do you want to commit these changes? (y/n)${NC}"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
  echo -e "${YELLOW}Enter commit message (or press Enter for default message):${NC}"
  read -r commit_msg
  
  if [ -z "$commit_msg" ]; then
    commit_msg="Update home temperature control system files"
  fi
  
  git commit -m "$commit_msg"
  
  # Ask about pushing
  echo -e "\n${YELLOW}Do you want to push these changes? (y/n)${NC}"
  read -r push_response
  if [[ "$push_response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo -e "${YELLOW}Enter branch name (or press Enter for 'main'):${NC}"
    read -r branch_name
    
    if [ -z "$branch_name" ]; then
      branch_name="main"
    fi
    
    git push -u origin "$branch_name"
  fi
fi

echo -e "\n${GREEN}Git operation completed!${NC}"
