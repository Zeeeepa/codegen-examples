# Codebase Analysis Example

[![Documentation](https://img.shields.io/badge/docs-docs.codegen.com-blue)](https://docs.codegen.com)

This example demonstrates how to use the Codegen SDK's `Codebase` class to analyze and manipulate code. The `Codebase` class provides powerful capabilities for parsing, analyzing, and modifying source code in Python and TypeScript projects.

## Overview

The codebase analysis example consists of several components:

1. **Basic Codebase Analysis** (`basic_analysis.py`)
   - Initializes a Codebase instance
   - Explores the structure of a repository
   - Analyzes files, functions, and classes

2. **Code Modification** (`code_modification.py`)
   - Demonstrates how to modify code using the Codebase API
   - Adds new functions and methods
   - Updates existing code

3. **Symbol Analysis** (`symbol_analysis.py`)
   - Analyzes symbols in a codebase
   - Finds function and method usages
   - Explores dependencies between components

## How It Works

The examples demonstrate various capabilities of the Codebase class:

1. **Initialization**
   ```python
   from codegen import Codebase
   
   # Initialize from a local repository
   codebase = Codebase("/path/to/repo")
   
   # Initialize from a GitHub repository
   codebase = Codebase.from_repo(
       repo_full_name="owner/repo",
       tmp_dir="/tmp/codegen",
       access_token="github_token"
   )
   
   # Initialize from a string of code
   codebase = Codebase.from_string(
       code="def add(a, b): return a + b",
       language="python"
   )
   ```

2. **Exploring Files**
   ```python
   # Get all Python files
   python_files = codebase.get_files(extension=".py")
   
   # Get a specific file
   file = codebase.get_file("path/to/file.py")
   
   # Print file content
   print(file.content)
   ```

3. **Analyzing Functions and Classes**
   ```python
   # Get all functions in a file
   functions = file.get_functions()
   
   # Get all classes in the codebase
   classes = codebase.get_classes()
   
   # Analyze a specific function
   function = file.get_function("function_name")
   print(f"Parameters: {function.parameters}")
   print(f"Return type: {function.return_type}")
   ```

4. **Modifying Code**
   ```python
   # Add a new function to a file
   file.add_function(
       name="new_function",
       parameters=["param1", "param2"],
       body="return param1 + param2",
       return_type="int"
   )
   
   # Save changes
   file.save()
   ```

## Setup

1. Install dependencies:
   ```bash
   pip install codegen
   ```

2. Configure GitHub access (if needed):
   ```python
   import os
   os.environ["GITHUB_ACCESS_TOKEN"] = "your_github_token"
   ```

## Usage

Run the examples to see the Codebase API in action:

```bash
python basic_analysis.py
python code_modification.py
python symbol_analysis.py
```

## Output Examples

When analyzing a repository:
```
Repository: example-repo
Total files: 42
Python files: 35
TypeScript files: 7

Top 5 largest files:
1. src/main.py (1250 lines)
2. src/utils.py (850 lines)
3. src/models.py (720 lines)
4. src/api/endpoints.py (650 lines)
5. src/config.py (450 lines)

Function analysis:
- Total functions: 156
- Average parameters per function: 2.7
- Functions with docstrings: 87 (55.8%)
```

## Learn More

- [Codebase API Documentation](https://docs.codegen.com/sdk/codebase)
- [Code Analysis Guide](https://docs.codegen.com/guides/code-analysis)
- [Code Modification Guide](https://docs.codegen.com/guides/code-modification)

## Contributing

Feel free to submit issues and enhancement requests! We welcome contributions to improve the codebase analysis examples.

