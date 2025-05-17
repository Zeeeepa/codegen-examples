# Linear Webhooks Modal Example

This example demonstrates how to deploy a Modal application that handles Linear webhooks and uses Codegen to analyze GitHub repositories mentioned in Linear issues.

## Features

- Handle Linear webhooks securely
- Automatically analyze GitHub repositories mentioned in Linear issues
- Use Codegen to extract code statistics and metrics
- Web endpoint for webhook integration

## Prerequisites

Before you begin, ensure you have the following:
- Python 3.10+
- [Modal CLI](https://modal.com/docs/guide/cli-reference)
- [Codegen SDK](https://docs.codegen.com)
- A Codegen API key (get one at [codegen.sh/token](https://www.codegen.sh/token))
- A Linear account with admin access to create webhooks

## Setup

1. Install the required dependencies:

```bash
pip install modal codegen pydantic
```

2. Authenticate with Modal:

```bash
modal token new
```

3. Create Modal secrets for your Codegen API key:

```bash
modal secret create codegen-api-key --value YOUR_CODEGEN_API_KEY
```

## Deployment

To deploy the application to Modal:

```bash
./deploy.sh
```

The script will check if the required secrets are set up in Modal before deploying.

## Setting Up Linear Webhook

After deploying the application, you need to set up a webhook in Linear:

1. Go to your Linear workspace settings
2. Navigate to "API" > "Webhooks"
3. Create a new webhook with the URL:
   ```
   https://linear-webhooks--linear-webhook-[your-modal-username].modal.run
   ```
4. Select the events you want to trigger the webhook (at least "Issue: created")
5. Copy the webhook secret and add it to Modal secrets:
   ```bash
   modal secret create linear-webhook-secret --value YOUR_LINEAR_WEBHOOK_SECRET
   ```

## Usage

Once deployed and configured, the application will automatically:

1. Receive webhook events from Linear
2. When a new issue is created with a GitHub repository URL in the description
3. Use Codegen to analyze the repository
4. Generate statistics about the codebase

In a real-world application, you would extend this to:
- Add comments to the Linear issue with the analysis results
- Create tasks for code improvements
- Integrate with other tools in your workflow

## Understanding the Code

- `app.py`: Contains the Modal application definition with two main functions:
  - `linear_webhook()`: Web endpoint that receives and verifies Linear webhook events
  - `handle_issue_created()`: Handles issue creation events and analyzes mentioned repositories

## Additional Resources

- [Modal Documentation](https://modal.com/docs/guide)
- [Codegen Documentation](https://docs.codegen.com)
- [Linear API Documentation](https://developers.linear.app/docs/graphql/working-with-the-graphql-api)

