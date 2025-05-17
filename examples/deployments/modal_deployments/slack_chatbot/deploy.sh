#!/bin/bash

# Slack Chatbot Deployment Script
# This script deploys the Slack chatbot to Modal

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

if [ -z "$SLACK_BOT_TOKEN" ] || [ -z "$SLACK_SIGNING_SECRET" ]; then
    echo "Error: Slack credentials are not set."
    echo "Please set them with:"
    echo "export SLACK_BOT_TOKEN=your_slack_bot_token"
    echo "export SLACK_SIGNING_SECRET=your_slack_signing_secret"
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
echo "Deploying Slack chatbot to Modal..."
python3 -m modal deploy app.py

# Get the deployment URL
WEBHOOK_URL=$(python3 -c "from modal.cli.app import get_remote_app_url; print(get_remote_app_url('slack-chatbot') + '/slack/events')")

echo ""
echo "Deployment successful!"
echo "Your Slack chatbot is now deployed."
echo ""
echo "Slack Event Subscription URL:"
echo "$WEBHOOK_URL"
echo ""
echo "To set up the Event Subscriptions in your Slack App:"
echo "1. Go to your Slack App settings at https://api.slack.com/apps"
echo "2. Click on 'Event Subscriptions'"
echo "3. Enable events and set the Request URL to: $WEBHOOK_URL"
echo "4. Subscribe to bot events: app_mention, message.im"
echo "5. Save changes"
echo ""
echo "To set up Slash Commands:"
echo "1. Go to your Slack App settings"
echo "2. Click on 'Slash Commands'"
echo "3. Create a new command: /codegen"
echo "4. Set the Request URL to: $WEBHOOK_URL/slack/commands"
echo "5. Add a description and save"
echo ""
echo "For more information, see the README.md file."

