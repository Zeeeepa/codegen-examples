#!/usr/bin/env python
"""
Basic Agent Example

This script demonstrates how to use the Codegen SDK's Agent class to create and
run AI-powered agents for code generation tasks.
"""

import os
import sys
import time
from typing import Dict, Optional

from codegen import Agent


def run_agent_task(prompt: str, token: Optional[str] = None, org_id: int = 1) -> Dict:
    """Run a task using the Codegen Agent.

    Args:
        prompt: The instruction for the agent to execute.
        token: API authentication token. If not provided, will use environment variable.
        org_id: Organization ID (default: 1).

    Returns:
        Dictionary containing the task result and status.
    """
    # Use environment variable if token not provided
    api_token = token or os.environ.get("CODEGEN_API_TOKEN")
    if not api_token:
        raise ValueError("API token is required. Provide it as an argument or set CODEGEN_API_TOKEN environment variable.")
    
    # Initialize the Agent
    agent = Agent(token=api_token, org_id=org_id)
    
    # Run the task
    task = agent.run(prompt)
    print(f"Task started: {task.id}")
    
    # Poll for task completion
    max_attempts = 30
    attempts = 0
    
    while attempts < max_attempts:
        status = agent.get_status()
        print(f"Task status: {status['status']}")
        
        if status["status"] == "completed":
            return {
                "id": status["id"],
                "status": status["status"],
                "result": status["result"],
                "web_url": status["web_url"]
            }
        
        if status["status"] == "failed":
            raise Exception(f"Task failed: {status.get('result', 'No error message provided')}")
        
        # Wait before checking again
        time.sleep(2)
        attempts += 1
    
    raise TimeoutError("Task did not complete within the expected time.")


def extract_code_from_response(response: str) -> str:
    """Extract code blocks from the agent's response.

    Args:
        response: The agent's response text.

    Returns:
        Extracted code as a string.
    """
    # Look for Python code blocks
    if "```python" in response:
        # Extract code between ```python and ```
        code_blocks = []
        parts = response.split("```python")
        for part in parts[1:]:  # Skip the first part (before the first ```python)
            if "```" in part:
                code_block = part.split("```")[0].strip()
                code_blocks.append(code_block)
        
        return "\n\n".join(code_blocks)
    
    # Look for generic code blocks
    elif "```" in response:
        # Extract code between ``` and ```
        code_blocks = []
        parts = response.split("```")
        for i in range(1, len(parts), 2):  # Get every other part (inside ```)
            if i < len(parts):
                code_block = parts[i].strip()
                # Skip if it starts with a language identifier
                if code_block.split("\n")[0].strip() in ["python", "javascript", "typescript", "java", "c++", "bash", "shell"]:
                    code_block = "\n".join(code_block.split("\n")[1:])
                code_blocks.append(code_block)
        
        return "\n\n".join(code_blocks)
    
    # No code blocks found, return the whole response
    return response


def save_code_to_file(code: str, filename: str) -> None:
    """Save the generated code to a file.

    Args:
        code: The code to save.
        filename: The filename to save to.
    """
    with open(filename, "w") as f:
        f.write(code)
    
    print(f"Code saved to {filename}")


def main():
    """Main function to run the example."""
    # Define the prompt for the agent
    prompt = """
    Generate a Python function that implements a binary search algorithm.
    The function should:
    1. Take a sorted list and a target value as input
    2. Return the index of the target if found, or -1 if not found
    3. Include proper type hints
    4. Include a comprehensive docstring with examples
    5. Include comments explaining the key parts of the algorithm
    """
    
    try:
        # Run the agent task
        result = run_agent_task(prompt)
        
        print("\nTask completed successfully!")
        print(f"View the task at: {result['web_url']}")
        
        # Extract and display the generated code
        code = extract_code_from_response(result["result"])
        print("\nGenerated code:")
        print(code)
        
        # Save the code to a file
        save_code_to_file(code, "binary_search.py")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

