# Slack Chatbot

This example demonstrates how to deploy a Slack chatbot using Modal and the Codegen API. The chatbot allows users to interact with Codegen directly from Slack.

## Features

- Interact with Codegen directly from Slack
- Analyze code snippets
- Answer programming questions
- Generate code samples
- Explain code functionality

## Prerequisites

- Codegen API token
- Modal account and token
- Slack Bot Token and Signing Secret

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
   export SLACK_BOT_TOKEN=your_slack_bot_token
   export SLACK_SIGNING_SECRET=your_slack_signing_secret
   ```

3. Alternatively, create a `.env` file in this directory with the above variables.

## Slack App Setup

1. Create a new Slack App at https://api.slack.com/apps
2. Under "OAuth & Permissions", add the following scopes:
   - `app_mentions:read`
   - `chat:write`
   - `files:read`
   - `im:history`
   - `im:read`
   - `im:write`
3. Install the app to your workspace
4. Note your Bot Token and Signing Secret

## Deployment

Run the deployment script:

```bash
./deploy.sh
```

This will deploy the Slack chatbot to Modal and set up the webhook endpoint.

## Usage

Once deployed, you can interact with the chatbot in several ways:

### Direct Messages

Simply send a message to the bot in a direct message:

```
How do I implement a binary search in Python?
```

### Mentions in Channels

Mention the bot in a channel:

```
@CodegenBot How do I implement a binary search in Python?
```

### Code Analysis

Share a code snippet with the bot:

````
Can you explain what this code does?

```python
def mystery_function(arr):
    if not arr:
        return []
    pivot = arr[0]
    left = [x for x in arr[1:] if x < pivot]
    right = [x for x in arr[1:] if x >= pivot]
    return mystery_function(left) + [pivot] + mystery_function(right)
```
````

### File Sharing

Upload a file to the bot in a direct message and ask a question about it:

```
What does this code do?
[file.py]
```

## Commands

The bot supports several commands:

- `/codegen help` - Show help information
- `/codegen analyze [code]` - Analyze a code snippet
- `/codegen generate [description]` - Generate code based on a description
- `/codegen explain [code]` - Explain what a code snippet does

## Customization

You can customize the bot by modifying the `app.py` file:

- Add new commands
- Change the response format
- Integrate with other services
- Add support for additional languages

## Monitoring

Monitor your bot in the Modal dashboard:
- https://modal.com/apps

## Troubleshooting

If you encounter issues:

1. Check your environment variables
2. Verify your Slack Bot Token and Signing Secret
3. Check the Modal logs for error messages
4. Ensure your Slack app has the necessary permissions

