# Custom Functions Example

[![Documentation](https://img.shields.io/badge/docs-docs.codegen.com-blue)](https://docs.codegen.com)

This example demonstrates how to use the Codegen SDK's `function` decorator to create custom functions that can be deployed and run in the Codegen environment. It also shows how to use the `CodegenApp` class to create event-driven applications that respond to GitHub, Slack, and Linear events.

## Overview

The custom functions example consists of several components:

1. **Basic Function Definition** (`basic_function.py`)
   - Defines a simple function using the `@function` decorator
   - Shows how to access the codebase within the function
   - Demonstrates function deployment

2. **Event-Driven App** (`event_app.py`)
   - Creates a `CodegenApp` instance
   - Configures handlers for GitHub, Slack, and Linear events
   - Shows how to process and respond to events

3. **Webhook Functions** (`webhook_functions.py`)
   - Defines functions that respond to webhook events
   - Shows how to handle PR creation, issue updates, and more
   - Demonstrates integration with external services

## How It Works

The examples demonstrate various capabilities of the function decorator and CodegenApp:

1. **Function Definition**
   ```python
   from codegen import function, Codebase
   
   @function('analyze-code')
   def analyze_code(codebase: Codebase):
       """Analyze code in a repository."""
       # Get all Python files
       python_files = codebase.get_files(extension=".py")
       
       # Count lines of code
       total_lines = sum(len(file.content.splitlines()) for file in python_files)
       
       return {
           "total_files": len(python_files),
           "total_lines": total_lines
       }
   ```

2. **CodegenApp Setup**
   ```python
   from codegen import CodegenApp
   
   # Create a CodegenApp instance
   app = CodegenApp(name="my-app", repo="owner/repo")
   
   # Parse the repository
   app.parse_repo()
   
   # Run the app
   app.run(host="0.0.0.0", port=8000)
   ```

3. **Event Handling**
   ```python
   @app.github.on("pull_request.created")
   async def handle_pr_created(payload):
       """Handle PR creation events."""
       pr_number = payload["pull_request"]["number"]
       repo_name = payload["repository"]["full_name"]
       
       # Get the codebase
       codebase = app.get_codebase()
       
       # Analyze the PR
       # ...
       
       # Add a comment to the PR
       codebase.create_pr_comment(pr_number, "PR analysis completed!")
   ```

## Setup

1. Install dependencies:
   ```bash
   pip install codegen
   ```

2. Configure API access:
   ```python
   import os
   os.environ["GITHUB_ACCESS_TOKEN"] = "your_github_token"
   os.environ["CODEGEN_API_TOKEN"] = "your_api_token"
   ```

3. Get your Codegen API token from [codegen.sh/token](https://www.codegen.sh/token)

## Usage

Run the examples to see the function decorator and CodegenApp in action:

```bash
# Run a basic function
python basic_function.py

# Start the event-driven app
python event_app.py

# Test webhook functions
python webhook_functions.py
```

## Deployment

To deploy your custom functions to the Codegen platform:

```bash
# Deploy a function
codegen deploy function analyze-code

# Deploy all functions in a directory
codegen deploy directory ./functions
```

## Example Output

When running a custom function:
```
Function: analyze-code
Repository: owner/repo
Analysis results:
- Total Python files: 42
- Total lines of code: 5,280
- Average lines per file: 125.7
```

## Learn More

- [Function API Documentation](https://docs.codegen.com/sdk/function)
- [CodegenApp Documentation](https://docs.codegen.com/sdk/codegenapp)
- [Webhook Integration Guide](https://docs.codegen.com/guides/webhooks)

## Contributing

Feel free to submit issues and enhancement requests! We welcome contributions to improve the custom functions examples.

