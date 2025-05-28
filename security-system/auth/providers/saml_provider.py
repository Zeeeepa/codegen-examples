"""
SAML 2.0 authentication provider for enterprise SSO integration.
Supports multiple SAML identity providers with flexible attribute mapping.
"""

import base64
import gzip
import secrets
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode, quote
import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.x509 import load_pem_x509_certificate
import defusedxml.ElementTree as safe_ET

class SAMLProvider:
    """SAML 2.0 Service Provider implementation."""
    
    def __init__(
        self,
        entity_id: str,
        acs_url: str,
        sso_url: str,
        slo_url: Optional[str] = None,
        x509_cert: Optional[str] = None,
        private_key: Optional[str] = None,
        idp_cert: Optional[str] = None,
        attribute_mapping: Optional[Dict[str, str]] = None
    ):
        self.entity_id = entity_id
        self.acs_url = acs_url  # Assertion Consumer Service URL
        self.sso_url = sso_url  # Identity Provider SSO URL
        self.slo_url = slo_url  # Single Logout URL
        self.x509_cert = x509_cert
        self.private_key = private_key
        self.idp_cert = idp_cert
        self.attribute_mapping = attribute_mapping or self._default_attribute_mapping()
        
        # Load certificates if provided
        self.idp_certificate = None
        if self.idp_cert:
            self.idp_certificate = load_pem_x509_certificate(self.idp_cert.encode())
    
    def _default_attribute_mapping(self) -> Dict[str, str]:
        """Default SAML attribute mapping."""
        return {
            'email': 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress',
            'first_name': 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname',
            'last_name': 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname',
            'display_name': 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name',
            'username': 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier',
            'groups': 'http://schemas.microsoft.com/ws/2008/06/identity/claims/groups',
            'department': 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/department',
            'title': 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/title'
        }
    
    def generate_request_id(self) -> str:
        """Generate unique request ID."""
        return f"_{secrets.token_hex(16)}"
    
    def create_authn_request(self, relay_state: Optional[str] = None) -> tuple[str, str]:
        """Create SAML authentication request."""
        request_id = self.generate_request_id()
        issue_instant = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # Create SAML AuthnRequest XML
        authn_request = f'''<?xml version="1.0" encoding="UTF-8"?>
<samlp:AuthnRequest
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{issue_instant}"
    Destination="{self.sso_url}"
    AssertionConsumerServiceURL="{self.acs_url}"
    ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
    <saml:Issuer>{self.entity_id}</saml:Issuer>
    <samlp:NameIDPolicy
        Format="urn:oasis:names:tc:SAML:2.0:nameid-format:emailAddress"
        AllowCreate="true"/>
    <samlp:RequestedAuthnContext Comparison="exact">
        <saml:AuthnContextClassRef>urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport</saml:AuthnContextClassRef>
    </samlp:RequestedAuthnContext>
</samlp:AuthnRequest>'''
        
        # Encode and compress the request
        encoded_request = base64.b64encode(
            gzip.compress(authn_request.encode('utf-8'))
        ).decode('utf-8')
        
        # Create SSO URL with parameters
        params = {
            'SAMLRequest': encoded_request
        }
        
        if relay_state:
            params['RelayState'] = relay_state
        
        sso_url = f"{self.sso_url}?{urlencode(params)}"
        
        return sso_url, request_id
    
    def parse_saml_response(self, saml_response: str, relay_state: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Parse and validate SAML response."""
        try:
            # Decode base64 response
            decoded_response = base64.b64decode(saml_response)
            
            # Parse XML safely
            root = safe_ET.fromstring(decoded_response)
            
            # Validate response
            if not self._validate_response(root):
                return None
            
            # Extract user attributes
            user_data = self._extract_user_attributes(root)
            
            if user_data:
                user_data['relay_state'] = relay_state
                user_data['provider'] = 'saml'
            
            return user_data
            
        except Exception as e:
            print(f"SAML response parsing error: {e}")
            return None
    
    def _validate_response(self, root: ET.Element) -> bool:
        """Validate SAML response."""
        # Define namespaces
        namespaces = {
            'samlp': 'urn:oasis:names:tc:SAML:2.0:protocol',
            'saml': 'urn:oasis:names:tc:SAML:2.0:assertion',
            'ds': 'http://www.w3.org/2000/09/xmldsig#'
        }
        
        # Check if response is successful
        status = root.find('.//samlp:Status/samlp:StatusCode', namespaces)
        if status is None or status.get('Value') != 'urn:oasis:names:tc:SAML:2.0:status:Success':
            return False
        
        # Find assertion
        assertion = root.find('.//saml:Assertion', namespaces)
        if assertion is None:
            return False
        
        # Validate assertion conditions
        conditions = assertion.find('.//saml:Conditions', namespaces)
        if conditions is not None:
            not_before = conditions.get('NotBefore')
            not_on_or_after = conditions.get('NotOnOrAfter')
            
            now = datetime.now(timezone.utc)
            
            if not_before:
                not_before_dt = datetime.fromisoformat(not_before.replace('Z', '+00:00'))
                if now < not_before_dt:
                    return False
            
            if not_on_or_after:
                not_on_or_after_dt = datetime.fromisoformat(not_on_or_after.replace('Z', '+00:00'))
                if now >= not_on_or_after_dt:
                    return False
            
            # Validate audience
            audience = conditions.find('.//saml:Audience', namespaces)
            if audience is not None and audience.text != self.entity_id:
                return False
        
        # Validate signature if certificate is provided
        if self.idp_certificate:
            return self._validate_signature(assertion, namespaces)
        
        return True
    
    def _validate_signature(self, assertion: ET.Element, namespaces: Dict[str, str]) -> bool:
        """Validate XML signature."""
        try:
            # Find signature
            signature = assertion.find('.//ds:Signature', namespaces)
            if signature is None:
                return False
            
            # Extract signature value
            signature_value = signature.find('.//ds:SignatureValue', namespaces)
            if signature_value is None:
                return False
            
            signature_bytes = base64.b64decode(signature_value.text)
            
            # Get public key from certificate
            public_key = self.idp_certificate.public_key()
            
            # Create canonical XML for verification (simplified)
            # In production, use proper XML canonicalization
            signed_info = signature.find('.//ds:SignedInfo', namespaces)
            if signed_info is None:
                return False
            
            # Verify signature (simplified - use proper XML-DSIG library in production)
            try:
                public_key.verify(
                    signature_bytes,
                    ET.tostring(signed_info, encoding='utf-8'),
                    padding.PKCS1v15(),
                    hashes.SHA256()
                )
                return True
            except Exception:
                return False
                
        except Exception as e:
            print(f"Signature validation error: {e}")
            return False
    
    def _extract_user_attributes(self, root: ET.Element) -> Optional[Dict[str, Any]]:
        """Extract user attributes from SAML assertion."""
        namespaces = {
            'samlp': 'urn:oasis:names:tc:SAML:2.0:protocol',
            'saml': 'urn:oasis:names:tc:SAML:2.0:assertion'
        }
        
        # Find assertion
        assertion = root.find('.//saml:Assertion', namespaces)
        if assertion is None:
            return None
        
        user_data = {}
        
        # Extract NameID
        name_id = assertion.find('.//saml:Subject/saml:NameID', namespaces)
        if name_id is not None:
            user_data['provider_user_id'] = name_id.text
            user_data['username'] = name_id.text
        
        # Extract attributes
        attribute_statements = assertion.findall('.//saml:AttributeStatement', namespaces)
        
        for attr_statement in attribute_statements:
            attributes = attr_statement.findall('.//saml:Attribute', namespaces)
            
            for attribute in attributes:
                attr_name = attribute.get('Name')
                attr_values = []
                
                # Get attribute values
                for attr_value in attribute.findall('.//saml:AttributeValue', namespaces):
                    if attr_value.text:
                        attr_values.append(attr_value.text)
                
                # Map to standard fields
                for field_name, saml_attr_name in self.attribute_mapping.items():
                    if attr_name == saml_attr_name:
                        if len(attr_values) == 1:
                            user_data[field_name] = attr_values[0]
                        elif len(attr_values) > 1:
                            user_data[field_name] = attr_values
                        break
                else:
                    # Store unmapped attributes
                    if 'saml_attributes' not in user_data:
                        user_data['saml_attributes'] = {}
                    
                    if len(attr_values) == 1:
                        user_data['saml_attributes'][attr_name] = attr_values[0]
                    elif len(attr_values) > 1:
                        user_data['saml_attributes'][attr_name] = attr_values
        
        # Set default values
        user_data['is_verified'] = True  # SAML users are considered verified
        user_data['auth_provider'] = 'saml'
        
        return user_data if user_data else None
    
    def create_logout_request(self, name_id: str, session_index: Optional[str] = None) -> str:
        """Create SAML logout request."""
        if not self.slo_url:
            raise ValueError("Single Logout URL not configured")
        
        request_id = self.generate_request_id()
        issue_instant = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        
        logout_request = f'''<?xml version="1.0" encoding="UTF-8"?>
<samlp:LogoutRequest
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{issue_instant}"
    Destination="{self.slo_url}">
    <saml:Issuer>{self.entity_id}</saml:Issuer>
    <saml:NameID Format="urn:oasis:names:tc:SAML:2.0:nameid-format:emailAddress">{name_id}</saml:NameID>
    {f'<samlp:SessionIndex>{session_index}</samlp:SessionIndex>' if session_index else ''}
</samlp:LogoutRequest>'''
        
        # Encode and compress the request
        encoded_request = base64.b64encode(
            gzip.compress(logout_request.encode('utf-8'))
        ).decode('utf-8')
        
        # Create logout URL
        params = {'SAMLRequest': encoded_request}
        logout_url = f"{self.slo_url}?{urlencode(params)}"
        
        return logout_url
    
    def generate_metadata(self) -> str:
        """Generate SAML metadata for this service provider."""
        metadata = f'''<?xml version="1.0" encoding="UTF-8"?>
<md:EntityDescriptor
    xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
    entityID="{self.entity_id}">
    <md:SPSSODescriptor
        protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol"
        AuthnRequestsSigned="false"
        WantAssertionsSigned="true">
        <md:NameIDFormat>urn:oasis:names:tc:SAML:2.0:nameid-format:emailAddress</md:NameIDFormat>
        <md:AssertionConsumerService
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
            Location="{self.acs_url}"
            index="1"/>
        {f'<md:SingleLogoutService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect" Location="{self.slo_url}"/>' if self.slo_url else ''}
    </md:SPSSODescriptor>
</md:EntityDescriptor>'''
        
        return metadata

class SAMLManager:
    """SAML provider manager for multiple identity providers."""
    
    def __init__(self):
        self.providers = {}
    
    def register_provider(self, name: str, provider: SAMLProvider):
        """Register a SAML provider."""
        self.providers[name] = provider
    
    def get_provider(self, name: str) -> Optional[SAMLProvider]:
        """Get SAML provider by name."""
        return self.providers.get(name)
    
    def create_authn_request(self, provider_name: str, relay_state: Optional[str] = None) -> Optional[tuple[str, str]]:
        """Create authentication request for a provider."""
        provider = self.get_provider(provider_name)
        if provider:
            return provider.create_authn_request(relay_state)
        return None
    
    def handle_response(self, provider_name: str, saml_response: str, relay_state: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Handle SAML response from a provider."""
        provider = self.get_provider(provider_name)
        if provider:
            return provider.parse_saml_response(saml_response, relay_state)
        return None
    
    def create_logout_request(self, provider_name: str, name_id: str, session_index: Optional[str] = None) -> Optional[str]:
        """Create logout request for a provider."""
        provider = self.get_provider(provider_name)
        if provider:
            return provider.create_logout_request(name_id, session_index)
        return None

# Example configuration
def create_saml_manager(config: Dict[str, Dict[str, Any]]) -> SAMLManager:
    """Create and configure SAML manager."""
    manager = SAMLManager()
    
    for provider_name, provider_config in config.items():
        provider = SAMLProvider(
            entity_id=provider_config['entity_id'],
            acs_url=provider_config['acs_url'],
            sso_url=provider_config['sso_url'],
            slo_url=provider_config.get('slo_url'),
            x509_cert=provider_config.get('x509_cert'),
            private_key=provider_config.get('private_key'),
            idp_cert=provider_config.get('idp_cert'),
            attribute_mapping=provider_config.get('attribute_mapping')
        )
        manager.register_provider(provider_name, provider)
    
    return manager

