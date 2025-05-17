#!/usr/bin/env python
"""
Webhook Functions Example

This script demonstrates how to use the Codegen SDK's webhook decorator to create
functions that respond to webhook events from GitHub, Slack, and Linear.
"""

import os
import sys
from typing import Dict, List, Optional, Tuple

from codegen import Codebase, function, webhook
from codegen.shared.enums.programming_language import ProgrammingLanguage


@webhook(
    label="pr-code-review",
    type="pr",
    event="created",
    description="Automatically review pull requests for code quality issues",
    users=["codegen-bot"]
)
def review_pull_request(codebase: Codebase, pr: Dict) -> None:
    """Review a pull request for code quality issues.
    
    This function is triggered when a new pull request is created. It analyzes
    the code changes for quality issues and adds comments to the PR.
    
    Args:
        codebase: The Codebase instance.
        pr: Dictionary containing pull request information.
    """
    pr_number = pr["number"]
    pr_author = pr["user"]["login"]
    
    print(f"Reviewing PR #{pr_number} by {pr_author}")
    
    # Get the files changed in the PR
    pr_files = codebase.github.get_pr_files(pr_number)
    
    # Track issues found
    issues_found = []
    
    # Review each file
    for pr_file in pr_files:
        file_path = pr_file.filename
        
        # Skip non-Python files
        if not file_path.endswith(".py"):
            continue
        
        # Get the file content
        file = codebase.get_file(file_path)
        if not file:
            continue
        
        # Check for missing docstrings
        functions = file.get_functions()
        for func in functions:
            if not func.docstring:
                issues_found.append({
                    "file": file_path,
                    "line": func.line,
                    "message": f"Function `{func.name}` is missing a docstring."
                })
        
        # Check for long functions
        for func in functions:
            if len(func.body.splitlines()) > 50:
                issues_found.append({
                    "file": file_path,
                    "line": func.line,
                    "message": f"Function `{func.name}` is too long ({len(func.body.splitlines())} lines). Consider refactoring."
                })
        
        # Check for complex functions
        for func in functions:
            if func.body.count("if ") + func.body.count("for ") + func.body.count("while ") > 10:
                issues_found.append({
                    "file": file_path,
                    "line": func.line,
                    "message": f"Function `{func.name}` is too complex. Consider refactoring."
                })
    
    # Add a summary comment to the PR
    if issues_found:
        comment = f"""
## Code Review

Hi @{pr_author}! I found {len(issues_found)} issue(s) in your code:

"""
        
        for i, issue in enumerate(issues_found, 1):
            comment += f"{i}. **{issue['file']}:{issue['line']}**: {issue['message']}\n"
        
        comment += """
Please address these issues before merging. Let me know if you have any questions!
"""
        
        codebase.create_pr_comment(pr_number, comment)
    else:
        comment = f"""
## Code Review

Hi @{pr_author}! I've reviewed your code and didn't find any issues. Great job!
"""
        
        codebase.create_pr_comment(pr_number, comment)


@webhook(
    label="issue-triage",
    type="issue",
    event="created",
    description="Automatically triage new issues",
    users=["codegen-bot"]
)
def triage_issue(codebase: Codebase, issue: Dict) -> None:
    """Triage a new issue.
    
    This function is triggered when a new issue is created. It analyzes the issue
    content and adds labels, assigns team members, and adds comments as needed.
    
    Args:
        codebase: The Codebase instance.
        issue: Dictionary containing issue information.
    """
    issue_number = issue["number"]
    issue_title = issue["title"]
    issue_body = issue["body"]
    issue_author = issue["user"]["login"]
    
    print(f"Triaging issue #{issue_number}: {issue_title}")
    
    # Determine issue type based on keywords
    labels = []
    
    if any(keyword in issue_title.lower() or keyword in issue_body.lower() 
           for keyword in ["bug", "error", "fail", "crash", "fix"]):
        labels.append("bug")
    
    if any(keyword in issue_title.lower() or keyword in issue_body.lower() 
           for keyword in ["feature", "enhancement", "add", "new"]):
        labels.append("enhancement")
    
    if any(keyword in issue_title.lower() or keyword in issue_body.lower() 
           for keyword in ["doc", "documentation", "example", "tutorial"]):
        labels.append("documentation")
    
    # Determine priority based on keywords
    if any(keyword in issue_title.lower() or keyword in issue_body.lower() 
           for keyword in ["urgent", "critical", "emergency", "severe"]):
        labels.append("high-priority")
    elif any(keyword in issue_title.lower() or keyword in issue_body.lower() 
             for keyword in ["minor", "trivial", "cosmetic"]):
        labels.append("low-priority")
    else:
        labels.append("medium-priority")
    
    # Add labels to the issue
    # Note: In a real application, you would use the GitHub API to add labels
    print(f"Would add labels to issue #{issue_number}: {', '.join(labels)}")
    
    # Add a comment to the issue
    comment = f"""
## Issue Triage

Hi @{issue_author}! Thanks for reporting this issue.

I've automatically added the following labels: {', '.join([f'`{label}`' for label in labels])}

Our team will review this issue soon.
"""
    
    # Note: In a real application, you would use the GitHub API to add a comment
    print(f"Would add comment to issue #{issue_number}:\n{comment}")


@webhook(
    label="release-notes",
    type="release",
    event="created",
    description="Generate release notes from PR descriptions",
    users=["codegen-bot"]
)
def generate_release_notes(codebase: Codebase, release: Dict) -> None:
    """Generate release notes from PR descriptions.
    
    This function is triggered when a new release is created. It collects the
    descriptions of all PRs included in the release and generates formatted
    release notes.
    
    Args:
        codebase: The Codebase instance.
        release: Dictionary containing release information.
    """
    tag_name = release["tag_name"]
    release_name = release["name"]
    previous_tag = release.get("previous_tag", "")
    
    print(f"Generating release notes for {release_name} ({tag_name})")
    
    # Get all PRs merged between the previous tag and this tag
    # Note: In a real application, you would use the GitHub API to get this information
    prs = [
        {"number": 123, "title": "Add new feature X", "body": "This PR adds feature X which allows users to...", "labels": ["enhancement"]},
        {"number": 124, "title": "Fix bug in module Y", "body": "This PR fixes a critical bug in module Y that caused...", "labels": ["bug"]},
        {"number": 125, "title": "Update documentation", "body": "This PR updates the documentation for feature Z...", "labels": ["documentation"]},
    ]
    
    # Group PRs by type
    features = []
    bug_fixes = []
    documentation = []
    other = []
    
    for pr in prs:
        if "enhancement" in pr["labels"]:
            features.append(pr)
        elif "bug" in pr["labels"]:
            bug_fixes.append(pr)
        elif "documentation" in pr["labels"]:
            documentation.append(pr)
        else:
            other.append(pr)
    
    # Generate release notes
    notes = f"""
# Release Notes for {release_name}

## Features

"""
    
    if features:
        for pr in features:
            notes += f"- {pr['title']} (#{pr['number']})\n"
    else:
        notes += "- No new features in this release\n"
    
    notes += "\n## Bug Fixes\n\n"
    
    if bug_fixes:
        for pr in bug_fixes:
            notes += f"- {pr['title']} (#{pr['number']})\n"
    else:
        notes += "- No bug fixes in this release\n"
    
    notes += "\n## Documentation\n\n"
    
    if documentation:
        for pr in documentation:
            notes += f"- {pr['title']} (#{pr['number']})\n"
    else:
        notes += "- No documentation changes in this release\n"
    
    if other:
        notes += "\n## Other Changes\n\n"
        for pr in other:
            notes += f"- {pr['title']} (#{pr['number']})\n"
    
    # Update the release notes
    # Note: In a real application, you would use the GitHub API to update the release
    print(f"Would update release notes for {release_name}:\n{notes}")


@webhook(
    label="dependency-check",
    type="push",
    event="created",
    description="Check for outdated dependencies",
    users=["codegen-bot"]
)
def check_dependencies(codebase: Codebase, push: Dict) -> None:
    """Check for outdated dependencies in the repository.
    
    This function is triggered when code is pushed to the repository. It analyzes
    dependency files and checks for outdated packages.
    
    Args:
        codebase: The Codebase instance.
        push: Dictionary containing push information.
    """
    branch = push["ref"].replace("refs/heads/", "")
    
    print(f"Checking dependencies for branch: {branch}")
    
    # Check for Python dependencies
    requirements_files = codebase.get_files(name="requirements.txt")
    pyproject_files = codebase.get_files(name="pyproject.toml")
    
    outdated_packages = []
    
    # Check requirements.txt files
    for req_file in requirements_files:
        content = req_file.content
        
        # This is a simplified check. In a real application, you would use
        # a package like pip-api to parse requirements and check versions.
        for line in content.splitlines():
            if "==" in line and not line.startswith("#"):
                package, version = line.split("==")
                package = package.strip()
                version = version.strip()
                
                # Simulate checking if the package is outdated
                if package == "requests" and version < "2.28.0":
                    outdated_packages.append({
                        "file": req_file.path,
                        "package": package,
                        "current_version": version,
                        "latest_version": "2.28.1"
                    })
                elif package == "numpy" and version < "1.23.0":
                    outdated_packages.append({
                        "file": req_file.path,
                        "package": package,
                        "current_version": version,
                        "latest_version": "1.23.5"
                    })
    
    # Check JavaScript dependencies
    package_json_files = codebase.get_files(name="package.json")
    
    for pkg_file in package_json_files:
        # This is a simplified check. In a real application, you would use
        # a package like npm to parse package.json and check versions.
        if "\"react\": \"^17.0.0\"" in pkg_file.content:
            outdated_packages.append({
                "file": pkg_file.path,
                "package": "react",
                "current_version": "17.0.0",
                "latest_version": "18.2.0"
            })
    
    # Create an issue if outdated packages are found
    if outdated_packages:
        issue_title = f"Outdated dependencies found in {branch} branch"
        
        issue_body = f"""
## Outdated Dependencies

The following dependencies are outdated:

| Package | Current Version | Latest Version | File |
|---------|----------------|----------------|------|
"""
        
        for pkg in outdated_packages:
            issue_body += f"| {pkg['package']} | {pkg['current_version']} | {pkg['latest_version']} | {pkg['file']} |\n"
        
        issue_body += """
Please update these dependencies to the latest versions.
"""
        
        # Note: In a real application, you would use the GitHub API to create an issue
        print(f"Would create issue: {issue_title}\n{issue_body}")


def simulate_webhook(webhook_name: str) -> None:
    """Simulate a webhook event.

    Args:
        webhook_name: Name of the webhook to simulate.
    """
    print(f"Simulating webhook: {webhook_name}")
    
    # Create a mock codebase
    # Note: In a real application, you would use a real Codebase instance
    class MockCodebase:
        def __init__(self):
            self.github = MockGitHub()
        
        def get_file(self, path):
            return MockFile(path)
        
        def get_files(self, name=None, extension=None):
            if name == "requirements.txt":
                return [MockFile("requirements.txt")]
            elif name == "pyproject.toml":
                return [MockFile("pyproject.toml")]
            elif name == "package.json":
                return [MockFile("package.json")]
            elif extension == ".py":
                return [MockFile("file1.py"), MockFile("file2.py")]
            return [MockFile("file1.py"), MockFile("file2.py"), MockFile("file3.js")]
        
        def create_pr_comment(self, pr_number, comment):
            print(f"Adding comment to PR #{pr_number}:\n{comment}")
    
    class MockGitHub:
        def get_pr_files(self, pr_number):
            return [MockPRFile("file1.py"), MockPRFile("file2.py")]
    
    class MockFile:
        def __init__(self, path):
            self.path = path
            if path.endswith(".py"):
                self.content = """
def example_function(param1, param2):
    # This function does something
    if param1 > 0:
        return param1 + param2
    else:
        return param2
"""
            elif path == "requirements.txt":
                self.content = """
requests==2.26.0
numpy==1.21.0
"""
            elif path == "package.json":
                self.content = """
{
  "dependencies": {
    "react": "^17.0.0",
    "react-dom": "^17.0.0"
  }
}
"""
            else:
                self.content = "Mock content"
        
        def get_functions(self):
            if self.path.endswith(".py"):
                return [MockFunction("example_function")]
            return []
    
    class MockPRFile:
        def __init__(self, filename):
            self.filename = filename
    
    class MockFunction:
        def __init__(self, name):
            self.name = name
            self.line = 2
            self.docstring = None
            self.body = """
    # This function does something
    if param1 > 0:
        return param1 + param2
    else:
        return param2
"""
    
    mock_codebase = MockCodebase()
    
    # Simulate the webhook
    if webhook_name == "pr-code-review":
        mock_pr = {
            "number": 123,
            "title": "Add new feature",
            "user": {"login": "example-user"}
        }
        review_pull_request(mock_codebase, mock_pr)
    
    elif webhook_name == "issue-triage":
        mock_issue = {
            "number": 456,
            "title": "Bug: Application crashes when clicking save",
            "body": "When I click the save button, the application crashes with an error.",
            "user": {"login": "example-user"}
        }
        triage_issue(mock_codebase, mock_issue)
    
    elif webhook_name == "release-notes":
        mock_release = {
            "tag_name": "v1.0.0",
            "name": "Version 1.0.0",
            "previous_tag": "v0.9.0"
        }
        generate_release_notes(mock_codebase, mock_release)
    
    elif webhook_name == "dependency-check":
        mock_push = {
            "ref": "refs/heads/main"
        }
        check_dependencies(mock_codebase, mock_push)
    
    else:
        print(f"Unknown webhook: {webhook_name}")


def main():
    """Main function to run the example."""
    if len(sys.argv) < 2:
        print("Usage: python webhook_functions.py <webhook_name>")
        print("  webhook_name: Name of the webhook to simulate (pr-code-review, issue-triage, release-notes, dependency-check)")
        sys.exit(1)
    
    webhook_name = sys.argv[1]
    
    try:
        simulate_webhook(webhook_name)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

