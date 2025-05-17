#!/usr/bin/env python
"""
Event-Driven App Example

This script demonstrates how to use the Codegen SDK's CodegenApp class to create
event-driven applications that respond to GitHub, Slack, and Linear events.
"""

import os
import sys
from typing import Any, Dict, List, Optional

from fastapi import Request

from codegen import CodegenApp


def create_app(repo_name: str, tmp_dir: str = "/tmp/codegen") -> CodegenApp:
    """Create a CodegenApp instance.

    Args:
        repo_name: Repository name in format "owner/repo".
        tmp_dir: Temporary directory for codebase storage.

    Returns:
        Initialized CodegenApp instance.
    """
    # Create the app
    app = CodegenApp(name="codegen-example-app", repo=repo_name, tmp_dir=tmp_dir)
    
    # Parse the repository
    app.parse_repo()
    
    return app


async def handle_github_pr_created(app: CodegenApp, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle GitHub pull request creation events.

    Args:
        app: The CodegenApp instance.
        payload: The event payload.

    Returns:
        Response dictionary.
    """
    # Extract PR information
    pr_number = payload["pull_request"]["number"]
    pr_title = payload["pull_request"]["title"]
    pr_author = payload["pull_request"]["user"]["login"]
    repo_name = payload["repository"]["full_name"]
    
    print(f"Received PR created event: #{pr_number} - {pr_title} by {pr_author}")
    
    try:
        # Get the codebase
        codebase = app.get_codebase()
        
        # Analyze the PR
        pr_files = codebase.github.get_pr_files(pr_number)
        file_count = len(pr_files)
        
        # Create a comment on the PR
        comment = f"""
## PR Analysis

Thank you for your contribution, @{pr_author}!

This PR modifies {file_count} files.

### Files Changed
{', '.join([f'`{f.filename}`' for f in pr_files[:5]])}
{f'... and {file_count - 5} more' if file_count > 5 else ''}

### Next Steps
- [ ] Review code changes
- [ ] Run tests
- [ ] Update documentation if needed
        """
        
        codebase.create_pr_comment(pr_number, comment)
        
        return {"status": "success", "message": f"Processed PR #{pr_number}"}
        
    except Exception as e:
        print(f"Error processing PR: {e}")
        return {"status": "error", "message": str(e)}


async def handle_github_issue_created(app: CodegenApp, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle GitHub issue creation events.

    Args:
        app: The CodegenApp instance.
        payload: The event payload.

    Returns:
        Response dictionary.
    """
    # Extract issue information
    issue_number = payload["issue"]["number"]
    issue_title = payload["issue"]["title"]
    issue_author = payload["issue"]["user"]["login"]
    repo_name = payload["repository"]["full_name"]
    
    print(f"Received issue created event: #{issue_number} - {issue_title} by {issue_author}")
    
    try:
        # Get the codebase
        codebase = app.get_codebase()
        
        # Create a comment on the issue
        comment = f"""
Thank you for reporting this issue, @{issue_author}!

We'll review it and get back to you soon.

### Issue Triage
- [ ] Reproduce the issue
- [ ] Identify root cause
- [ ] Develop fix
- [ ] Test fix
- [ ] Deploy fix
        """
        
        # Note: This is a simplified example. In a real application, you would use
        # the GitHub API to create a comment on the issue.
        print(f"Would add comment to issue #{issue_number}:\n{comment}")
        
        return {"status": "success", "message": f"Processed issue #{issue_number}"}
        
    except Exception as e:
        print(f"Error processing issue: {e}")
        return {"status": "error", "message": str(e)}


async def handle_slack_message(app: CodegenApp, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle Slack message events.

    Args:
        app: The CodegenApp instance.
        payload: The event payload.

    Returns:
        Response dictionary.
    """
    # Extract message information
    event = payload.get("event", {})
    message_text = event.get("text", "")
    user_id = event.get("user", "")
    channel_id = event.get("channel", "")
    
    print(f"Received Slack message: '{message_text}' from user {user_id} in channel {channel_id}")
    
    # Check if the message is a command
    if message_text.startswith("!analyze"):
        try:
            # Get the codebase
            codebase = app.get_codebase()
            
            # Analyze the codebase
            python_files = codebase.get_files(extension=".py")
            typescript_files = codebase.get_files(extension=[".ts", ".tsx"])
            
            # Prepare the response
            response = f"""
*Codebase Analysis*

Repository: {codebase.name}
Total files: {len(codebase.get_files())}
Python files: {len(python_files)}
TypeScript files: {len(typescript_files)}
            """
            
            # Note: This is a simplified example. In a real application, you would use
            # the Slack API to send a message to the channel.
            print(f"Would send Slack response to channel {channel_id}:\n{response}")
            
            return {"status": "success", "message": "Processed Slack command"}
            
        except Exception as e:
            print(f"Error processing Slack command: {e}")
            return {"status": "error", "message": str(e)}
    
    return {"status": "success", "message": "Ignored non-command message"}


async def handle_linear_issue_created(app: CodegenApp, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle Linear issue creation events.

    Args:
        app: The CodegenApp instance.
        payload: The event payload.

    Returns:
        Response dictionary.
    """
    # Extract issue information
    issue_data = payload.get("data", {})
    issue_id = issue_data.get("id", "")
    issue_title = issue_data.get("title", "")
    issue_creator = issue_data.get("creator", {}).get("name", "Unknown")
    
    print(f"Received Linear issue created event: {issue_id} - {issue_title} by {issue_creator}")
    
    try:
        # Get the codebase
        codebase = app.get_codebase()
        
        # Prepare the response
        response = f"""
Thank you for creating this issue, {issue_creator}!

We'll review it and get back to you soon.

### Issue Triage
- [ ] Understand requirements
- [ ] Estimate effort
- [ ] Assign to team member
- [ ] Implement solution
- [ ] Test solution
        """
        
        # Note: This is a simplified example. In a real application, you would use
        # the Linear API to add a comment to the issue.
        print(f"Would add comment to Linear issue {issue_id}:\n{response}")
        
        return {"status": "success", "message": f"Processed Linear issue {issue_id}"}
        
    except Exception as e:
        print(f"Error processing Linear issue: {e}")
        return {"status": "error", "message": str(e)}


def register_event_handlers(app: CodegenApp) -> None:
    """Register event handlers for the app.

    Args:
        app: The CodegenApp instance.
    """
    # Register GitHub event handlers
    @app.github.on("pull_request.opened")
    async def on_pr_created(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
        return await handle_github_pr_created(app, payload)
    
    @app.github.on("issues.opened")
    async def on_issue_created(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
        return await handle_github_issue_created(app, payload)
    
    # Register Slack event handlers
    @app.slack.on("message")
    async def on_slack_message(payload: Dict[str, Any]) -> Dict[str, Any]:
        return await handle_slack_message(app, payload)
    
    # Register Linear event handlers
    @app.linear.on("Issue.create")
    async def on_linear_issue_created(payload: Dict[str, Any]) -> Dict[str, Any]:
        return await handle_linear_issue_created(app, payload)


def simulate_events(app: CodegenApp) -> None:
    """Simulate events for testing.

    Args:
        app: The CodegenApp instance.
    """
    # Simulate a GitHub PR created event
    pr_payload = {
        "action": "opened",
        "pull_request": {
            "number": 123,
            "title": "Add new feature",
            "user": {"login": "example-user"}
        },
        "repository": {
            "full_name": app.repo
        }
    }
    
    # Simulate a GitHub issue created event
    issue_payload = {
        "action": "opened",
        "issue": {
            "number": 456,
            "title": "Bug report",
            "user": {"login": "example-user"}
        },
        "repository": {
            "full_name": app.repo
        }
    }
    
    # Simulate a Slack message event
    slack_payload = {
        "event": {
            "type": "message",
            "text": "!analyze",
            "user": "U12345",
            "channel": "C67890"
        }
    }
    
    # Simulate a Linear issue created event
    linear_payload = {
        "action": "create",
        "type": "Issue",
        "data": {
            "id": "ABC123",
            "title": "New feature request",
            "creator": {"name": "Example User"}
        }
    }
    
    # Process the simulated events
    import asyncio
    
    loop = asyncio.get_event_loop()
    
    print("\n=== Simulating GitHub PR Created Event ===")
    loop.run_until_complete(app.simulate_event("github", "pull_request.opened", pr_payload))
    
    print("\n=== Simulating GitHub Issue Created Event ===")
    loop.run_until_complete(app.simulate_event("github", "issues.opened", issue_payload))
    
    print("\n=== Simulating Slack Message Event ===")
    loop.run_until_complete(app.simulate_event("slack", "message", slack_payload))
    
    print("\n=== Simulating Linear Issue Created Event ===")
    loop.run_until_complete(app.simulate_event("linear", "Issue.create", linear_payload))


def main():
    """Main function to run the example."""
    if len(sys.argv) < 2:
        print("Usage: python event_app.py <repo_name> [simulate]")
        print("  repo_name: Repository name in format 'owner/repo'")
        print("  simulate: Optional flag to simulate events instead of running the server")
        sys.exit(1)
    
    repo_name = sys.argv[1]
    simulate_flag = len(sys.argv) > 2 and sys.argv[2].lower() == "simulate"
    
    try:
        # Create the app
        app = create_app(repo_name)
        
        # Register event handlers
        register_event_handlers(app)
        
        if simulate_flag:
            # Simulate events for testing
            simulate_events(app)
        else:
            # Run the app
            print(f"Starting CodegenApp for repository: {repo_name}")
            print("Server will listen on http://0.0.0.0:8000")
            print("Press Ctrl+C to stop")
            
            app.run(host="0.0.0.0", port=8000)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

