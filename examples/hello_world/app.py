"""
A simple Modal hello world example that demonstrates basic Modal functionality.
"""

import modal

# Define the Modal app
app = modal.App("hello-world")

# Create an image with Python dependencies
image = modal.Image.debian_slim().pip_install(["codegen==0.52.19"])

# Define a function that will run on Modal
@app.function(image=image)
def hello(name: str = "world"):
    """Say hello to someone."""
    print(f"Hello, {name}!")
    return f"Hello, {name}!"

# Define a web endpoint
@app.function(image=image, keep_warm=1)
@modal.web_endpoint(method="GET")
def web_hello(name: str = "world"):
    """Web endpoint that says hello to someone."""
    return {"message": f"Hello, {name}!"}

# Define a scheduled function that runs every hour
@app.function(image=image)
@modal.schedule(rate="1 hour")
def scheduled_hello():
    """Say hello every hour."""
    print("Hello, it's time for a scheduled greeting!")
    return "Hello, it's time for a scheduled greeting!"

if __name__ == "__main__":
    # This block is executed when running the script directly
    with app.run():
        # Call the function locally
        result = hello.remote("Modal")
        print(f"Result from remote function: {result}")

