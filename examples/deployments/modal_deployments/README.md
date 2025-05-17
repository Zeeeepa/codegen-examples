# Modal Deployments for Codegen Applications

This directory contains examples of deploying Codegen applications using [Modal](https://modal.com), a serverless compute platform that makes it easy to run Python code in the cloud.

## Why Modal?

Modal is an excellent choice for deploying Codegen applications because:

1. **Serverless** - No infrastructure to manage
2. **Scalable** - Automatically scales based on demand
3. **Cost-effective** - Pay only for what you use
4. **Python-native** - Designed specifically for Python applications
5. **GPU support** - Easy access to GPUs for AI workloads

## Prerequisites

Before you can deploy these examples, you'll need:

1. A Codegen API token (get one at [codegen.sh/token](https://www.codegen.sh/token))
2. A Modal account and token (sign up at [modal.com](https://modal.com))
3. Python 3.10+

## Setup

1. Install the required packages:
   ```bash
   pip install modal codegen
   ```

2. Set up your environment variables:
   ```bash
   export CODEGEN_API_TOKEN=your_codegen_token
   export MODAL_TOKEN_ID=your_modal_token_id
   export MODAL_TOKEN_SECRET=your_modal_token_secret
   ```

3. Alternatively, create a `.env` file in your project directory:
   ```
   CODEGEN_API_TOKEN=your_codegen_token
   MODAL_TOKEN_ID=your_modal_token_id
   MODAL_TOKEN_SECRET=your_modal_token_secret
   ```

## Available Examples

Each example includes:
- A README with specific setup instructions
- A deployment script (`deploy.sh`)
- The Modal application code
- Any necessary configuration files

### Examples:

1. **Code Analysis Service** - A web service that analyzes GitHub repositories
2. **PR Review Bot** - A bot that automatically reviews pull requests
3. **Documentation Generator** - A service that generates documentation for code
4. **Slack Chatbot** - A Slack bot powered by Codegen

## Deploying an Example

To deploy an example, navigate to its directory and run the deployment script:

```bash
cd code_analysis_service
./deploy.sh
```

## Deployment Script

Each example includes a `deploy.sh` script that:

1. Validates your environment setup
2. Installs any required dependencies
3. Deploys the application to Modal
4. Provides the URL or endpoint for accessing the deployed application

## Common Patterns

These examples demonstrate common patterns for Modal deployments:

1. **Web Endpoints** - HTTP endpoints for web services
2. **Scheduled Jobs** - Periodic tasks that run on a schedule
3. **Event Triggers** - Functions that respond to events (webhooks)
4. **Asynchronous Processing** - Background processing of tasks

## Customizing Deployments

You can customize these examples by:

1. Modifying the Modal application code
2. Adjusting the deployment configuration
3. Adding your own business logic
4. Integrating with other services

## Monitoring and Logs

Once deployed, you can monitor your applications in the Modal dashboard:
- https://modal.com/apps

## Additional Resources

- [Modal Documentation](https://modal.com/docs)
- [Codegen Documentation](https://docs.codegen.com)
- [Modal Python SDK](https://github.com/modal-labs/modal-client)
- [Codegen Python SDK](https://github.com/Zeeeepa/codegen)

