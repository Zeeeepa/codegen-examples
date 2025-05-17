# Codegen Modal Examples

This directory contains examples of Modal applications that integrate with Codegen. Each example demonstrates different aspects of using Codegen with Modal for various use cases.

## What is Modal?

[Modal](https://modal.com) is a cloud platform for running Python functions and applications. It provides a simple way to deploy and scale your code without managing infrastructure. Modal is particularly well-suited for AI and data processing workloads.

## What is Codegen?

[Codegen](https://codegen.com) is a Python SDK for interacting with intelligent code generation agents. It provides tools for code analysis, generation, and manipulation.

## Available Examples

- **[hello_world](./hello_world)**: A simple example that demonstrates basic Modal functionality with Codegen integration.
- **[code_analyzer](./code_analyzer)**: An application that uses Codegen to analyze GitHub repositories and extract code metrics.
- **[linear_webhooks](./linear_webhooks)**: An application that handles Linear webhooks and uses Codegen to analyze GitHub repositories mentioned in Linear issues.

## Prerequisites

Before running these examples, ensure you have:

1. Python 3.10+ installed
2. Modal CLI installed: `pip install modal`
3. Codegen SDK installed: `pip install codegen==0.52.19`
4. A Modal account (sign up at [modal.com](https://modal.com))
5. A Codegen API key (get one at [codegen.sh/token](https://www.codegen.sh/token))

## Using the Deployer Script

The `Deployer.sh` script allows you to interactively select and deploy multiple Modal examples concurrently.

To use it:

1. Make sure the script is executable:
   ```bash
   chmod +x Deployer.sh
   ```

2. Run the script:
   ```bash
   ./Deployer.sh
   ```

3. Select the examples you want to deploy when prompted:
   - Enter the numbers of the examples (space-separated)
   - Or enter 'all' to deploy all examples

4. Confirm your selection

The script will deploy the selected examples concurrently and show the deployment status.

## Manual Deployment

Each example can also be deployed manually by:

1. Navigating to the example directory:
   ```bash
   cd example_name
   ```

2. Running the deploy script:
   ```bash
   ./deploy.sh
   ```

## Additional Resources

- [Modal Documentation](https://modal.com/docs/guide)
- [Codegen Documentation](https://docs.codegen.com)
- [Modal Python SDK](https://github.com/modal-labs/modal-client)
- [Codegen Python SDK](https://github.com/Zeeeepa/codegen)
