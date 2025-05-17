"""
Slack Chatbot
A Modal application that provides a Slack chatbot interface to the Codegen API.
"""

import os
import re
import json
import hmac
import hashlib
import time
import tempfile
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple

import modal
from modal import web_endpoint, Image, Stub, Secret, asgi_app
from fastapi import FastAPI, Request, Response, HTTPException, Depends, Header
from fastapi.responses import JSONResponse
from codegen import Agent

# Define the Modal image with required dependencies
image = Image.debian_slim().pip_install(
    "codegen>=0.52.19",
    "python-dotenv>=1.0.0",
    "fastapi>=0.95.0",
    "slack_sdk>=3.19.0",
    "aiohttp>=3.8.4",
)

# Create a Modal Stub
stub = Stub(
    name="slack-chatbot",
    image=image,
    secrets=[
        Secret.from_name("codegen-secrets"),  # Contains CODEGEN_API_TOKEN
        Secret.from_name("slack-secrets"),    # Contains SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET
    ]
)

# Create a FastAPI app
app = FastAPI()

# Slack verification
def verify_slack_request(
    request: Request,
    x_slack_request_timestamp: str = Header(...),
    x_slack_signature: str = Header(...),
):
    """
    Verify that the request is coming from Slack.
    
    Args:
        request: FastAPI request
        x_slack_request_timestamp: Slack request timestamp
        x_slack_signature: Slack signature
        
    Returns:
        None if valid, raises HTTPException if invalid
    """
    # Check if timestamp is recent
    timestamp = int(x_slack_request_timestamp)
    current_time = int(time.time())
    if abs(current_time - timestamp) > 60 * 5:
        raise HTTPException(status_code=401, detail="Request timestamp is too old")
    
    # Get request body
    body = request.scope.get("body")
    if not body:
        raise HTTPException(status_code=400, detail="Request body is empty")
    
    # Verify signature
    signing_secret = os.environ.get("SLACK_SIGNING_SECRET", "")
    sig_basestring = f"v0:{timestamp}:{body.decode()}"
    my_signature = "v0=" + hmac.new(
        signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(my_signature, x_slack_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

async def send_slack_message(channel: str, text: str, thread_ts: Optional[str] = None):
    """
    Send a message to a Slack channel.
    
    Args:
        channel: Slack channel ID
        text: Message text
        thread_ts: Thread timestamp (for replies)
        
    Returns:
        Response from Slack API
    """
    import aiohttp
    
    bot_token = os.environ.get("SLACK_BOT_TOKEN", "")
    
    headers = {
        "Authorization": f"Bearer {bot_token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    
    payload = {
        "channel": channel,
        "text": text,
    }
    
    if thread_ts:
        payload["thread_ts"] = thread_ts
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://slack.com/api/chat.postMessage",
            headers=headers,
            json=payload,
        ) as response:
            return await response.json()

async def process_message(text: str, user_id: str) -> str:
    """
    Process a message from Slack and generate a response using Codegen.
    
    Args:
        text: Message text
        user_id: Slack user ID
        
    Returns:
        Response text
    """
    # Remove mentions from the text
    text = re.sub(r"<@[A-Z0-9]+>", "", text).strip()
    
    # Check if the message contains a code block
    code_blocks = re.findall(r"```(.*?)```", text, re.DOTALL)
    
    # Initialize Codegen Agent
    agent = Agent(
        token=os.environ.get("CODEGEN_API_TOKEN"),
    )
    
    # Generate a prompt based on the message
    if code_blocks:
        # Extract the code and language
        code = code_blocks[0]
        language = ""
        
        # Check if the code block specifies a language
        first_line = code.split("\n")[0].strip().lower()
        if first_line in ["python", "javascript", "typescript", "java", "c", "cpp", "csharp", "go", "ruby", "php", "swift", "kotlin", "rust"]:
            language = first_line
            code = "\n".join(code.split("\n")[1:])
        
        # Remove the code block from the text
        text_without_code = re.sub(r"```.*?```", "", text, flags=re.DOTALL).strip()
        
        if not text_without_code:
            # If there's no text, assume the user wants an explanation
            text_without_code = "Explain what this code does."
        
        # Generate a prompt for code analysis
        prompt = f"""
        {text_without_code}
        
        ```{language}
        {code}
        ```
        
        Provide a detailed and helpful response. If the user is asking for improvements or explanations,
        be specific and provide examples. If the code has issues, explain them clearly and suggest fixes.
        """
    else:
        # Generate a prompt for general questions
        prompt = f"""
        {text}
        
        Provide a detailed and helpful response. If the user is asking for code examples,
        include them with proper formatting. If the user is asking for explanations,
        be clear and concise.
        """
    
    # Run the agent
    response = agent.run(prompt)
    
    # Format the response for Slack
    response = response.replace("```", "```\n")
    
    return response

@app.post("/slack/events")
async def slack_events(request: Request):
    """
    Handle Slack events.
    """
    # Get the request body
    body = await request.body()
    payload = json.loads(body)
    
    # Handle URL verification
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge")}
    
    # Verify the request
    verify_slack_request(request)
    
    # Handle events
    event = payload.get("event", {})
    event_type = event.get("type")
    
    if event_type == "message":
        # Ignore bot messages
        if event.get("bot_id"):
            return {"status": "ignored", "reason": "bot message"}
        
        # Get message details
        channel = event.get("channel")
        user = event.get("user")
        text = event.get("text", "")
        thread_ts = event.get("thread_ts", event.get("ts"))
        
        # Check if this is a direct message or the bot was mentioned
        is_dm = channel and channel.startswith("D")
        
        if is_dm:
            # Send a typing indicator
            await send_slack_message(channel, "Thinking...", thread_ts)
            
            # Process the message
            response = await process_message(text, user)
            
            # Send the response
            await send_slack_message(channel, response, thread_ts)
    
    elif event_type == "app_mention":
        # Get message details
        channel = event.get("channel")
        user = event.get("user")
        text = event.get("text", "")
        thread_ts = event.get("thread_ts", event.get("ts"))
        
        # Send a typing indicator
        await send_slack_message(channel, "Thinking...", thread_ts)
        
        # Process the message
        response = await process_message(text, user)
        
        # Send the response
        await send_slack_message(channel, response, thread_ts)
    
    return {"status": "ok"}

@app.post("/slack/commands")
async def slack_commands(request: Request):
    """
    Handle Slack slash commands.
    """
    # Get the request body
    body = await request.body()
    form_data = urllib.parse.parse_qs(body.decode())
    
    # Verify the request
    verify_slack_request(request)
    
    # Get command details
    command = form_data.get("command", [""])[0]
    text = form_data.get("text", [""])[0]
    channel_id = form_data.get("channel_id", [""])[0]
    user_id = form_data.get("user_id", [""])[0]
    
    if command == "/codegen":
        # Parse the command
        parts = text.split(" ", 1)
        subcommand = parts[0].lower() if parts else ""
        subtext = parts[1] if len(parts) > 1 else ""
        
        if subcommand == "help" or not subcommand:
            # Show help information
            help_text = """
*Codegen Slack Bot Help*

Use the following commands:

• `/codegen analyze [code]` - Analyze a code snippet
• `/codegen generate [description]` - Generate code based on a description
• `/codegen explain [code]` - Explain what a code snippet does
• `/codegen help` - Show this help information

You can also interact with the bot by:
• Sending a direct message
• Mentioning the bot in a channel (@CodegenBot)
• Sharing a code snippet with the bot
            """
            
            return {"text": help_text}
        
        elif subcommand in ["analyze", "generate", "explain"]:
            # Process the command
            if not subtext:
                return {"text": f"Please provide text for the {subcommand} command."}
            
            # Create a prompt based on the command
            if subcommand == "analyze":
                prompt = f"Analyze this code and provide feedback:\n\n```\n{subtext}\n```"
            elif subcommand == "generate":
                prompt = f"Generate code for: {subtext}"
            elif subcommand == "explain":
                prompt = f"Explain what this code does:\n\n```\n{subtext}\n```"
            
            # Process the message
            response = await process_message(prompt, user_id)
            
            return {"text": response}
        
        else:
            # Unknown subcommand
            return {"text": f"Unknown command: {subcommand}. Try `/codegen help` for available commands."}
    
    return {"text": "Unknown command."}

@stub.function
@asgi_app()
def fastapi_app():
    """
    Serve the FastAPI application.
    """
    return app

if __name__ == "__main__":
    # This will be executed when running the script locally
    stub.deploy("slack-chatbot")
    print("Slack Chatbot deployed successfully!")

