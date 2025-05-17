#!/bin/bash

# Codegen Modal Deployments - Master Deployment Script
# This script allows users to select which examples to deploy

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
echo "║             Codegen Modal Deployments - Deployer            ║"
echo "║                                                             ║"
echo "╚═════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if required environment variables are set
echo -e "${YELLOW}Checking environment setup...${NC}"

MISSING_VARS=0

if [ -z "$CODEGEN_API_TOKEN" ]; then
    echo -e "${RED}✗ CODEGEN_API_TOKEN is not set${NC}"
    MISSING_VARS=1
else
    echo -e "${GREEN}✓ CODEGEN_API_TOKEN is set${NC}"
fi

if [ -z "$MODAL_TOKEN_ID" ] || [ -z "$MODAL_TOKEN_SECRET" ]; then
    echo -e "${RED}✗ Modal token environment variables are not set${NC}"
    MISSING_VARS=1
else
    echo -e "${GREEN}✓ Modal token environment variables are set${NC}"
fi

if [ $MISSING_VARS -eq 1 ]; then
    echo -e "\n${RED}Error: Some required environment variables are missing.${NC}"
    echo "Please set them with:"
    echo "export CODEGEN_API_TOKEN=your_codegen_token"
    echo "export MODAL_TOKEN_ID=your_modal_token_id"
    echo "export MODAL_TOKEN_SECRET=your_modal_token_secret"
    echo "Or create a .env file with these variables."
    
    # Ask if user wants to continue anyway
    read -p "Do you want to continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed.${NC}"
    exit 1
fi

# Check if required packages are installed
echo -e "\n${YELLOW}Checking required packages...${NC}"
python3 -m pip install -q modal codegen python-dotenv

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    echo -e "${GREEN}Loading environment variables from .env file...${NC}"
    export $(grep -v '^#' .env | xargs)
fi

# Define available examples
declare -a EXAMPLES=(
    "code_analysis_service"
    "pr_review_bot"
    "slack_chatbot"
)

# Define example descriptions
declare -A DESCRIPTIONS=(
    ["code_analysis_service"]="A web service that analyzes GitHub repositories"
    ["pr_review_bot"]="A bot that automatically reviews pull requests"
    ["slack_chatbot"]="A Slack bot powered by Codegen"
)

# Define example requirements
declare -A REQUIREMENTS=(
    ["code_analysis_service"]="CODEGEN_API_TOKEN, MODAL_TOKEN_ID, MODAL_TOKEN_SECRET"
    ["pr_review_bot"]="CODEGEN_API_TOKEN, MODAL_TOKEN_ID, MODAL_TOKEN_SECRET, GITHUB_TOKEN or GITHUB_APP_*"
    ["slack_chatbot"]="CODEGEN_API_TOKEN, MODAL_TOKEN_ID, MODAL_TOKEN_SECRET, SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET"
)

# Function to display examples
display_examples() {
    echo -e "\n${BLUE}Available examples:${NC}"
    for i in "${!EXAMPLES[@]}"; do
        echo -e "${CYAN}[$((i+1))] ${EXAMPLES[$i]}${NC} - ${DESCRIPTIONS[${EXAMPLES[$i]}]}"
        echo -e "    ${YELLOW}Requirements:${NC} ${REQUIREMENTS[${EXAMPLES[$i]}]}"
    done
}

# Display examples
display_examples

# Ask user to select examples
echo -e "\n${BLUE}Select examples to deploy (comma-separated list, e.g., 1,3):${NC}"
read -p "> " SELECTION

# Parse selection
IFS=',' read -ra SELECTED <<< "$SELECTION"
SELECTED_EXAMPLES=()

for sel in "${SELECTED[@]}"; do
    # Remove leading/trailing whitespace
    sel=$(echo $sel | xargs)
    
    # Check if selection is valid
    if [[ $sel =~ ^[0-9]+$ ]] && [ $sel -ge 1 ] && [ $sel -le ${#EXAMPLES[@]} ]; then
        SELECTED_EXAMPLES+=(${EXAMPLES[$((sel-1))]})
    else
        echo -e "${RED}Invalid selection: $sel${NC}"
    fi
done

# Check if any examples were selected
if [ ${#SELECTED_EXAMPLES[@]} -eq 0 ]; then
    echo -e "${RED}No valid examples selected. Exiting.${NC}"
    exit 1
fi

# Confirm selection
echo -e "\n${BLUE}You selected the following examples:${NC}"
for example in "${SELECTED_EXAMPLES[@]}"; do
    echo -e "${CYAN}* $example${NC} - ${DESCRIPTIONS[$example]}"
done

read -p "Do you want to deploy these examples? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Deployment cancelled.${NC}"
    exit 0
fi

# Deploy selected examples
echo -e "\n${BLUE}Deploying selected examples...${NC}"

# Function to deploy an example
deploy_example() {
    local example=$1
    echo -e "\n${PURPLE}Deploying $example...${NC}"
    
    # Check if deploy.sh exists
    if [ -f "$example/deploy.sh" ]; then
        # Make sure the script is executable
        chmod +x "$example/deploy.sh"
        
        # Run the deployment script
        (cd "$example" && ./deploy.sh)
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ $example deployed successfully${NC}"
            return 0
        else
            echo -e "${RED}✗ Failed to deploy $example${NC}"
            return 1
        fi
    else
        echo -e "${RED}✗ Deployment script not found for $example${NC}"
        return 1
    fi
}

# Track successful and failed deployments
SUCCESSFUL=()
FAILED=()

# Deploy examples concurrently if requested
read -p "Do you want to deploy examples concurrently? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Deploying examples concurrently...${NC}"
    
    # Start all deployments in the background
    for example in "${SELECTED_EXAMPLES[@]}"; do
        deploy_example "$example" &
    done
    
    # Wait for all deployments to finish
    wait
else
    echo -e "${YELLOW}Deploying examples sequentially...${NC}"
    
    # Deploy examples one by one
    for example in "${SELECTED_EXAMPLES[@]}"; do
        if deploy_example "$example"; then
            SUCCESSFUL+=("$example")
        else
            FAILED+=("$example")
        fi
    done
fi

# Print summary
echo -e "\n${BLUE}Deployment Summary:${NC}"

if [ ${#SUCCESSFUL[@]} -gt 0 ]; then
    echo -e "${GREEN}Successfully deployed:${NC}"
    for example in "${SUCCESSFUL[@]}"; do
        echo -e "${GREEN}✓ $example${NC}"
    done
fi

if [ ${#FAILED[@]} -gt 0 ]; then
    echo -e "${RED}Failed to deploy:${NC}"
    for example in "${FAILED[@]}"; do
        echo -e "${RED}✗ $example${NC}"
    done
fi

echo -e "\n${BLUE}Deployment complete!${NC}"
echo -e "${YELLOW}You can monitor your deployments in the Modal dashboard: https://modal.com/apps${NC}"

