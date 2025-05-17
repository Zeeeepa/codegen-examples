#!/usr/bin/env python
"""
Documentation Generator Example

This script demonstrates how to use the Codegen SDK's Agent class to create an
AI-powered documentation generator that can analyze code and generate comprehensive
documentation in Markdown format.
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


def generate_documentation_prompt(code: str, file_path: str) -> str:
    """Generate a prompt for the documentation generator agent.

    Args:
        code: The code to document.
        file_path: Path to the code file.

    Returns:
        A prompt string for the agent.
    """
    # Determine language from file extension
    ext = os.path.splitext(file_path)[1].lower()
    language = "Unknown"
    
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
    
    filename = os.path.basename(file_path)
    
    return f"""
    Please generate comprehensive documentation for the following {language} code file: {filename}
    
    The documentation should include:
    
    1. A high-level overview of the file's purpose and functionality
    2. Detailed documentation for each class, function, and method, including:
       - Description of what it does
       - Parameters and their types
       - Return values and their types
       - Exceptions that might be raised
       - Usage examples where appropriate
    3. Explanation of any complex algorithms or logic
    4. Dependencies and requirements
    5. Any potential issues, limitations, or areas for improvement
    
    Format the documentation as Markdown with proper headings, code blocks, and formatting.
    
    Here is the code to document:
    
    ```{language.lower()}
    {code}
    ```
    
    Please ensure the documentation is clear, comprehensive, and follows best practices for {language} documentation.
    """


def run_documentation_generator(code: str, file_path: str, token: Optional[str] = None, org_id: int = 1) -> Dict:
    """Run a documentation generator using the Codegen Agent.

    Args:
        code: The code to document.
        file_path: Path to the code file.
        token: API authentication token. If not provided, will use environment variable.
        org_id: Organization ID (default: 1).

    Returns:
        Dictionary containing the documentation result and status.
    """
    # Use environment variable if token not provided
    api_token = token or os.environ.get("CODEGEN_API_TOKEN")
    if not api_token:
        raise ValueError("API token is required. Provide it as an argument or set CODEGEN_API_TOKEN environment variable.")
    
    # Generate the documentation prompt
    prompt = generate_documentation_prompt(code, file_path)
    
    # Initialize the Agent
    agent = Agent(token=api_token, org_id=org_id)
    
    # Run the task
    task = agent.run(prompt)
    print(f"Documentation generation started: {task.id}")
    
    # Poll for task completion
    max_attempts = 30
    attempts = 0
    
    while attempts < max_attempts:
        status = agent.get_status()
        print(f"Generation status: {status['status']}")
        
        if status["status"] == "completed":
            return {
                "id": status["id"],
                "status": status["status"],
                "result": status["result"],
                "web_url": status["web_url"]
            }
        
        if status["status"] == "failed":
            raise Exception(f"Documentation generation failed: {status.get('result', 'No error message provided')}")
        
        # Wait before checking again
        time.sleep(2)
        attempts += 1
    
    raise TimeoutError("Documentation generation did not complete within the expected time.")


def save_documentation_to_file(documentation: str, file_path: str) -> str:
    """Save the generated documentation to a Markdown file.

    Args:
        documentation: The documentation text.
        file_path: Path to the original code file.

    Returns:
        Path to the saved documentation file.
    """
    # Create the documentation filename
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    doc_filename = f"{base_name}_documentation.md"
    
    # Save the documentation
    with open(doc_filename, "w") as f:
        f.write(documentation)
    
    print(f"Documentation saved to {doc_filename}")
    return doc_filename


def main():
    """Main function to run the example."""
    if len(sys.argv) < 2:
        print("Usage: python documentation_generator.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    try:
        # Read the code file
        code = read_code_file(file_path)
        
        # Run the documentation generator
        result = run_documentation_generator(code, file_path)
        
        print("\nDocumentation generation completed successfully!")
        print(f"View the task at: {result['web_url']}")
        
        # Save the documentation to a file
        doc_file = save_documentation_to_file(result["result"], file_path)
        
        print(f"\nDocumentation has been generated and saved to {doc_file}")
        print("You can open this file in a Markdown viewer or editor to see the formatted documentation.")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

