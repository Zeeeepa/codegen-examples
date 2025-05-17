#!/bin/bash

# Deployer.sh - Interactive script to deploy Modal examples
# This script allows you to select and deploy multiple Modal examples concurrently

# Colors for better readability
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check if Modal CLI is installed
check_modal_cli() {
    if ! command -v modal &> /dev/null; then
        echo -e "${RED}Error: Modal CLI is not installed.${NC}"
        echo -e "Please install it with: ${YELLOW}pip install modal${NC}"
        exit 1
    fi
}

# Function to check if Modal is authenticated
check_modal_auth() {
    if ! modal token list &> /dev/null; then
        echo -e "${RED}Error: Not authenticated with Modal.${NC}"
        echo -e "Please run: ${YELLOW}modal token new${NC}"
        exit 1
    fi
}

# Function to find all examples with deploy.sh scripts
find_examples() {
    find "$(dirname "$0")" -name "deploy.sh" -not -path "$(dirname "$0")/Deployer.sh" | sort
}

# Function to deploy examples concurrently
deploy_examples() {
    local examples=("$@")
    local pids=()
    local results=()
    
    echo -e "${BLUE}Starting deployment of ${#examples[@]} examples...${NC}"
    
    # Start all deployments in the background
    for example in "${examples[@]}"; do
        local example_dir=$(dirname "$example")
        local example_name=$(basename "$example_dir")
        
        echo -e "${YELLOW}Deploying ${example_name}...${NC}"
        
        # Change to the example directory and run deploy.sh
        (cd "$example_dir" && ./deploy.sh > /tmp/deploy_${example_name}.log 2>&1)&
        
        # Store the PID and example name
        pids+=($!)
        results+=("$example_name")
    done
    
    # Wait for all deployments to finish
    for i in "${!pids[@]}"; do
        if wait "${pids[$i]}"; then
            echo -e "${GREEN}✓ ${results[$i]} deployed successfully${NC}"
        else
            echo -e "${RED}✗ ${results[$i]} deployment failed${NC}"
            echo -e "${YELLOW}See log at /tmp/deploy_${results[$i]}.log${NC}"
        fi
    done
    
    echo -e "${BLUE}All deployments completed.${NC}"
}

# Main function
main() {
    # Check if Modal CLI is installed and authenticated
    check_modal_cli
    check_modal_auth
    
    # Find all examples with deploy.sh scripts
    examples=($(find_examples))
    
    if [ ${#examples[@]} -eq 0 ]; then
        echo -e "${RED}No examples with deploy.sh scripts found.${NC}"
        exit 1
    fi
    
    # Display the list of available examples
    echo -e "${BLUE}Available examples:${NC}"
    for i in "${!examples[@]}"; do
        local example_dir=$(dirname "${examples[$i]}")
        local example_name=$(basename "$example_dir")
        echo -e "${YELLOW}$((i+1)).${NC} $example_name"
    done
    
    # Prompt for selection
    echo -e "${BLUE}Enter the numbers of the examples you want to deploy (space-separated), or 'all' for all examples:${NC}"
    read -r selection
    
    selected_examples=()
    
    if [ "$selection" == "all" ]; then
        selected_examples=("${examples[@]}")
    else
        # Parse the selection
        for num in $selection; do
            if [[ "$num" =~ ^[0-9]+$ ]] && [ "$num" -ge 1 ] && [ "$num" -le "${#examples[@]}" ]; then
                selected_examples+=("${examples[$((num-1))]}")
            else
                echo -e "${RED}Invalid selection: $num${NC}"
            fi
        done
    fi
    
    if [ ${#selected_examples[@]} -eq 0 ]; then
        echo -e "${RED}No valid examples selected.${NC}"
        exit 1
    fi
    
    # Confirm the selection
    echo -e "${BLUE}You selected the following examples:${NC}"
    for example in "${selected_examples[@]}"; do
        local example_dir=$(dirname "$example")
        local example_name=$(basename "$example_dir")
        echo -e "${YELLOW}•${NC} $example_name"
    done
    
    echo -e "${BLUE}Do you want to deploy these examples? (y/n)${NC}"
    read -r confirm
    
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo -e "${RED}Deployment cancelled.${NC}"
        exit 0
    fi
    
    # Deploy the selected examples
    deploy_examples "${selected_examples[@]}"
}

# Run the main function
main

