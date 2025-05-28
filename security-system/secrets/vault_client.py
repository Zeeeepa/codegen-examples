"""
HashiCorp Vault client for secure secret management.
Supports multiple authentication methods and automatic secret rotation.
"""

import hvac
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from enum import Enum
import threading
import schedule

class VaultAuthMethod(Enum):
    """Supported Vault authentication methods."""
    TOKEN = "token"
    USERPASS = "userpass"
    APPROLE = "approle"
    AWS_IAM = "aws_iam"
    KUBERNETES = "kubernetes"
    LDAP = "ldap"

@dataclass
class SecretMetadata:
    """Metadata for stored secrets."""
    path: str
    version: int
    created_time: datetime
    deletion_time: Optional[datetime]
    destroyed: bool
    custom_metadata: Dict[str, Any]

class VaultClient:
    """
    Comprehensive HashiCorp Vault client with advanced features.
    Supports multiple auth methods, secret rotation, and high availability.
    """
    
    def __init__(
        self,
        url: str,
        auth_method: VaultAuthMethod,
        auth_config: Dict[str, Any],
        mount_point: str = "secret",
        namespace: Optional[str] = None,
        verify_ssl: bool = True,
        timeout: int = 30,
        max_retries: int = 3
    ):
        self.url = url
        self.auth_method = auth_method
        self.auth_config = auth_config
        self.mount_point = mount_point
        self.namespace = namespace
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Initialize Vault client
        self.client = hvac.Client(
            url=self.url,
            verify=self.verify_ssl,
            timeout=self.timeout,
            namespace=self.namespace
        )
        
        # Authentication state
        self._authenticated = False
        self._token_lease_duration = 0
        self._token_renewable = False
        self._auth_lock = threading.Lock()
        
        # Auto-renewal thread
        self._renewal_thread = None
        self._stop_renewal = threading.Event()
        
        # Initialize authentication
        self._authenticate()
    
    def _authenticate(self) -> bool:
        """Authenticate with Vault using configured method."""
        with self._auth_lock:
            try:
                if self.auth_method == VaultAuthMethod.TOKEN:
                    self.client.token = self.auth_config["token"]
                    
                elif self.auth_method == VaultAuthMethod.USERPASS:
                    response = self.client.auth.userpass.login(
                        username=self.auth_config["username"],
                        password=self.auth_config["password"]
                    )
                    self._handle_auth_response(response)
                    
                elif self.auth_method == VaultAuthMethod.APPROLE:
                    response = self.client.auth.approle.login(
                        role_id=self.auth_config["role_id"],
                        secret_id=self.auth_config["secret_id"]
                    )
                    self._handle_auth_response(response)
                    
                elif self.auth_method == VaultAuthMethod.AWS_IAM:
                    response = self.client.auth.aws.iam_login(
                        access_key=self.auth_config.get("access_key"),
                        secret_key=self.auth_config.get("secret_key"),
                        session_token=self.auth_config.get("session_token"),
                        role=self.auth_config["role"]
                    )
                    self._handle_auth_response(response)
                    
                elif self.auth_method == VaultAuthMethod.KUBERNETES:
                    with open(self.auth_config["jwt_path"], "r") as f:
                        jwt_token = f.read().strip()
                    
                    response = self.client.auth.kubernetes.login(
                        role=self.auth_config["role"],
                        jwt=jwt_token
                    )
                    self._handle_auth_response(response)
                    
                elif self.auth_method == VaultAuthMethod.LDAP:
                    response = self.client.auth.ldap.login(
                        username=self.auth_config["username"],
                        password=self.auth_config["password"]
                    )
                    self._handle_auth_response(response)
                
                # Verify authentication
                if self.client.is_authenticated():
                    self._authenticated = True
                    self._start_token_renewal()
                    return True
                
                return False
                
            except Exception as e:
                print(f"Vault authentication failed: {e}")
                return False
    
    def _handle_auth_response(self, response: Dict[str, Any]):
        """Handle authentication response and extract token info."""
        if response and "auth" in response:
            auth_data = response["auth"]
            self.client.token = auth_data["client_token"]
            self._token_lease_duration = auth_data.get("lease_duration", 0)
            self._token_renewable = auth_data.get("renewable", False)
    
    def _start_token_renewal(self):
        """Start automatic token renewal if token is renewable."""
        if self._token_renewable and self._token_lease_duration > 0:
            if self._renewal_thread and self._renewal_thread.is_alive():
                self._stop_renewal.set()
                self._renewal_thread.join()
            
            self._stop_renewal.clear()
            self._renewal_thread = threading.Thread(target=self._token_renewal_loop)
            self._renewal_thread.daemon = True
            self._renewal_thread.start()
    
    def _token_renewal_loop(self):
        """Token renewal loop running in background thread."""
        # Renew token at 50% of lease duration
        renewal_interval = self._token_lease_duration * 0.5
        
        while not self._stop_renewal.wait(renewal_interval):
            try:
                response = self.client.auth.token.renew_self()
                if response and "auth" in response:
                    auth_data = response["auth"]
                    self._token_lease_duration = auth_data.get("lease_duration", 0)
                    renewal_interval = self._token_lease_duration * 0.5
                    print(f"Vault token renewed, next renewal in {renewal_interval} seconds")
                
            except Exception as e:
                print(f"Token renewal failed: {e}")
                # Try to re-authenticate
                if not self._authenticate():
                    print("Re-authentication failed, stopping renewal")
                    break
    
    def is_authenticated(self) -> bool:
        """Check if client is authenticated."""
        return self._authenticated and self.client.is_authenticated()
    
    def read_secret(self, path: str, version: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Read secret from Vault.
        
        Args:
            path: Secret path
            version: Specific version to read (KV v2 only)
        
        Returns:
            Secret data or None if not found
        """
        if not self.is_authenticated():
            if not self._authenticate():
                return None
        
        try:
            if version:
                # KV v2 with specific version
                response = self.client.secrets.kv.v2.read_secret_version(
                    path=path,
                    version=version,
                    mount_point=self.mount_point
                )
            else:
                # KV v2 latest version
                response = self.client.secrets.kv.v2.read_secret_version(
                    path=path,
                    mount_point=self.mount_point
                )
            
            if response and "data" in response:
                return response["data"]["data"]
            
            return None
            
        except Exception as e:
            print(f"Failed to read secret {path}: {e}")
            return None
    
    def write_secret(
        self,
        path: str,
        secret_data: Dict[str, Any],
        cas: Optional[int] = None
    ) -> bool:
        """
        Write secret to Vault.
        
        Args:
            path: Secret path
            secret_data: Secret data to store
            cas: Check-and-set version for atomic updates
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_authenticated():
            if not self._authenticate():
                return False
        
        try:
            self.client.secrets.kv.v2.create_or_update_secret(
                path=path,
                secret=secret_data,
                cas=cas,
                mount_point=self.mount_point
            )
            return True
            
        except Exception as e:
            print(f"Failed to write secret {path}: {e}")
            return False
    
    def delete_secret(self, path: str, versions: Optional[List[int]] = None) -> bool:
        """
        Delete secret or specific versions.
        
        Args:
            path: Secret path
            versions: Specific versions to delete (None for latest)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_authenticated():
            if not self._authenticate():
                return False
        
        try:
            if versions:
                # Delete specific versions
                self.client.secrets.kv.v2.delete_secret_versions(
                    path=path,
                    versions=versions,
                    mount_point=self.mount_point
                )
            else:
                # Delete latest version
                self.client.secrets.kv.v2.delete_latest_version_of_secret(
                    path=path,
                    mount_point=self.mount_point
                )
            
            return True
            
        except Exception as e:
            print(f"Failed to delete secret {path}: {e}")
            return False
    
    def list_secrets(self, path: str = "") -> Optional[List[str]]:
        """
        List secrets at given path.
        
        Args:
            path: Path to list (empty for root)
        
        Returns:
            List of secret names or None if error
        """
        if not self.is_authenticated():
            if not self._authenticate():
                return None
        
        try:
            response = self.client.secrets.kv.v2.list_secrets(
                path=path,
                mount_point=self.mount_point
            )
            
            if response and "data" in response and "keys" in response["data"]:
                return response["data"]["keys"]
            
            return []
            
        except Exception as e:
            print(f"Failed to list secrets at {path}: {e}")
            return None
    
    def get_secret_metadata(self, path: str) -> Optional[SecretMetadata]:
        """
        Get metadata for a secret.
        
        Args:
            path: Secret path
        
        Returns:
            SecretMetadata object or None if not found
        """
        if not self.is_authenticated():
            if not self._authenticate():
                return None
        
        try:
            response = self.client.secrets.kv.v2.read_secret_metadata(
                path=path,
                mount_point=self.mount_point
            )
            
            if response and "data" in response:
                data = response["data"]
                
                # Get latest version info
                current_version = data.get("current_version", 1)
                versions = data.get("versions", {})
                version_info = versions.get(str(current_version), {})
                
                return SecretMetadata(
                    path=path,
                    version=current_version,
                    created_time=datetime.fromisoformat(
                        version_info.get("created_time", "").replace("Z", "+00:00")
                    ) if version_info.get("created_time") else datetime.now(timezone.utc),
                    deletion_time=datetime.fromisoformat(
                        version_info.get("deletion_time", "").replace("Z", "+00:00")
                    ) if version_info.get("deletion_time") else None,
                    destroyed=version_info.get("destroyed", False),
                    custom_metadata=data.get("custom_metadata", {})
                )
            
            return None
            
        except Exception as e:
            print(f"Failed to get metadata for {path}: {e}")
            return None
    
    def create_database_credentials(
        self,
        db_role: str,
        mount_point: str = "database"
    ) -> Optional[Dict[str, str]]:
        """
        Generate dynamic database credentials.
        
        Args:
            db_role: Database role name
            mount_point: Database secrets engine mount point
        
        Returns:
            Dictionary with username and password or None if failed
        """
        if not self.is_authenticated():
            if not self._authenticate():
                return None
        
        try:
            response = self.client.secrets.database.generate_credentials(
                name=db_role,
                mount_point=mount_point
            )
            
            if response and "data" in response:
                return {
                    "username": response["data"]["username"],
                    "password": response["data"]["password"],
                    "lease_id": response.get("lease_id"),
                    "lease_duration": response.get("lease_duration")
                }
            
            return None
            
        except Exception as e:
            print(f"Failed to generate database credentials for role {db_role}: {e}")
            return None
    
    def revoke_lease(self, lease_id: str) -> bool:
        """
        Revoke a lease.
        
        Args:
            lease_id: Lease ID to revoke
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_authenticated():
            if not self._authenticate():
                return False
        
        try:
            self.client.sys.revoke_lease(lease_id)
            return True
            
        except Exception as e:
            print(f"Failed to revoke lease {lease_id}: {e}")
            return False
    
    def encrypt_data(self, plaintext: str, key_name: str, context: Optional[str] = None) -> Optional[str]:
        """
        Encrypt data using Vault's transit engine.
        
        Args:
            plaintext: Data to encrypt
            key_name: Encryption key name
            context: Optional context for key derivation
        
        Returns:
            Encrypted ciphertext or None if failed
        """
        if not self.is_authenticated():
            if not self._authenticate():
                return None
        
        try:
            import base64
            
            # Encode plaintext to base64
            encoded_plaintext = base64.b64encode(plaintext.encode()).decode()
            
            response = self.client.secrets.transit.encrypt_data(
                name=key_name,
                plaintext=encoded_plaintext,
                context=context
            )
            
            if response and "data" in response:
                return response["data"]["ciphertext"]
            
            return None
            
        except Exception as e:
            print(f"Failed to encrypt data with key {key_name}: {e}")
            return None
    
    def decrypt_data(self, ciphertext: str, key_name: str, context: Optional[str] = None) -> Optional[str]:
        """
        Decrypt data using Vault's transit engine.
        
        Args:
            ciphertext: Encrypted data
            key_name: Encryption key name
            context: Optional context for key derivation
        
        Returns:
            Decrypted plaintext or None if failed
        """
        if not self.is_authenticated():
            if not self._authenticate():
                return None
        
        try:
            import base64
            
            response = self.client.secrets.transit.decrypt_data(
                name=key_name,
                ciphertext=ciphertext,
                context=context
            )
            
            if response and "data" in response:
                # Decode from base64
                encoded_plaintext = response["data"]["plaintext"]
                return base64.b64decode(encoded_plaintext).decode()
            
            return None
            
        except Exception as e:
            print(f"Failed to decrypt data with key {key_name}: {e}")
            return None
    
    def close(self):
        """Close the Vault client and stop background threads."""
        self._stop_renewal.set()
        if self._renewal_thread and self._renewal_thread.is_alive():
            self._renewal_thread.join(timeout=5)

# Example configuration and usage
def create_vault_client(config: Dict[str, Any]) -> VaultClient:
    """Create Vault client with configuration."""
    auth_method = VaultAuthMethod(config["auth_method"])
    
    return VaultClient(
        url=config["url"],
        auth_method=auth_method,
        auth_config=config["auth_config"],
        mount_point=config.get("mount_point", "secret"),
        namespace=config.get("namespace"),
        verify_ssl=config.get("verify_ssl", True),
        timeout=config.get("timeout", 30),
        max_retries=config.get("max_retries", 3)
    )

# Example configurations
EXAMPLE_CONFIGS = {
    "token_auth": {
        "url": "https://vault.example.com:8200",
        "auth_method": "token",
        "auth_config": {
            "token": "hvs.CAESIJ..."
        }
    },
    "userpass_auth": {
        "url": "https://vault.example.com:8200",
        "auth_method": "userpass",
        "auth_config": {
            "username": "vault-user",
            "password": "vault-password"
        }
    },
    "approle_auth": {
        "url": "https://vault.example.com:8200",
        "auth_method": "approle",
        "auth_config": {
            "role_id": "12345678-1234-1234-1234-123456789012",
            "secret_id": "87654321-4321-4321-4321-210987654321"
        }
    },
    "kubernetes_auth": {
        "url": "https://vault.example.com:8200",
        "auth_method": "kubernetes",
        "auth_config": {
            "role": "my-app-role",
            "jwt_path": "/var/run/secrets/kubernetes.io/serviceaccount/token"
        }
    }
}

