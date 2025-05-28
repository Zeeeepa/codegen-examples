"""
JWT token service for secure token generation, validation, and management.
Supports access tokens, refresh tokens, and API key management.
"""

import jwt
import secrets
import hashlib
import hmac
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import base64

class TokenService:
    """
    Comprehensive token service for JWT and API key management.
    Supports RS256 and HS256 algorithms with key rotation.
    """
    
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 30,
        private_key: Optional[str] = None,
        public_key: Optional[str] = None,
        issuer: str = "ai-workflow-platform",
        audience: str = "ai-workflow-platform"
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        self.issuer = issuer
        self.audience = audience
        
        # For RS256 algorithm
        self.private_key = private_key
        self.public_key = public_key
        
        # Validate configuration
        if algorithm == "RS256" and (not private_key or not public_key):
            raise ValueError("RS256 algorithm requires both private and public keys")
    
    def generate_access_token(
        self,
        user_id: str,
        email: str,
        roles: List[str],
        permissions: List[str],
        mfa_verified: bool = False,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate JWT access token with user claims."""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            # Standard claims
            "iss": self.issuer,
            "aud": self.audience,
            "sub": user_id,
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "jti": secrets.token_hex(16),  # JWT ID for revocation
            
            # Custom claims
            "email": email,
            "roles": roles,
            "permissions": permissions,
            "mfa_verified": mfa_verified,
            "token_type": "access"
        }
        
        # Add additional claims if provided
        if additional_claims:
            payload.update(additional_claims)
        
        return self._encode_token(payload)
    
    def generate_refresh_token(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate JWT refresh token."""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=self.refresh_token_expire_days)
        
        payload = {
            # Standard claims
            "iss": self.issuer,
            "aud": self.audience,
            "sub": user_id,
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "jti": secrets.token_hex(16),
            
            # Custom claims
            "token_type": "refresh",
            "session_id": session_id
        }
        
        # Add additional claims if provided
        if additional_claims:
            payload.update(additional_claims)
        
        return self._encode_token(payload)
    
    def verify_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode access token."""
        try:
            payload = self._decode_token(token)
            
            # Verify token type
            if payload.get("token_type") != "access":
                return None
            
            # Verify expiration
            exp = payload.get("exp")
            if exp and datetime.now(timezone.utc).timestamp() > exp:
                return None
            
            return payload
            
        except Exception as e:
            print(f"Access token verification failed: {e}")
            return None
    
    def verify_refresh_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode refresh token."""
        try:
            payload = self._decode_token(token)
            
            # Verify token type
            if payload.get("token_type") != "refresh":
                return None
            
            # Verify expiration
            exp = payload.get("exp")
            if exp and datetime.now(timezone.utc).timestamp() > exp:
                return None
            
            return payload
            
        except Exception as e:
            print(f"Refresh token verification failed: {e}")
            return None
    
    def refresh_access_token(
        self,
        refresh_token: str,
        user_data: Dict[str, Any]
    ) -> Optional[tuple[str, str]]:
        """
        Generate new access and refresh tokens using refresh token.
        
        Returns:
            Tuple of (new_access_token, new_refresh_token) or None if invalid
        """
        # Verify refresh token
        payload = self.verify_refresh_token(refresh_token)
        if not payload:
            return None
        
        # Generate new tokens
        new_access_token = self.generate_access_token(
            user_id=payload["sub"],
            email=user_data["email"],
            roles=user_data["roles"],
            permissions=user_data["permissions"],
            mfa_verified=user_data.get("mfa_verified", False)
        )
        
        new_refresh_token = self.generate_refresh_token(
            user_id=payload["sub"],
            session_id=payload.get("session_id")
        )
        
        return new_access_token, new_refresh_token
    
    def generate_api_key(self, prefix: str = "ak") -> tuple[str, str, str]:
        """
        Generate API key with prefix and hash.
        
        Returns:
            Tuple of (api_key, key_hash, key_prefix)
        """
        # Generate random key
        key_bytes = secrets.token_bytes(32)
        key_b64 = base64.urlsafe_b64encode(key_bytes).decode().rstrip('=')
        
        # Create full API key with prefix
        api_key = f"{prefix}_{key_b64}"
        
        # Generate hash for storage
        key_hash = self.hash_api_key(api_key)
        
        # Extract prefix for identification
        key_prefix = api_key[:8] + "..."
        
        return api_key, key_hash, key_prefix
    
    def hash_api_key(self, api_key: str) -> str:
        """Hash API key for secure storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def verify_api_key(self, api_key: str, stored_hash: str) -> bool:
        """Verify API key against stored hash."""
        computed_hash = self.hash_api_key(api_key)
        return hmac.compare_digest(computed_hash, stored_hash)
    
    def extract_token_claims(self, token: str) -> Optional[Dict[str, Any]]:
        """Extract claims from token without verification (for debugging)."""
        try:
            # Decode without verification
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload
        except Exception:
            return None
    
    def is_token_expired(self, token: str) -> bool:
        """Check if token is expired without full verification."""
        claims = self.extract_token_claims(token)
        if not claims:
            return True
        
        exp = claims.get("exp")
        if not exp:
            return True
        
        return datetime.now(timezone.utc).timestamp() > exp
    
    def get_token_expiry(self, token: str) -> Optional[datetime]:
        """Get token expiry time."""
        claims = self.extract_token_claims(token)
        if not claims:
            return None
        
        exp = claims.get("exp")
        if not exp:
            return None
        
        return datetime.fromtimestamp(exp, tz=timezone.utc)
    
    def revoke_token(self, token: str, revoked_tokens_store) -> bool:
        """
        Revoke a token by adding its JTI to revoked tokens store.
        
        Args:
            token: Token to revoke
            revoked_tokens_store: Storage for revoked token JTIs (Redis, database, etc.)
        
        Returns:
            True if successfully revoked, False otherwise
        """
        claims = self.extract_token_claims(token)
        if not claims:
            return False
        
        jti = claims.get("jti")
        if not jti:
            return False
        
        # Store JTI with expiry time
        exp = claims.get("exp")
        if exp:
            expiry = datetime.fromtimestamp(exp, tz=timezone.utc)
            revoked_tokens_store.set(f"revoked:{jti}", "1", ex=int((expiry - datetime.now(timezone.utc)).total_seconds()))
        
        return True
    
    def is_token_revoked(self, token: str, revoked_tokens_store) -> bool:
        """Check if token is revoked."""
        claims = self.extract_token_claims(token)
        if not claims:
            return True
        
        jti = claims.get("jti")
        if not jti:
            return True
        
        return revoked_tokens_store.exists(f"revoked:{jti}")
    
    def _encode_token(self, payload: Dict[str, Any]) -> str:
        """Encode JWT token using configured algorithm."""
        if self.algorithm == "RS256":
            return jwt.encode(payload, self.private_key, algorithm=self.algorithm)
        else:
            return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def _decode_token(self, token: str) -> Dict[str, Any]:
        """Decode JWT token using configured algorithm."""
        if self.algorithm == "RS256":
            return jwt.decode(
                token,
                self.public_key,
                algorithms=[self.algorithm],
                issuer=self.issuer,
                audience=self.audience
            )
        else:
            return jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                issuer=self.issuer,
                audience=self.audience
            )

class KeyRotationService:
    """Service for managing key rotation for enhanced security."""
    
    def __init__(self, token_service: TokenService):
        self.token_service = token_service
        self.key_history = []  # Store previous keys for token validation
    
    def generate_new_rsa_keypair(self) -> tuple[str, str]:
        """Generate new RSA key pair for RS256 algorithm."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode()
        
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        
        return private_pem, public_pem
    
    def rotate_keys(self) -> tuple[str, str]:
        """Rotate keys and update token service."""
        if self.token_service.algorithm == "RS256":
            # Store current keys in history
            if self.token_service.private_key and self.token_service.public_key:
                self.key_history.append({
                    "private_key": self.token_service.private_key,
                    "public_key": self.token_service.public_key,
                    "rotated_at": datetime.now(timezone.utc)
                })
            
            # Generate new keys
            new_private_key, new_public_key = self.generate_new_rsa_keypair()
            
            # Update token service
            self.token_service.private_key = new_private_key
            self.token_service.public_key = new_public_key
            
            return new_private_key, new_public_key
        
        else:
            # For HS256, generate new secret
            old_secret = self.token_service.secret_key
            new_secret = secrets.token_urlsafe(64)
            
            # Store old secret in history
            self.key_history.append({
                "secret_key": old_secret,
                "rotated_at": datetime.now(timezone.utc)
            })
            
            # Update token service
            self.token_service.secret_key = new_secret
            
            return new_secret, ""
    
    def verify_token_with_history(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify token using current and historical keys."""
        # Try current key first
        payload = self.token_service.verify_access_token(token)
        if payload:
            return payload
        
        # Try historical keys
        for key_data in reversed(self.key_history):
            try:
                if self.token_service.algorithm == "RS256":
                    payload = jwt.decode(
                        token,
                        key_data["public_key"],
                        algorithms=[self.token_service.algorithm],
                        issuer=self.token_service.issuer,
                        audience=self.token_service.audience
                    )
                else:
                    payload = jwt.decode(
                        token,
                        key_data["secret_key"],
                        algorithms=[self.token_service.algorithm],
                        issuer=self.token_service.issuer,
                        audience=self.token_service.audience
                    )
                
                if payload:
                    return payload
                    
            except Exception:
                continue
        
        return None
    
    def cleanup_old_keys(self, max_age_days: int = 30):
        """Remove old keys from history."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        self.key_history = [
            key_data for key_data in self.key_history
            if key_data["rotated_at"] > cutoff_date
        ]

# Example usage and configuration
def create_token_service(config: Dict[str, Any]) -> TokenService:
    """Create token service with configuration."""
    return TokenService(
        secret_key=config["secret_key"],
        algorithm=config.get("algorithm", "HS256"),
        access_token_expire_minutes=config.get("access_token_expire_minutes", 15),
        refresh_token_expire_days=config.get("refresh_token_expire_days", 30),
        private_key=config.get("private_key"),
        public_key=config.get("public_key"),
        issuer=config.get("issuer", "ai-workflow-platform"),
        audience=config.get("audience", "ai-workflow-platform")
    )

