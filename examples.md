# Codegen SDK Examples

This document provides an overview of the examples available in the [codegen-examples](https://github.com/Zeeeepa/codegen-examples) repository. These examples demonstrate how to use the Codegen SDK for various code generation and analysis tasks.

## Available Examples

### 1. Agent Tasks

The [agent_tasks](examples/agent_tasks) directory contains examples of using the `Agent` class to create and run AI-powered agents:

- [basic_agent.py](examples/agent_tasks/basic_agent.py): Demonstrates how to initialize an Agent and run a simple code generation task.
- [code_review_agent.py](examples/agent_tasks/code_review_agent.py): Shows how to create an agent for reviewing code and providing feedback.
- [documentation_generator.py](examples/agent_tasks/documentation_generator.py): Uses an agent to generate documentation for code files.

### 2. Codebase Analysis

The [codebase_analysis](examples/codebase_analysis) directory contains examples of using the `Codebase` class to analyze and manipulate code:

- [basic_analysis.py](examples/codebase_analysis/basic_analysis.py): Shows how to initialize a Codebase and explore its structure.
- [code_modification.py](examples/codebase_analysis/code_modification.py): Demonstrates how to modify code using the Codebase API.
- [symbol_analysis.py](examples/codebase_analysis/symbol_analysis.py): Shows how to analyze symbols in a codebase and find usages.

### 3. Custom Functions

The [custom_functions](examples/custom_functions) directory contains examples of using the `function` decorator and `CodegenApp` class:

- [basic_function.py](examples/custom_functions/basic_function.py): Demonstrates how to define custom functions using the `@function` decorator.
- [event_app.py](examples/custom_functions/event_app.py): Shows how to create an event-driven application using the `CodegenApp` class.
- [webhook_functions.py](examples/custom_functions/webhook_functions.py): Demonstrates how to create webhook functions that respond to events.

### 4. Codecov Agent Trigger

The [codecov_agent_trigger](examples/codecov_agent_trigger) directory contains an example of integrating Codegen with Codecov:

- [process_coverage_report.py](examples/codecov_agent_trigger/process_coverage_report.py): Shows how to trigger a Codegen agent when code coverage falls below a threshold.
- [generate_codecov_agent_prompt.py](examples/codecov_agent_trigger/generate_codecov_agent_prompt.py): Demonstrates how to generate prompts for the Codegen agent.

## Getting Started

To run these examples, you'll need to:

1. Install the Codegen SDK:
   ```bash
   pip install codegen
   ```

2. Get your Codegen API token from [codegen.sh/token](https://www.codegen.sh/token)

3. Set up your environment:
   ```bash
   export CODEGEN_API_TOKEN=your_api_token
   ```

4. Run an example:
   ```bash
   python examples/agent_tasks/basic_agent.py
   ```

## Example Usage Patterns

### Running an Agent

```python
from codegen import Agent

# Initialize the Agent
agent = Agent(token="your_api_token", org_id=1)

# Run a task
task = agent.run("Generate a Python function to calculate Fibonacci numbers")

# Get the task status
status = agent.get_status()
print(f"Task status: {status['status']}")

# Access the result
if status and status["status"] == "completed":
    print(f"Result: {status['result']}")
```

### Analyzing a Codebase

```python
from codegen import Codebase

# Initialize the Codebase
codebase = Codebase("/path/to/repo")

# Get all Python files
python_files = codebase.get_files(extension=".py")

# Analyze functions
for file in python_files:
    functions = file.get_functions()
    for func in functions:
        print(f"Function: {func.name}")
        print(f"Parameters: {[p.name for p in func.parameters]}")
        print(f"Return type: {func.return_type}")
        print(f"Has docstring: {bool(func.docstring)}")
```

### Creating a Custom Function

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

### Creating an Event-Driven App

```python
from codegen import CodegenApp

# Create a CodegenApp instance
app = CodegenApp(name="my-app", repo="owner/repo")

# Register a GitHub event handler
@app.github.on("pull_request.opened")
async def on_pr_created(payload):
    pr_number = payload["pull_request"]["number"]
    codebase = app.get_codebase()
    codebase.create_pr_comment(pr_number, "Thanks for your contribution!")

# Run the app
app.run(host="0.0.0.0", port=8000)
```

## Contributing

Have a useful example to share? We'd love to include it! Please see our [Contributing Guide](CONTRIBUTING.md) for instructions.

