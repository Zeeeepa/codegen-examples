#!/bin/bash

# Check if CODEGEN_API_KEY is set
if [ -z "$CODEGEN_API_KEY" ]; then
    echo "Error: CODEGEN_API_KEY environment variable is not set."
    echo "Please set your Codegen API key before deploying:"
    echo "export CODEGEN_API_KEY=your_api_key_here"
    exit 1
fi

# Deploy the code analyzer Modal app
echo "Deploying code analyzer Modal app..."

# Create a temporary file with the API key inserted
TMP_FILE=$(mktemp)
sed "s|{{CODEGEN_API_KEY}}|$CODEGEN_API_KEY|g" app.py > "$TMP_FILE"

# Deploy the app with the API key
modal deploy "$TMP_FILE" --name code-analyzer

# Remove the temporary file
rm "$TMP_FILE"

echo "Deployment complete! Your app is now running on Modal."
echo "You can view your deployment at https://modal.com/apps"
echo "You can use the web endpoint to analyze GitHub repositories."

