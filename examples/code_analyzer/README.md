# Code Analyzer Modal Example

This example demonstrates how to deploy a Modal application that uses Codegen to analyze GitHub repositories.

## Features

- Analyze GitHub repositories using Codegen
- Extract code statistics and metrics
- Identify complex functions and classes
- Web endpoint for API access

## Prerequisites

Before you begin, ensure you have the following installed:
- Python 3.10+
- [Modal CLI](https://modal.com/docs/guide/cli-reference)
- [Codegen SDK](https://docs.codegen.com)
- A Codegen API key (get one at [codegen.sh/token](https://www.codegen.sh/token))

## Setup

1. Install the required dependencies:

```bash
pip install modal codegen gitpython pydantic
```

2. Authenticate with Modal:

```bash
modal token new
```

3. Set your Codegen API key as an environment variable:

```bash
export CODEGEN_API_KEY=your_api_key_here
```

## Running Locally

To run the application locally:

```bash
modal run app.py
```

This will analyze the Modal repository as an example.

## Deployment

To deploy the application to Modal:

```bash
./deploy.sh
```

The script will automatically insert your Codegen API key from the environment variable.

## Usage

Once deployed, you can use the web endpoint to analyze GitHub repositories:

```bash
curl -X POST "https://code-analyzer--analyze-github-repo-[your-modal-username].modal.run" \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/username/repo.git", "branch": "main"}'
```

The response will include:
- Basic repository statistics
- Most complex functions
- Most complex classes

## Understanding the Code

- `app.py`: Contains the Modal application definition with three functions:
  - `clone_repo()`: Clones a GitHub repository to a temporary directory
  - `analyze_repo()`: Analyzes a repository using Codegen
  - `analyze_github_repo()`: Web endpoint that combines the above functions

## Additional Resources

- [Modal Documentation](https://modal.com/docs/guide)
- [Codegen Documentation](https://docs.codegen.com)
- [GitPython Documentation](https://gitpython.readthedocs.io/)

