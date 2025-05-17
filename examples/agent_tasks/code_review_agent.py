#!/usr/bin/env python
"""
Code Review Agent Example

This script demonstrates how to use the Codegen SDK's Agent class to create an
AI-powered code review agent that can analyze code and provide feedback.
"""

import os
import sys
import time
from typing import Dict, List, Optional, Tuple

from codegen import Agent


def read_code_file(file_path: str) -> str:
    """Read code from a file.

    Args:
        file_path: Path to the code file.

    Returns:
        The code as a string.
    """
    try:
        with open(file_path, "r") as f:
            return f.read()
    except Exception as e:
        raise ValueError(f"Error reading file {file_path}: {e}")


def generate_review_prompt(code: str, language: Optional[str] = None) -> str:
    """Generate a prompt for the code review agent.

    Args:
        code: The code to review.
        language: The programming language of the code (optional).

    Returns:
        A prompt string for the agent.
    """
    # Determine language from file extension if not provided
    if not language and "file_path" in globals():
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".py":
            language = "Python"
        elif ext in [".js", ".jsx"]:
            language = "JavaScript"
        elif ext in [".ts", ".tsx"]:
            language = "TypeScript"
        elif ext == ".java":
            language = "Java"
        elif ext in [".c", ".cpp", ".h", ".hpp"]:
            language = "C++"
        else:
            language = "Unknown"
    
    return f"""
    Please review the following {language} code and provide feedback on:
    
    1. Code quality and style
    2. Potential bugs or errors
    3. Performance issues
    4. Security concerns
    5. Suggestions for improvement
    
    For each issue, please provide:
    - The line number or code snippet
    - A description of the issue
    - A suggested fix or improvement
    
    Here is the code to review:
    
    ```
    {code}
    ```
    
    Please format your response as a structured code review with clear sections for each category of feedback.
    """


def run_code_review(code: str, token: Optional[str] = None, org_id: int = 1) -> Dict:
    """Run a code review using the Codegen Agent.

    Args:
        code: The code to review.
        token: API authentication token. If not provided, will use environment variable.
        org_id: Organization ID (default: 1).

    Returns:
        Dictionary containing the review result and status.
    """
    # Use environment variable if token not provided
    api_token = token or os.environ.get("CODEGEN_API_TOKEN")
    if not api_token:
        raise ValueError("API token is required. Provide it as an argument or set CODEGEN_API_TOKEN environment variable.")
    
    # Generate the review prompt
    prompt = generate_review_prompt(code)
    
    # Initialize the Agent
    agent = Agent(token=api_token, org_id=org_id)
    
    # Run the task
    task = agent.run(prompt)
    print(f"Code review started: {task.id}")
    
    # Poll for task completion
    max_attempts = 30
    attempts = 0
    
    while attempts < max_attempts:
        status = agent.get_status()
        print(f"Review status: {status['status']}")
        
        if status["status"] == "completed":
            return {
                "id": status["id"],
                "status": status["status"],
                "result": status["result"],
                "web_url": status["web_url"]
            }
        
        if status["status"] == "failed":
            raise Exception(f"Review failed: {status.get('result', 'No error message provided')}")
        
        # Wait before checking again
        time.sleep(2)
        attempts += 1
    
    raise TimeoutError("Review did not complete within the expected time.")


def parse_review_feedback(review: str) -> Dict[str, List[Dict]]:
    """Parse the review feedback into structured categories.

    Args:
        review: The review text from the agent.

    Returns:
        Dictionary with categorized feedback.
    """
    # This is a simplified parser. In a real application, you might want to use
    # a more sophisticated approach to extract structured data from the review.
    categories = {
        "code_quality": [],
        "bugs": [],
        "performance": [],
        "security": [],
        "improvements": []
    }
    
    current_category = None
    
    for line in review.split("\n"):
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
        
        # Check for category headers
        lower_line = line.lower()
        if "quality" in lower_line or "style" in lower_line:
            current_category = "code_quality"
            continue
        elif "bug" in lower_line or "error" in lower_line:
            current_category = "bugs"
            continue
        elif "performance" in lower_line:
            current_category = "performance"
            continue
        elif "security" in lower_line:
            current_category = "security"
            continue
        elif "improvement" in lower_line or "suggestion" in lower_line:
            current_category = "improvements"
            continue
        
        # If we have a current category and the line starts with a bullet point or number
        if current_category and (line.startswith("-") or line.startswith("*") or (line[0].isdigit() and line[1:3] in [". ", ") "])):
            categories[current_category].append({"description": line[2:].strip()})
    
    return categories


def save_review_to_file(review: str, filename: str) -> None:
    """Save the review to a file.

    Args:
        review: The review text.
        filename: The filename to save to.
    """
    with open(filename, "w") as f:
        f.write(review)
    
    print(f"Review saved to {filename}")


def main():
    """Main function to run the example."""
    if len(sys.argv) < 2:
        print("Usage: python code_review_agent.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    try:
        # Read the code file
        code = read_code_file(file_path)
        
        # Run the code review
        result = run_code_review(code)
        
        print("\nCode review completed successfully!")
        print(f"View the review at: {result['web_url']}")
        
        # Parse and display the review feedback
        feedback = parse_review_feedback(result["result"])
        
        print("\nReview Summary:")
        for category, items in feedback.items():
            if items:
                print(f"\n{category.replace('_', ' ').title()} ({len(items)} issues):")
                for item in items:
                    print(f"  - {item['description']}")
        
        # Save the full review to a file
        review_filename = os.path.splitext(os.path.basename(file_path))[0] + "_review.md"
        save_review_to_file(result["result"], review_filename)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

