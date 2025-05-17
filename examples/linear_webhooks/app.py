"""
A Modal application that handles Linear webhooks and uses Codegen to analyze code.
"""

import json
import hmac
import hashlib
import os
from typing import Dict, Optional

import modal
from modal import web

# Define the Modal app
app = modal.App("linear-webhooks")

# Create an image with Python dependencies
image = modal.Image.debian_slim().pip_install(
    [
        "codegen==0.52.19",
        "pydantic>=2.0.0",
    ]
)

# Define a secret for the Linear webhook
linear_webhook_secret = modal.Secret.from_name("linear-webhook-secret")

# Define a secret for the Codegen API key
codegen_api_key = modal.Secret.from_name("codegen-api-key")

# Define a function to verify the Linear webhook signature
def verify_linear_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify the Linear webhook signature."""
    computed_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed_signature, signature)

# Define a function to handle Linear issue creation
@app.function(image=image, secrets=[codegen_api_key])
def handle_issue_created(data: Dict) -> Dict:
    """Handle a Linear issue creation event."""
    import codegen
    
    # Extract issue data
    issue = data.get("data", {}).get("issue", {})
    if not issue:
        return {"status": "error", "message": "No issue data found"}
    
    issue_id = issue.get("id")
    issue_title = issue.get("title", "")
    issue_description = issue.get("description", "")
    
    # Check if the issue contains a GitHub repository URL
    import re
    repo_pattern = r"https://github\.com/([^/]+)/([^/\s]+)"
    repo_match = re.search(repo_pattern, issue_description)
    
    if not repo_match:
        return {
            "status": "success",
            "message": "No GitHub repository found in issue description",
            "issue_id": issue_id,
        }
    
    # Extract repository information
    owner = repo_match.group(1)
    repo = repo_match.group(2)
    repo_url = f"https://github.com/{owner}/{repo}.git"
    
    # Initialize Codegen with the repository
    codebase = codegen.Codebase.from_github(
        repo=f"{owner}/{repo}",
        api_key=os.environ["CODEGEN_API_KEY"],
    )
    
    # Generate a simple analysis
    analysis = {
        "num_files": len(codebase.files),
        "num_functions": len(codebase.functions),
        "num_classes": len(codebase.classes),
        "languages": list(set(f.language for f in codebase.files if f.language)),
    }
    
    # Add a comment to the Linear issue with the analysis
    # Note: In a real application, you would use the Linear API to add a comment
    
    return {
        "status": "success",
        "message": "Repository analyzed",
        "issue_id": issue_id,
        "repo": f"{owner}/{repo}",
        "analysis": analysis,
    }

# Define a web endpoint to handle Linear webhooks
@app.function(image=image, secrets=[linear_webhook_secret, codegen_api_key], keep_warm=1)
@modal.web_endpoint(method="POST")
def linear_webhook(request: web.Request) -> Dict:
    """Handle Linear webhooks."""
    # Get the request payload
    payload = request.body
    
    # Get the Linear signature
    signature = request.headers.get("linear-signature")
    if not signature:
        return {"status": "error", "message": "No Linear signature found"}
    
    # Verify the signature
    if not verify_linear_signature(payload, signature, linear_webhook_secret.get()):
        return {"status": "error", "message": "Invalid Linear signature"}
    
    # Parse the payload
    data = json.loads(payload)
    
    # Get the event type
    event_type = data.get("type")
    if not event_type:
        return {"status": "error", "message": "No event type found"}
    
    # Handle different event types
    if event_type == "Issue.created":
        return handle_issue_created.remote(data)
    
    # Return a default response for unhandled event types
    return {
        "status": "success",
        "message": f"Event type '{event_type}' not handled",
    }

if __name__ == "__main__":
    # This block is executed when running the script directly
    print("This script is designed to be deployed as a Modal application.")
    print("Use 'modal deploy app.py' to deploy it.")
