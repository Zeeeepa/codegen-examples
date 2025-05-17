#!/bin/bash

# Check if required secrets are set up in Modal
echo "Checking if required secrets are set up in Modal..."

# Check if linear-webhook-secret exists
if ! modal secret list | grep -q "linear-webhook-secret"; then
    echo "Error: 'linear-webhook-secret' not found in Modal secrets."
    echo "Please create it with:"
    echo "modal secret create linear-webhook-secret --value YOUR_LINEAR_WEBHOOK_SECRET"
    exit 1
fi

# Check if codegen-api-key exists
if ! modal secret list | grep -q "codegen-api-key"; then
    echo "Error: 'codegen-api-key' not found in Modal secrets."
    echo "Please create it with:"
    echo "modal secret create codegen-api-key --value YOUR_CODEGEN_API_KEY"
    exit 1
fi

# Deploy the Linear webhooks Modal app
echo "Deploying Linear webhooks Modal app..."
modal deploy app.py

echo "Deployment complete! Your app is now running on Modal."
echo "You can view your deployment at https://modal.com/apps"
echo ""
echo "To set up the Linear webhook:"
echo "1. Go to your Linear workspace settings"
echo "2. Navigate to 'API' > 'Webhooks'"
echo "3. Create a new webhook with the URL:"
echo "   https://linear-webhooks--linear-webhook-[your-modal-username].modal.run"
echo "4. Select the events you want to trigger the webhook (at least 'Issue: created')"
echo "5. Copy the webhook secret and add it to Modal secrets:"
echo "   modal secret create linear-webhook-secret --value YOUR_LINEAR_WEBHOOK_SECRET"

