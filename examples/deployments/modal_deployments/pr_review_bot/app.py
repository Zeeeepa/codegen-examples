"""
PR Review Bot
A Modal application that automatically reviews GitHub pull requests using the Codegen API.
"""

import os
import json
import hmac
import base64
import tempfile
import subprocess
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple

import modal
from modal import web_endpoint, Image, Stub, Secret, asgi_app
from fastapi import FastAPI, Request, Response, HTTPException, Depends, Header
from fastapi.responses import JSONResponse
from codegen import Codebase, Agent

# Define the Modal image with required dependencies
image = Image.debian_slim().pip_install(
    "codegen>=0.52.19",
    "gitpython>=3.1.30",
    "python-dotenv>=1.0.0",
    "pyyaml>=6.0",
    "fastapi>=0.95.0",
    "pyjwt>=2.6.0",
    "cryptography>=40.0.0",
)

# Create a Modal Stub
stub = Stub(
    name="pr-review-bot",
    image=image,
    secrets=[
        Secret.from_name("codegen-secrets"),  # Contains CODEGEN_API_TOKEN
        Secret.from_name("github-secrets"),   # Contains GITHUB_TOKEN or GITHUB_APP_* variables
    ]
)

# Create a FastAPI app
app = FastAPI()

# GitHub App authentication
def get_github_token(installation_id: int) -> str:
    """
    Get a GitHub token for an installation ID using GitHub App credentials.
    
    Args:
        installation_id: GitHub App installation ID
        
    Returns:
        GitHub token
    """
    import jwt
    import time
    import requests
    
    # Get GitHub App credentials
    app_id = os.environ.get("GITHUB_APP_ID")
    private_key = os.environ.get("GITHUB_APP_PRIVATE_KEY")
    
    if not app_id or not private_key:
        # Fall back to personal access token
        return os.environ.get("GITHUB_TOKEN", "")
    
    # Create a JWT for GitHub App authentication
    now = int(time.time())
    payload = {
        "iat": now,
        "exp": now + 600,
        "iss": app_id,
    }
    
    # Replace newlines in private key if needed
    if "\\n" in private_key:
        private_key = private_key.replace("\\n", "\n")
    
    # Sign the JWT
    encoded_jwt = jwt.encode(payload, private_key, algorithm="RS256")
    
    # Get an installation token
    headers = {
        "Authorization": f"Bearer {encoded_jwt}",
        "Accept": "application/vnd.github.v3+json",
    }
    
    response = requests.post(
        f"https://api.github.com/app/installations/{installation_id}/access_tokens",
        headers=headers,
    )
    
    if response.status_code != 201:
        print(f"Error getting installation token: {response.status_code} {response.text}")
        return os.environ.get("GITHUB_TOKEN", "")
    
    return response.json()["token"]

def clone_repository(repo_url: str, target_dir: str, token: str) -> bool:
    """
    Clone a GitHub repository to the target directory.
    
    Args:
        repo_url: URL of the GitHub repository
        target_dir: Directory to clone the repository to
        token: GitHub token
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Add GitHub token to URL
        if "github.com" in repo_url:
            # Insert token into URL for private repo access
            if repo_url.startswith("https://"):
                repo_url = repo_url.replace(
                    "https://", f"https://{token}@"
                )
        
        # Clone the repository
        subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, target_dir],
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False

def fetch_pull_request(repo_owner: str, repo_name: str, pr_number: int, token: str) -> Dict[str, Any]:
    """
    Fetch pull request details from GitHub.
    
    Args:
        repo_owner: Repository owner
        repo_name: Repository name
        pr_number: Pull request number
        token: GitHub token
        
    Returns:
        Dict containing pull request details
    """
    import requests
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    
    response = requests.get(
        f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls/{pr_number}",
        headers=headers,
    )
    
    if response.status_code != 200:
        print(f"Error fetching PR: {response.status_code} {response.text}")
        return {}
    
    return response.json()

def fetch_pull_request_files(repo_owner: str, repo_name: str, pr_number: int, token: str) -> List[Dict[str, Any]]:
    """
    Fetch files changed in a pull request.
    
    Args:
        repo_owner: Repository owner
        repo_name: Repository name
        pr_number: Pull request number
        token: GitHub token
        
    Returns:
        List of files changed in the pull request
    """
    import requests
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    
    response = requests.get(
        f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls/{pr_number}/files",
        headers=headers,
    )
    
    if response.status_code != 200:
        print(f"Error fetching PR files: {response.status_code} {response.text}")
        return []
    
    return response.json()

def add_pr_comment(repo_owner: str, repo_name: str, pr_number: int, comment: str, token: str) -> bool:
    """
    Add a comment to a pull request.
    
    Args:
        repo_owner: Repository owner
        repo_name: Repository name
        pr_number: Pull request number
        comment: Comment text
        token: GitHub token
        
    Returns:
        bool: True if successful, False otherwise
    """
    import requests
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    
    response = requests.post(
        f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{pr_number}/comments",
        headers=headers,
        json={"body": comment},
    )
    
    return response.status_code == 201

def add_pr_review_comment(
    repo_owner: str, 
    repo_name: str, 
    pr_number: int, 
    commit_id: str,
    path: str,
    position: int,
    body: str,
    token: str
) -> bool:
    """
    Add a review comment to a specific line in a pull request.
    
    Args:
        repo_owner: Repository owner
        repo_name: Repository name
        pr_number: Pull request number
        commit_id: Commit ID
        path: File path
        position: Line position
        body: Comment text
        token: GitHub token
        
    Returns:
        bool: True if successful, False otherwise
    """
    import requests
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    
    response = requests.post(
        f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls/{pr_number}/comments",
        headers=headers,
        json={
            "commit_id": commit_id,
            "path": path,
            "position": position,
            "body": body,
        },
    )
    
    return response.status_code == 201

def load_config(repo_dir: str) -> Dict[str, Any]:
    """
    Load the PR review bot configuration from the repository.
    
    Args:
        repo_dir: Repository directory
        
    Returns:
        Dict containing configuration
    """
    # Default configuration
    default_config = {
        "version": 1,
        "review": {
            "focus": ["security", "performance", "style", "documentation"],
            "severity": ["error", "warning", "info"],
            "max_comments": 10,
            "add_summary": True,
            "ignore": ["*.md", "*.json", "tests/**", "docs/**"],
        },
    }
    
    # Check if configuration file exists
    config_path = os.path.join(repo_dir, ".codegen-review.yml")
    if not os.path.exists(config_path):
        return default_config
    
    try:
        # Load configuration from file
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        # Merge with default configuration
        if not config:
            return default_config
        
        if "review" not in config:
            config["review"] = default_config["review"]
        else:
            for key, value in default_config["review"].items():
                if key not in config["review"]:
                    config["review"][key] = value
        
        return config
    except:
        return default_config

def review_pull_request(
    repo_owner: str,
    repo_name: str,
    pr_number: int,
    focus_areas: List[str] = None,
) -> Dict[str, Any]:
    """
    Review a pull request and provide feedback.
    
    Args:
        repo_owner: Repository owner
        repo_name: Repository name
        pr_number: Pull request number
        focus_areas: Areas to focus on (security, performance, style, documentation)
        
    Returns:
        Dict containing review results
    """
    # Get GitHub token
    token = os.environ.get("GITHUB_TOKEN", "")
    
    # Fetch pull request details
    pr_details = fetch_pull_request(repo_owner, repo_name, pr_number, token)
    if not pr_details:
        return {"error": "Failed to fetch pull request details"}
    
    # Get installation ID if using GitHub App
    installation_id = pr_details.get("base", {}).get("repo", {}).get("installation_id")
    if installation_id:
        token = get_github_token(installation_id)
    
    # Fetch files changed in the pull request
    pr_files = fetch_pull_request_files(repo_owner, repo_name, pr_number, token)
    if not pr_files:
        return {"error": "Failed to fetch pull request files"}
    
    # Get repository URL
    repo_url = f"https://github.com/{repo_owner}/{repo_name}.git"
    
    # Create a temporary directory for the repository
    with tempfile.TemporaryDirectory() as temp_dir:
        # Clone the repository
        if not clone_repository(repo_url, temp_dir, token):
            return {"error": "Failed to clone repository"}
        
        # Checkout the PR branch
        try:
            subprocess.run(
                ["git", "fetch", "origin", pr_details["head"]["ref"]],
                cwd=temp_dir,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "checkout", pr_details["head"]["ref"]],
                cwd=temp_dir,
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError:
            # Try to checkout by commit hash if branch fetch fails
            try:
                subprocess.run(
                    ["git", "checkout", pr_details["head"]["sha"]],
                    cwd=temp_dir,
                    check=True,
                    capture_output=True,
                )
            except subprocess.CalledProcessError:
                return {"error": "Failed to checkout pull request branch"}
        
        # Load configuration
        config = load_config(temp_dir)
        
        # Override focus areas if specified
        if focus_areas:
            config["review"]["focus"] = focus_areas
        
        # Initialize Codegen Codebase
        codebase = Codebase(temp_dir)
        
        # Initialize Codegen Agent
        agent = Agent(
            token=os.environ.get("CODEGEN_API_TOKEN"),
            codebase=codebase,
        )
        
        # Generate review for each file
        reviews = []
        for file in pr_files:
            # Skip files that match ignore patterns
            file_path = file["filename"]
            skip = False
            for pattern in config["review"]["ignore"]:
                if pattern.endswith("/**"):
                    # Directory pattern
                    dir_pattern = pattern[:-3]
                    if file_path.startswith(dir_pattern):
                        skip = True
                        break
                elif pattern.startswith("*."):
                    # Extension pattern
                    ext = pattern[1:]
                    if file_path.endswith(ext):
                        skip = True
                        break
                elif pattern == file_path:
                    # Exact match
                    skip = True
                    break
            
            if skip:
                continue
            
            # Skip binary files
            if file.get("status") == "removed" or file.get("binary"):
                continue
            
            # Generate review for the file
            prompt = f"""
            Review the following file in a pull request: {file_path}
            
            Focus on the following areas: {', '.join(config['review']['focus'])}
            
            For each issue you find, provide:
            1. Line number
            2. Severity (error, warning, info)
            3. Description of the issue
            4. Suggested fix
            
            Format your response as a JSON array of objects with the following structure:
            [
                {{
                    "line": int,
                    "severity": string,
                    "description": string,
                    "suggestion": string
                }}
            ]
            
            Only include issues with severity levels: {', '.join(config['review']['severity'])}
            """
            
            response = agent.run(prompt)
            
            try:
                # Parse the JSON response
                file_review = json.loads(response)
                
                # Add file path to each issue
                for issue in file_review:
                    issue["file"] = file_path
                    issue["commit_id"] = pr_details["head"]["sha"]
                
                reviews.extend(file_review)
            except:
                # Skip if parsing fails
                continue
        
        # Sort reviews by severity
        severity_order = {"error": 0, "warning": 1, "info": 2}
        reviews.sort(key=lambda x: severity_order.get(x["severity"], 3))
        
        # Limit the number of comments
        reviews = reviews[:config["review"]["max_comments"]]
        
        # Add comments to the pull request
        for review in reviews:
            comment = f"""
### {review['severity'].upper()}: {review['description']}

**File:** {review['file']}  
**Line:** {review['line']}

{review['suggestion']}

---
*This comment was generated automatically by the Codegen PR Review Bot.*
            """
            
            add_pr_review_comment(
                repo_owner=repo_owner,
                repo_name=repo_name,
                pr_number=pr_number,
                commit_id=review["commit_id"],
                path=review["file"],
                position=review["line"],
                body=comment,
                token=token,
            )
        
        # Add summary comment if enabled
        if config["review"]["add_summary"] and reviews:
            # Count issues by severity
            severity_counts = {}
            for review in reviews:
                severity = review["severity"]
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            # Generate summary
            summary = f"""
## PR Review Summary

I've reviewed this pull request and found the following issues:

{', '.join([f"**{count} {severity}**" for severity, count in severity_counts.items()])}

Focus areas: {', '.join(config['review']['focus'])}

{len(reviews)} comments have been added to specific lines in the code.

---
*This review was generated automatically by the Codegen PR Review Bot.*
            """
            
            add_pr_comment(
                repo_owner=repo_owner,
                repo_name=repo_name,
                pr_number=pr_number,
                comment=summary,
                token=token,
            )
        elif config["review"]["add_summary"] and not reviews:
            # No issues found
            summary = f"""
## PR Review Summary

I've reviewed this pull request and found no issues! 🎉

Focus areas: {', '.join(config['review']['focus'])}

---
*This review was generated automatically by the Codegen PR Review Bot.*
            """
            
            add_pr_comment(
                repo_owner=repo_owner,
                repo_name=repo_name,
                pr_number=pr_number,
                comment=summary,
                token=token,
            )
        
        return {
            "repo": f"{repo_owner}/{repo_name}",
            "pr": pr_number,
            "reviews": len(reviews),
            "focus_areas": config["review"]["focus"],
        }

@app.post("/github-webhook")
async def github_webhook(request: Request):
    """
    Handle GitHub webhook events.
    """
    # Get the request body
    body = await request.body()
    payload = json.loads(body)
    
    # Get the event type
    event_type = request.headers.get("X-GitHub-Event")
    
    # Handle pull request events
    if event_type == "pull_request":
        action = payload.get("action")
        if action in ["opened", "synchronize"]:
            # New PR or new commits pushed to PR
            pr = payload.get("pull_request", {})
            repo = payload.get("repository", {})
            
            # Extract repository details
            repo_owner = repo.get("owner", {}).get("login")
            repo_name = repo.get("name")
            pr_number = pr.get("number")
            
            if repo_owner and repo_name and pr_number:
                # Review the pull request
                review_pull_request.spawn(
                    repo_owner=repo_owner,
                    repo_name=repo_name,
                    pr_number=pr_number,
                )
    
    # Handle issue comment events
    elif event_type == "issue_comment":
        action = payload.get("action")
        if action == "created":
            # New comment
            comment = payload.get("comment", {})
            issue = payload.get("issue", {})
            repo = payload.get("repository", {})
            
            # Check if this is a PR comment
            if "pull_request" not in issue:
                return {"status": "ignored", "reason": "not a pull request comment"}
            
            # Extract comment text
            comment_text = comment.get("body", "").strip().lower()
            
            # Check if this is a review command
            if comment_text.startswith("/review"):
                # Extract repository details
                repo_owner = repo.get("owner", {}).get("login")
                repo_name = repo.get("name")
                pr_number = issue.get("number")
                
                # Extract focus areas
                focus_areas = []
                if " " in comment_text:
                    areas = comment_text.split(" ", 1)[1].strip().split()
                    valid_areas = ["security", "performance", "style", "documentation"]
                    focus_areas = [area for area in areas if area in valid_areas]
                
                if repo_owner and repo_name and pr_number:
                    # Review the pull request
                    review_pull_request.spawn(
                        repo_owner=repo_owner,
                        repo_name=repo_name,
                        pr_number=pr_number,
                        focus_areas=focus_areas if focus_areas else None,
                    )
    
    return {"status": "ok"}

@stub.function
@asgi_app()
def fastapi_app():
    """
    Serve the FastAPI application.
    """
    return app

if __name__ == "__main__":
    # This will be executed when running the script locally
    stub.deploy("pr-review-bot")
    print("PR Review Bot deployed successfully!")

