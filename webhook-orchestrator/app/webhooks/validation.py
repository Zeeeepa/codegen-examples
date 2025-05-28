"""
Webhook payload validation and security.
"""
import hashlib
import hmac
import time
from typing import Dict, Any, Optional
from fastapi import HTTPException, Request
from pydantic import BaseModel, Field, validator

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


class WebhookHeaders(BaseModel):
    """GitHub webhook headers validation."""
    x_github_delivery: str = Field(..., alias="x-github-delivery")
    x_github_event: str = Field(..., alias="x-github-event")
    x_github_hook_id: Optional[str] = Field(None, alias="x-github-hook-id")
    x_github_hook_installation_target_id: Optional[str] = Field(None, alias="x-github-hook-installation-target-id")
    x_github_hook_installation_target_type: Optional[str] = Field(None, alias="x-github-hook-installation-target-type")
    x_hub_signature_256: Optional[str] = Field(None, alias="x-hub-signature-256")
    user_agent: Optional[str] = Field(None, alias="user-agent")
    content_type: str = Field(..., alias="content-type")
    
    @validator("x_github_event")
    def validate_event_type(cls, v):
        """Validate GitHub event type."""
        allowed_events = {
            "pull_request",
            "push",
            "check_run",
            "check_suite",
            "status",
            "workflow_run",
            "repository",
            "installation",
            "installation_repositories",
            "ping",
        }
        if v not in allowed_events:
            logger.warning(f"Received unsupported event type: {v}")
        return v
    
    @validator("content_type")
    def validate_content_type(cls, v):
        """Validate content type."""
        if v != "application/json":
            raise ValueError("Content-Type must be application/json")
        return v


class GitHubWebhookPayload(BaseModel):
    """Base GitHub webhook payload."""
    action: Optional[str] = None
    number: Optional[int] = None
    repository: Optional[Dict[str, Any]] = None
    sender: Optional[Dict[str, Any]] = None
    installation: Optional[Dict[str, Any]] = None
    
    class Config:
        extra = "allow"  # Allow additional fields


class PullRequestPayload(GitHubWebhookPayload):
    """Pull request webhook payload."""
    pull_request: Dict[str, Any]
    
    @validator("pull_request")
    def validate_pull_request(cls, v):
        """Validate pull request data."""
        required_fields = ["id", "number", "state", "head", "base"]
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Missing required field in pull_request: {field}")
        return v


class CheckRunPayload(GitHubWebhookPayload):
    """Check run webhook payload."""
    check_run: Dict[str, Any]
    
    @validator("check_run")
    def validate_check_run(cls, v):
        """Validate check run data."""
        required_fields = ["id", "status", "conclusion", "pull_requests"]
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Missing required field in check_run: {field}")
        return v


class CheckSuitePayload(GitHubWebhookPayload):
    """Check suite webhook payload."""
    check_suite: Dict[str, Any]
    
    @validator("check_suite")
    def validate_check_suite(cls, v):
        """Validate check suite data."""
        required_fields = ["id", "status", "conclusion", "pull_requests"]
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Missing required field in check_suite: {field}")
        return v


class WebhookValidator:
    """Webhook validation and security handler."""
    
    def __init__(self):
        self.secret = settings.github_webhook_secret.encode()
        self.replay_window = 300  # 5 minutes
        self.processed_deliveries = set()  # In production, use Redis
    
    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify GitHub webhook signature."""
        if not signature:
            logger.warning("Missing webhook signature")
            return False
        
        if not signature.startswith("sha256="):
            logger.warning("Invalid signature format")
            return False
        
        expected_signature = hmac.new(
            self.secret,
            payload,
            hashlib.sha256
        ).hexdigest()
        
        received_signature = signature[7:]  # Remove 'sha256=' prefix
        
        if not hmac.compare_digest(expected_signature, received_signature):
            logger.warning("Signature verification failed")
            return False
        
        return True
    
    def check_replay_attack(self, delivery_id: str, timestamp: Optional[str] = None) -> bool:
        """Check for replay attacks."""
        # Check if delivery ID was already processed
        if delivery_id in self.processed_deliveries:
            logger.warning(f"Duplicate delivery ID detected: {delivery_id}")
            return False
        
        # Check timestamp if provided (GitHub doesn't send timestamp in headers)
        if timestamp:
            try:
                webhook_time = int(timestamp)
                current_time = int(time.time())
                
                if abs(current_time - webhook_time) > self.replay_window:
                    logger.warning(f"Webhook timestamp outside replay window: {timestamp}")
                    return False
            except (ValueError, TypeError):
                logger.warning(f"Invalid timestamp format: {timestamp}")
                return False
        
        # Mark delivery as processed
        self.processed_deliveries.add(delivery_id)
        
        # Clean up old delivery IDs (in production, use Redis with TTL)
        if len(self.processed_deliveries) > 10000:
            # Keep only recent 5000 entries
            self.processed_deliveries = set(list(self.processed_deliveries)[-5000:])
        
        return True
    
    def validate_payload_size(self, payload: bytes) -> bool:
        """Validate payload size."""
        if len(payload) > settings.webhook_max_payload_size:
            logger.warning(f"Payload size exceeds limit: {len(payload)} bytes")
            return False
        return True
    
    async def validate_webhook(self, request: Request) -> tuple[WebhookHeaders, Dict[str, Any]]:
        """Validate complete webhook request."""
        # Read payload
        payload = await request.body()
        
        # Validate payload size
        if not self.validate_payload_size(payload):
            raise HTTPException(
                status_code=413,
                detail="Payload too large"
            )
        
        # Parse headers
        try:
            headers = WebhookHeaders(**dict(request.headers))
        except Exception as e:
            logger.error(f"Invalid webhook headers: {e}")
            raise HTTPException(
                status_code=400,
                detail="Invalid webhook headers"
            )
        
        # Verify signature
        if settings.github_webhook_secret and headers.x_hub_signature_256:
            if not self.verify_signature(payload, headers.x_hub_signature_256):
                raise HTTPException(
                    status_code=401,
                    detail="Invalid signature"
                )
        
        # Check for replay attacks
        if not self.check_replay_attack(headers.x_github_delivery):
            raise HTTPException(
                status_code=409,
                detail="Duplicate or replayed request"
            )
        
        # Parse JSON payload
        try:
            import json
            payload_data = json.loads(payload.decode())
        except Exception as e:
            logger.error(f"Invalid JSON payload: {e}")
            raise HTTPException(
                status_code=400,
                detail="Invalid JSON payload"
            )
        
        # Validate payload structure based on event type
        try:
            if headers.x_github_event == "pull_request":
                PullRequestPayload(**payload_data)
            elif headers.x_github_event == "check_run":
                CheckRunPayload(**payload_data)
            elif headers.x_github_event == "check_suite":
                CheckSuitePayload(**payload_data)
            else:
                # For other events, use base validation
                GitHubWebhookPayload(**payload_data)
        except Exception as e:
            logger.error(f"Invalid payload structure for {headers.x_github_event}: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid payload structure: {e}"
            )
        
        logger.info(
            "webhook_validated",
            event_type=headers.x_github_event,
            delivery_id=headers.x_github_delivery,
            payload_size=len(payload),
        )
        
        return headers, payload_data


# Global validator instance
webhook_validator = WebhookValidator()

