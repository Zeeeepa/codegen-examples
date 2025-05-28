"""
OAuth2 authentication provider supporting multiple providers.
Implements secure OAuth2 flows with PKCE and state validation.
"""

import secrets
import hashlib
import base64
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlencode, parse_qs
import httpx
from cryptography.fernet import Fernet

class OAuth2Provider:
    """Base OAuth2 provider with common functionality."""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.state_encryption_key = Fernet.generate_key()
        self.fernet = Fernet(self.state_encryption_key)
    
    def generate_pkce_pair(self) -> Tuple[str, str]:
        """Generate PKCE code verifier and challenge."""
        # Generate code verifier (43-128 characters)
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        
        # Generate code challenge
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        return code_verifier, code_challenge
    
    def generate_state(self, user_data: Dict[str, Any] = None) -> str:
        """Generate encrypted state parameter."""
        state_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'nonce': secrets.token_urlsafe(16),
            'user_data': user_data or {}
        }
        
        state_json = json.dumps(state_data)
        encrypted_state = self.fernet.encrypt(state_json.encode())
        return base64.urlsafe_b64encode(encrypted_state).decode()
    
    def validate_state(self, state: str, max_age_minutes: int = 10) -> Optional[Dict[str, Any]]:
        """Validate and decrypt state parameter."""
        try:
            encrypted_state = base64.urlsafe_b64decode(state.encode())
            decrypted_data = self.fernet.decrypt(encrypted_state)
            state_data = json.loads(decrypted_data.decode())
            
            # Check timestamp
            timestamp = datetime.fromisoformat(state_data['timestamp'])
            if datetime.now(timezone.utc) - timestamp > timedelta(minutes=max_age_minutes):
                return None
            
            return state_data
        except Exception:
            return None
    
    async def exchange_code_for_token(self, code: str, code_verifier: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access token."""
        raise NotImplementedError("Subclasses must implement this method")
    
    async def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user information from the provider."""
        raise NotImplementedError("Subclasses must implement this method")

class GoogleOAuth2Provider(OAuth2Provider):
    """Google OAuth2 provider implementation."""
    
    AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USER_INFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        super().__init__(client_id, client_secret, redirect_uri)
        self.scopes = ["openid", "email", "profile"]
    
    def get_authorization_url(self, user_data: Dict[str, Any] = None) -> Tuple[str, str, str]:
        """Generate authorization URL with PKCE."""
        code_verifier, code_challenge = self.generate_pkce_pair()
        state = self.generate_state(user_data)
        
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(self.scopes),
            'response_type': 'code',
            'state': state,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'access_type': 'offline',
            'prompt': 'consent'
        }
        
        url = f"{self.AUTHORIZATION_URL}?{urlencode(params)}"
        return url, state, code_verifier
    
    async def exchange_code_for_token(self, code: str, code_verifier: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access token."""
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri,
            'code_verifier': code_verifier
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.TOKEN_URL, data=data)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                print(f"Token exchange error: {e}")
                return None
    
    async def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user information from Google."""
        headers = {'Authorization': f'Bearer {access_token}'}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.USER_INFO_URL, headers=headers)
                response.raise_for_status()
                user_data = response.json()
                
                # Normalize user data
                return {
                    'provider_user_id': user_data.get('id'),
                    'email': user_data.get('email'),
                    'first_name': user_data.get('given_name'),
                    'last_name': user_data.get('family_name'),
                    'display_name': user_data.get('name'),
                    'avatar_url': user_data.get('picture'),
                    'is_verified': user_data.get('verified_email', False),
                    'provider_data': user_data
                }
            except Exception as e:
                print(f"User info error: {e}")
                return None

class GitHubOAuth2Provider(OAuth2Provider):
    """GitHub OAuth2 provider implementation."""
    
    AUTHORIZATION_URL = "https://github.com/login/oauth/authorize"
    TOKEN_URL = "https://github.com/login/oauth/access_token"
    USER_INFO_URL = "https://api.github.com/user"
    USER_EMAIL_URL = "https://api.github.com/user/emails"
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        super().__init__(client_id, client_secret, redirect_uri)
        self.scopes = ["user:email", "read:user"]
    
    def get_authorization_url(self, user_data: Dict[str, Any] = None) -> Tuple[str, str, str]:
        """Generate authorization URL."""
        state = self.generate_state(user_data)
        
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(self.scopes),
            'state': state,
            'allow_signup': 'true'
        }
        
        url = f"{self.AUTHORIZATION_URL}?{urlencode(params)}"
        return url, state, ""  # GitHub doesn't use PKCE
    
    async def exchange_code_for_token(self, code: str, code_verifier: str = None) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access token."""
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code
        }
        
        headers = {'Accept': 'application/json'}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.TOKEN_URL, data=data, headers=headers)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                print(f"Token exchange error: {e}")
                return None
    
    async def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user information from GitHub."""
        headers = {
            'Authorization': f'token {access_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        async with httpx.AsyncClient() as client:
            try:
                # Get user profile
                user_response = await client.get(self.USER_INFO_URL, headers=headers)
                user_response.raise_for_status()
                user_data = user_response.json()
                
                # Get user emails
                email_response = await client.get(self.USER_EMAIL_URL, headers=headers)
                email_response.raise_for_status()
                emails = email_response.json()
                
                # Find primary email
                primary_email = None
                for email in emails:
                    if email.get('primary'):
                        primary_email = email.get('email')
                        break
                
                # Normalize user data
                return {
                    'provider_user_id': str(user_data.get('id')),
                    'email': primary_email or user_data.get('email'),
                    'username': user_data.get('login'),
                    'display_name': user_data.get('name') or user_data.get('login'),
                    'avatar_url': user_data.get('avatar_url'),
                    'is_verified': any(email.get('verified') for email in emails if email.get('primary')),
                    'provider_data': {
                        'user': user_data,
                        'emails': emails
                    }
                }
            except Exception as e:
                print(f"User info error: {e}")
                return None

class MicrosoftOAuth2Provider(OAuth2Provider):
    """Microsoft OAuth2 provider implementation."""
    
    AUTHORIZATION_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    USER_INFO_URL = "https://graph.microsoft.com/v1.0/me"
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, tenant_id: str = "common"):
        super().__init__(client_id, client_secret, redirect_uri)
        self.tenant_id = tenant_id
        self.scopes = ["openid", "profile", "email", "User.Read"]
        
        # Update URLs with tenant ID
        self.AUTHORIZATION_URL = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
        self.TOKEN_URL = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    
    def get_authorization_url(self, user_data: Dict[str, Any] = None) -> Tuple[str, str, str]:
        """Generate authorization URL with PKCE."""
        code_verifier, code_challenge = self.generate_pkce_pair()
        state = self.generate_state(user_data)
        
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(self.scopes),
            'response_type': 'code',
            'state': state,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'response_mode': 'query'
        }
        
        url = f"{self.AUTHORIZATION_URL}?{urlencode(params)}"
        return url, state, code_verifier
    
    async def exchange_code_for_token(self, code: str, code_verifier: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access token."""
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri,
            'code_verifier': code_verifier
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.TOKEN_URL, data=data)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                print(f"Token exchange error: {e}")
                return None
    
    async def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user information from Microsoft Graph."""
        headers = {'Authorization': f'Bearer {access_token}'}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.USER_INFO_URL, headers=headers)
                response.raise_for_status()
                user_data = response.json()
                
                # Normalize user data
                return {
                    'provider_user_id': user_data.get('id'),
                    'email': user_data.get('mail') or user_data.get('userPrincipalName'),
                    'first_name': user_data.get('givenName'),
                    'last_name': user_data.get('surname'),
                    'display_name': user_data.get('displayName'),
                    'username': user_data.get('userPrincipalName'),
                    'is_verified': True,  # Microsoft accounts are considered verified
                    'provider_data': user_data
                }
            except Exception as e:
                print(f"User info error: {e}")
                return None

class OAuth2Manager:
    """OAuth2 provider manager."""
    
    def __init__(self):
        self.providers = {}
    
    def register_provider(self, name: str, provider: OAuth2Provider):
        """Register an OAuth2 provider."""
        self.providers[name] = provider
    
    def get_provider(self, name: str) -> Optional[OAuth2Provider]:
        """Get OAuth2 provider by name."""
        return self.providers.get(name)
    
    def get_authorization_url(self, provider_name: str, user_data: Dict[str, Any] = None) -> Optional[Tuple[str, str, str]]:
        """Get authorization URL for a provider."""
        provider = self.get_provider(provider_name)
        if provider:
            return provider.get_authorization_url(user_data)
        return None
    
    async def handle_callback(self, provider_name: str, code: str, state: str, code_verifier: str = None) -> Optional[Dict[str, Any]]:
        """Handle OAuth2 callback and return user information."""
        provider = self.get_provider(provider_name)
        if not provider:
            return None
        
        # Validate state
        state_data = provider.validate_state(state)
        if not state_data:
            return None
        
        # Exchange code for token
        token_data = await provider.exchange_code_for_token(code, code_verifier)
        if not token_data or 'access_token' not in token_data:
            return None
        
        # Get user information
        user_info = await provider.get_user_info(token_data['access_token'])
        if not user_info:
            return None
        
        # Add token and state data
        user_info['token_data'] = token_data
        user_info['state_data'] = state_data
        user_info['provider'] = provider_name
        
        return user_info

# Example usage and configuration
def create_oauth2_manager(config: Dict[str, Dict[str, str]]) -> OAuth2Manager:
    """Create and configure OAuth2 manager."""
    manager = OAuth2Manager()
    
    # Register Google provider
    if 'google' in config:
        google_config = config['google']
        provider = GoogleOAuth2Provider(
            client_id=google_config['client_id'],
            client_secret=google_config['client_secret'],
            redirect_uri=google_config['redirect_uri']
        )
        manager.register_provider('google', provider)
    
    # Register GitHub provider
    if 'github' in config:
        github_config = config['github']
        provider = GitHubOAuth2Provider(
            client_id=github_config['client_id'],
            client_secret=github_config['client_secret'],
            redirect_uri=github_config['redirect_uri']
        )
        manager.register_provider('github', provider)
    
    # Register Microsoft provider
    if 'microsoft' in config:
        microsoft_config = config['microsoft']
        provider = MicrosoftOAuth2Provider(
            client_id=microsoft_config['client_id'],
            client_secret=microsoft_config['client_secret'],
            redirect_uri=microsoft_config['redirect_uri'],
            tenant_id=microsoft_config.get('tenant_id', 'common')
        )
        manager.register_provider('microsoft', provider)
    
    return manager

