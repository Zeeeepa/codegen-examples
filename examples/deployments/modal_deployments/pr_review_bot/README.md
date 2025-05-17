# PR Review Bot

This example demonstrates how to deploy a Pull Request review bot using Modal and the Codegen API. The bot automatically reviews GitHub pull requests and provides feedback.

## Features

- Automatically review GitHub pull requests
- Analyze code changes for quality, security, and performance issues
- Provide actionable feedback as PR comments
- Support for multiple repositories and organizations

## Prerequisites

- Codegen API token
- Modal account and token
- GitHub App or Personal Access Token with appropriate permissions

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
   export GITHUB_APP_ID=your_github_app_id
   export GITHUB_APP_PRIVATE_KEY=your_github_app_private_key
   # Or for personal access token:
   export GITHUB_TOKEN=your_github_token
   ```

3. Alternatively, create a `.env` file in this directory with the above variables.

## GitHub App Setup (Recommended)

Using a GitHub App is recommended over a personal access token for production deployments:

1. Create a GitHub App at https://github.com/settings/apps/new
2. Set the following permissions:
   - Repository permissions:
     - Contents: Read
     - Pull requests: Read & Write
     - Metadata: Read
   - Subscribe to events:
     - Pull request
     - Pull request review
3. Install the app on your repositories
4. Note your App ID and generate a private key

## Deployment

Run the deployment script:

```bash
./deploy.sh
```

This will deploy the PR review bot to Modal and set up the webhook endpoint.

## Usage

The bot will automatically review pull requests when:

1. A new PR is opened
2. A PR is updated with new commits
3. Someone comments on a PR with `/review`

### Manual Trigger

You can manually trigger a review by commenting on a PR:

```
/review
```

Or with specific focus areas:

```
/review security
/review performance
/review documentation
```

## Configuration

You can customize the bot's behavior by creating a `.codegen-review.yml` file in the root of your repository:

```yaml
# PR Review Bot Configuration
version: 1

# Review settings
review:
  # Focus areas (security, performance, style, documentation)
  focus: 
    - security
    - performance
  
  # Severity levels to report (error, warning, info)
  severity:
    - error
    - warning
  
  # Maximum number of comments to add
  max_comments: 10
  
  # Whether to add a summary comment
  add_summary: true
  
  # Files to ignore (glob patterns)
  ignore:
    - "*.md"
    - "*.json"
    - "tests/**"
    - "docs/**"
```

## Customization

You can customize the bot by modifying the `app.py` file:

- Change the review criteria
- Adjust the comment format
- Add support for additional languages
- Integrate with other services

## Monitoring

Monitor your bot in the Modal dashboard:
- https://modal.com/apps

## Troubleshooting

If you encounter issues:

1. Check your environment variables
2. Verify your GitHub App permissions
3. Check the Modal logs for error messages
4. Ensure your GitHub token or App has the necessary permissions

