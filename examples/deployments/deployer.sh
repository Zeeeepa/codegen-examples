#!/bin/bash

# Codegen Deployments - Master Deployment Script
# This script allows users to select which deployment examples to deploy

# ANSI color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Print banner
echo -e "${BLUE}"
echo "╔═════════════════════════════════════════════════════════════╗"
echo "║                                                             ║"
echo "║               Codegen Deployments - Deployer                ║"
echo "║                                                             ║"
echo "╚═════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Define available deployment types
declare -a DEPLOYMENT_TYPES=(
    "modal_deployments"
)

# Define deployment type descriptions
declare -A TYPE_DESCRIPTIONS=(
    ["modal_deployments"]="Deploy Codegen applications using Modal, a serverless compute platform"
)

# Function to display deployment types
display_deployment_types() {
    echo -e "\n${BLUE}Available deployment types:${NC}"
    for i in "${!DEPLOYMENT_TYPES[@]}"; do
        echo -e "${CYAN}[$((i+1))] ${DEPLOYMENT_TYPES[$i]}${NC} - ${TYPE_DESCRIPTIONS[${DEPLOYMENT_TYPES[$i]}]}"
    done
}

# Display deployment types
display_deployment_types

# Ask user to select a deployment type
echo -e "\n${BLUE}Select a deployment type (number):${NC}"
read -p "> " TYPE_SELECTION

# Validate selection
if ! [[ $TYPE_SELECTION =~ ^[0-9]+$ ]] || [ $TYPE_SELECTION -lt 1 ] || [ $TYPE_SELECTION -gt ${#DEPLOYMENT_TYPES[@]} ]; then
    echo -e "${RED}Invalid selection. Exiting.${NC}"
    exit 1
fi

# Get selected deployment type
SELECTED_TYPE=${DEPLOYMENT_TYPES[$((TYPE_SELECTION-1))]}

echo -e "\n${BLUE}You selected: ${CYAN}$SELECTED_TYPE${NC} - ${TYPE_DESCRIPTIONS[$SELECTED_TYPE]}"

# Check if deployer.sh exists for the selected type
DEPLOYER_PATH="$SELECTED_TYPE/deployer.sh"

if [ ! -f "$DEPLOYER_PATH" ]; then
    echo -e "${RED}Error: Deployer script not found at $DEPLOYER_PATH${NC}"
    exit 1
fi

# Make sure the script is executable
chmod +x "$DEPLOYER_PATH"

# Run the deployment script
echo -e "\n${YELLOW}Running $DEPLOYER_PATH...${NC}\n"
./"$DEPLOYER_PATH"

# Exit with the same status as the deployment script
exit $?

