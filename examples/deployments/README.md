# Codegen Deployment Examples

This directory contains examples of deploying Codegen-powered applications to various platforms.

## Available Deployment Examples

1. **Modal Deployments** - Examples of deploying Codegen applications using Modal, a serverless compute platform
   - Code analysis service
   - PR review bot
   - Documentation generator
   - Slack chatbot integration

## Getting Started

Each subdirectory contains:
- A README with detailed setup instructions
- Deployment scripts
- Example code
- Configuration templates

## Prerequisites

- Codegen API token (get one at [codegen.sh/token](https://www.codegen.sh/token))
- Appropriate platform credentials (e.g., Modal token)
- Python 3.10+

## Deployment Options

Codegen applications can be deployed in various ways:

1. **Serverless** - Deploy as serverless functions (Modal, AWS Lambda, etc.)
2. **Container-based** - Deploy as Docker containers (Kubernetes, ECS, etc.)
3. **Self-hosted** - Run on your own infrastructure

The examples in this directory focus on serverless deployments using Modal, which offers an excellent balance of simplicity, scalability, and cost-effectiveness.

