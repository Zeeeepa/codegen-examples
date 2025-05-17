# Hello World Modal Example

This is a simple example that demonstrates how to deploy a basic Modal application that integrates with Codegen.

## Features

- Basic Modal function deployment
- Web endpoint for API access
- Scheduled function that runs every hour
- Integration with Codegen SDK

## Prerequisites

Before you begin, ensure you have the following installed:
- Python 3.10+
- [Modal CLI](https://modal.com/docs/guide/cli-reference)
- [Codegen SDK](https://docs.codegen.com)

## Setup

1. Install the required dependencies:

```bash
pip install modal codegen
```

2. Authenticate with Modal:

```bash
modal token new
```

## Running Locally

To run the application locally:

```bash
modal run app.py
```

This will execute the function defined in the `if __name__ == "__main__"` block.

## Deployment

To deploy the application to Modal:

```bash
./deploy.sh
```

Or manually:

```bash
modal deploy app.py
```

## Usage

Once deployed, you can:

1. Access the web endpoint at: `https://hello-world--web-hello-[your-modal-username].modal.run`
2. The scheduled function will run automatically every hour
3. You can invoke the function programmatically:

```python
import modal

app = modal.App("hello-world")
f = app.function.lookup("hello")
result = f.remote("your name")
print(result)
```

## Understanding the Code

- `app.py`: Contains the Modal application definition with three functions:
  - `hello()`: A basic function that returns a greeting
  - `web_hello()`: A web endpoint that returns a JSON greeting
  - `scheduled_hello()`: A function that runs on a schedule

## Additional Resources

- [Modal Documentation](https://modal.com/docs/guide)
- [Codegen Documentation](https://docs.codegen.com)

