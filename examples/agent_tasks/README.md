# Agent Tasks Example

[![Documentation](https://img.shields.io/badge/docs-docs.codegen.com-blue)](https://docs.codegen.com)

This example demonstrates how to use the Codegen SDK's `Agent` class to create and run AI-powered agents for various code-related tasks. The `Agent` class provides a simple interface to interact with Codegen's AI capabilities.

## Overview

The agent tasks example consists of several components:

1. **Basic Agent Usage** (`basic_agent.py`)
   - Initializes an Agent instance
   - Runs a simple code generation task
   - Handles the response

2. **Code Review Agent** (`code_review_agent.py`)
   - Creates an agent for reviewing code
   - Provides code snippets for review
   - Processes review feedback

3. **Documentation Generator** (`documentation_generator.py`)
   - Uses an agent to generate documentation for code
   - Extracts docstrings and comments
   - Formats documentation in Markdown

## How It Works

The examples demonstrate various capabilities of the Agent class:

1. **Initialization**
   ```python
   from codegen import Agent
   
   # Initialize with API token
   agent = Agent(token="your_api_token", org_id=1)
   ```

2. **Running Tasks**
   ```python
   # Run a simple task
   task = agent.run("Generate a Python function to calculate Fibonacci numbers")
   
   # Get the task status
   status = agent.get_status()
   print(f"Task status: {status['status']}")
   
   # Access the result
   if status and status["status"] == "completed":
       print(f"Result: {status['result']}")
   ```

3. **Handling Responses**
   ```python
   # Extract code from the response
   if status and status["status"] == "completed":
       result = status["result"]
       # Process the result
       if "```python" in result:
           code = result.split("```python")[1].split("```")[0].strip()
           print("Generated code:")
           print(code)
   ```

## Setup

1. Install dependencies:
   ```bash
   pip install codegen
   ```

2. Configure API access:
   ```python
   import os
   os.environ["CODEGEN_API_TOKEN"] = "your_api_token"
   ```

3. Get your Codegen API token from [codegen.sh/token](https://www.codegen.sh/token)

## Usage

Run the examples to see the Agent API in action:

```bash
python basic_agent.py
python code_review_agent.py "path/to/code/file.py"
python documentation_generator.py "path/to/code/file.py"
```

## Example Output

When running a code generation task:
```
Task started: 12345
Task status: running
Task status: completed
Generated code:
def fibonacci(n):
    """Calculate the nth Fibonacci number.
    
    Args:
        n: The position in the Fibonacci sequence (0-indexed)
        
    Returns:
        The nth Fibonacci number
    """
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fibonacci(n-1) + fibonacci(n-2)
```

## Learn More

- [Agent API Documentation](https://docs.codegen.com/sdk/agent)
- [Prompt Engineering Guide](https://docs.codegen.com/guides/prompting)
- [Advanced Agent Usage](https://docs.codegen.com/guides/advanced-agents)

## Contributing

Feel free to submit issues and enhancement requests! We welcome contributions to improve the agent tasks examples.

