#!/bin/bash

# PR Review Bot Deployment Script
# This script deploys the PR review bot to Modal

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

# Check if GitHub credentials are set
if [ -z "$GITHUB_TOKEN" ] && ([ -z "$GITHUB_APP_ID" ] || [ -z "$GITHUB_APP_PRIVATE_KEY" ]); then
    echo "Warning: GitHub credentials are not set."
    echo "You need either a personal access token:"
    echo "export GITHUB_TOKEN=your_github_token"
    echo "Or GitHub App credentials:"
    echo "export GITHUB_APP_ID=your_github_app_id"
    echo "export GITHUB_APP_PRIVATE_KEY=your_github_app_private_key"
    echo "Continuing, but the bot may not work correctly."
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
echo "Deploying PR review bot to Modal..."
python3 -m modal deploy app.py

# Get the deployment URL
WEBHOOK_URL=$(python3 -c "from modal.cli.app import get_remote_app_url; print(get_remote_app_url('pr-review-bot') + '/github-webhook')")

echo ""
echo "Deployment successful!"
echo "Your PR review bot is now deployed."
echo ""
echo "GitHub Webhook URL:"
echo "$WEBHOOK_URL"
echo ""
echo "To set up the webhook in your GitHub repository:"
echo "1. Go to your repository settings"
echo "2. Click on 'Webhooks'"
echo "3. Click 'Add webhook'"
echo "4. Set the Payload URL to: $WEBHOOK_URL"
echo "5. Set the Content type to: application/json"
echo "6. Select 'Let me select individual events'"
echo "7. Check 'Pull requests' and 'Issue comments'"
echo "8. Click 'Add webhook'"
echo ""
echo "For more information, see the README.md file."

