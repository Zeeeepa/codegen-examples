#!/bin/bash

# Code Analysis Service Deployment Script
# This script deploys the code analysis service to Modal

# Check if required environment variables are set
if [ -z "$CODEGEN_API_TOKEN" ]; then
    echo "Error: CODEGEN_API_TOKEN environment variable is not set."
    echo "Please set it with: export CODEGEN_API_TOKEN=your_token"
    echo "Or create a .env file with CODEGEN_API_TOKEN=your_token"
    exit 1
fi

if [ -z "$MODAL_TOKEN_ID" ] || [ -z "$MODAL_TOKEN_SECRET" ]; then
    echo "Error: Modal token environment variables are not set."
    echo "Please set them with:"
    echo "export MODAL_TOKEN_ID=your_modal_token_id"
    echo "export MODAL_TOKEN_SECRET=your_modal_token_secret"
    echo "Or create a .env file with these variables."
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed."
    exit 1
fi

# Check if required packages are installed
echo "Checking required packages..."
python3 -m pip install -q modal codegen python-dotenv

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    export $(grep -v '^#' .env | xargs)
fi

# Deploy to Modal
echo "Deploying code analysis service to Modal..."
python3 -m modal deploy app.py

# Get the deployment URL
DEPLOYMENT_URL=$(python3 -c "from modal.cli.app import get_remote_app_url; print(get_remote_app_url('code-analysis-service'))")

echo ""
echo "Deployment successful!"
echo "Your code analysis service is now available at:"
echo "$DEPLOYMENT_URL/analyze"
echo ""
echo "Example usage:"
echo "curl -X POST $DEPLOYMENT_URL/analyze \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"repo_url\": \"https://github.com/username/repo\", \"analysis_type\": \"full\"}'"
echo ""
echo "For more information, see the README.md file."

