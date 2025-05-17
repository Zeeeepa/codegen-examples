# Code Analysis Service

This example demonstrates how to deploy a code analysis service using Modal and the Codegen API. The service provides an HTTP endpoint that analyzes GitHub repositories and returns insights about the codebase.

## Features

- Analyze GitHub repositories by URL
- Generate code quality metrics
- Identify potential issues and improvements
- Provide actionable recommendations

## Prerequisites

- Codegen API token
- Modal account and token
- GitHub personal access token (for private repositories)

## Setup

1. Install the required packages:
   ```bash
   pip install modal codegen python-dotenv
   ```

2. Set up your environment variables:
   ```bash
   export CODEGEN_API_TOKEN=your_codegen_token
   export MODAL_TOKEN_ID=your_modal_token_id
   export MODAL_TOKEN_SECRET=your_modal_token_secret
   export GITHUB_TOKEN=your_github_token  # Optional, for private repos
   ```

3. Alternatively, create a `.env` file in this directory:
   ```
   CODEGEN_API_TOKEN=your_codegen_token
   MODAL_TOKEN_ID=your_modal_token_id
   MODAL_TOKEN_SECRET=your_modal_token_secret
   GITHUB_TOKEN=your_github_token  # Optional, for private repos
   ```

## Deployment

Run the deployment script:

```bash
./deploy.sh
```

This will deploy the service to Modal and provide you with a URL for accessing it.

## Usage

Once deployed, you can use the service by sending a POST request to the provided URL:

```bash
curl -X POST https://your-modal-app-url.modal.run/analyze \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/username/repo", "analysis_type": "full"}'
```

### Request Parameters

- `repo_url` (required): URL of the GitHub repository to analyze
- `analysis_type` (optional): Type of analysis to perform (default: "basic")
  - "basic": Quick analysis of the repository structure
  - "full": Comprehensive analysis including code quality metrics
  - "security": Focus on security issues
  - "performance": Focus on performance issues

### Response Format

The service returns a JSON response with the analysis results:

```json
{
  "repo": "username/repo",
  "analysis_type": "full",
  "timestamp": "2023-05-17T13:45:30Z",
  "summary": {
    "files": 120,
    "lines_of_code": 15000,
    "languages": {
      "Python": 70,
      "JavaScript": 30,
      "Other": 20
    }
  },
  "metrics": {
    "complexity": 3.5,
    "maintainability": 4.2,
    "test_coverage": 0.75
  },
  "issues": [
    {
      "type": "security",
      "severity": "high",
      "description": "Potential SQL injection in user_controller.py",
      "file": "app/controllers/user_controller.py",
      "line": 42
    }
  ],
  "recommendations": [
    "Add input validation to prevent SQL injection",
    "Increase test coverage for authentication module",
    "Consider refactoring the user_controller.py file to reduce complexity"
  ]
}
```

## Customization

You can customize the service by modifying the `app.py` file:

- Add new analysis types
- Change the metrics calculation
- Integrate with other services
- Add authentication

## Monitoring

Monitor your service in the Modal dashboard:
- https://modal.com/apps

## Troubleshooting

If you encounter issues:

1. Check your environment variables
2. Verify your Modal and Codegen tokens
3. Check the Modal logs for error messages
4. Ensure your GitHub token has the necessary permissions

