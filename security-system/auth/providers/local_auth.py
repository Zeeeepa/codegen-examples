"""
Local authentication provider with secure password handling and MFA support.
Implements bcrypt password hashing, account lockout, and TOTP-based MFA.
"""

import secrets
import base64
import qrcode
import io
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
import bcrypt
import pyotp
from email_validator import validate_email, EmailNotValidError

class PasswordPolicy:
    """Password policy configuration and validation."""
    
    def __init__(
        self,
        min_length: int = 8,
        max_length: int = 128,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digits: bool = True,
        require_special: bool = True,
        special_chars: str = "!@#$%^&*()_+-=[]{}|;:,.<>?",
        max_repeated_chars: int = 3,
        prevent_common_passwords: bool = True,
        prevent_personal_info: bool = True
    ):
        self.min_length = min_length
        self.max_length = max_length
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_digits = require_digits
        self.require_special = require_special
        self.special_chars = special_chars
        self.max_repeated_chars = max_repeated_chars
        self.prevent_common_passwords = prevent_common_passwords
        self.prevent_personal_info = prevent_personal_info
        
        # Common passwords to reject
        self.common_passwords = {
            'password', '123456', '123456789', 'qwerty', 'abc123',
            'password123', 'admin', 'letmein', 'welcome', 'monkey',
            'dragon', 'master', 'shadow', 'superman', 'michael',
            'football', 'baseball', 'liverpool', 'jordan', 'princess'
        }
    
    def validate_password(self, password: str, user_info: Optional[Dict[str, str]] = None) -> tuple[bool, List[str]]:
        """
        Validate password against policy.
        
        Args:
            password: Password to validate
            user_info: User information for personal info check
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Length check
        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters long")
        
        if len(password) > self.max_length:
            errors.append(f"Password must be no more than {self.max_length} characters long")
        
        # Character requirements
        if self.require_uppercase and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if self.require_lowercase and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if self.require_digits and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")
        
        if self.require_special and not any(c in self.special_chars for c in password):
            errors.append(f"Password must contain at least one special character: {self.special_chars}")
        
        # Repeated characters check
        if self.max_repeated_chars > 0:
            repeated_count = 1
            max_repeated = 1
            
            for i in range(1, len(password)):
                if password[i] == password[i-1]:
                    repeated_count += 1
                    max_repeated = max(max_repeated, repeated_count)
                else:
                    repeated_count = 1
            
            if max_repeated > self.max_repeated_chars:
                errors.append(f"Password cannot have more than {self.max_repeated_chars} repeated characters in a row")
        
        # Common passwords check
        if self.prevent_common_passwords and password.lower() in self.common_passwords:
            errors.append("Password is too common, please choose a different one")
        
        # Personal information check
        if self.prevent_personal_info and user_info:
            password_lower = password.lower()
            for field, value in user_info.items():
                if value and len(value) >= 3 and value.lower() in password_lower:
                    errors.append(f"Password cannot contain personal information ({field})")
        
        return len(errors) == 0, errors

class AccountLockoutPolicy:
    """Account lockout policy for failed login attempts."""
    
    def __init__(
        self,
        max_attempts: int = 5,
        lockout_duration_minutes: int = 30,
        progressive_lockout: bool = True,
        reset_attempts_after_minutes: int = 60
    ):
        self.max_attempts = max_attempts
        self.lockout_duration_minutes = lockout_duration_minutes
        self.progressive_lockout = progressive_lockout
        self.reset_attempts_after_minutes = reset_attempts_after_minutes
    
    def calculate_lockout_duration(self, attempt_count: int) -> timedelta:
        """Calculate lockout duration based on attempt count."""
        if not self.progressive_lockout:
            return timedelta(minutes=self.lockout_duration_minutes)
        
        # Progressive lockout: 30min, 1hr, 2hr, 4hr, 8hr, then 24hr max
        base_minutes = self.lockout_duration_minutes
        multiplier = min(2 ** (attempt_count - self.max_attempts), 48)  # Max 24 hours
        return timedelta(minutes=base_minutes * multiplier)
    
    def should_reset_attempts(self, last_attempt: datetime) -> bool:
        """Check if failed attempts should be reset."""
        time_since_last = datetime.now(timezone.utc) - last_attempt
        return time_since_last > timedelta(minutes=self.reset_attempts_after_minutes)

class LocalAuthProvider:
    """Local authentication provider with secure password handling."""
    
    def __init__(
        self,
        password_policy: Optional[PasswordPolicy] = None,
        lockout_policy: Optional[AccountLockoutPolicy] = None,
        bcrypt_rounds: int = 12
    ):
        self.password_policy = password_policy or PasswordPolicy()
        self.lockout_policy = lockout_policy or AccountLockoutPolicy()
        self.bcrypt_rounds = bcrypt_rounds
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        salt = bcrypt.gensalt(rounds=self.bcrypt_rounds)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception:
            return False
    
    def validate_email(self, email: str) -> tuple[bool, Optional[str]]:
        """Validate email address format."""
        try:
            validated_email = validate_email(email)
            return True, validated_email.email
        except EmailNotValidError as e:
            return False, str(e)
    
    def validate_password_policy(self, password: str, user_info: Optional[Dict[str, str]] = None) -> tuple[bool, List[str]]:
        """Validate password against policy."""
        return self.password_policy.validate_password(password, user_info)
    
    def check_account_lockout(self, user) -> tuple[bool, Optional[datetime]]:
        """
        Check if account is locked out.
        
        Returns:
            Tuple of (is_locked, unlock_time)
        """
        if not user.locked_until:
            return False, None
        
        now = datetime.now(timezone.utc)
        if now >= user.locked_until:
            return False, None
        
        return True, user.locked_until
    
    def handle_failed_login(self, user) -> Optional[datetime]:
        """
        Handle failed login attempt and return lockout time if applicable.
        
        Returns:
            Lockout time if account should be locked, None otherwise
        """
        now = datetime.now(timezone.utc)
        
        # Reset attempts if enough time has passed
        if user.last_login and self.lockout_policy.should_reset_attempts(user.last_login):
            user.failed_login_attempts = 0
        
        # Increment failed attempts
        user.failed_login_attempts += 1
        
        # Check if account should be locked
        if user.failed_login_attempts >= self.lockout_policy.max_attempts:
            lockout_duration = self.lockout_policy.calculate_lockout_duration(user.failed_login_attempts)
            user.locked_until = now + lockout_duration
            return user.locked_until
        
        return None
    
    def handle_successful_login(self, user):
        """Handle successful login - reset failed attempts and update last login."""
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.now(timezone.utc)
    
    def authenticate_user(self, email: str, password: str, user_model, db_session) -> tuple[bool, Optional[Any], Optional[str]]:
        """
        Authenticate user with email and password.
        
        Returns:
            Tuple of (success, user_object, error_message)
        """
        # Find user by email
        user = db_session.query(user_model).filter(user_model.email == email).first()
        if not user:
            return False, None, "Invalid email or password"
        
        # Check account status
        if not user.can_login():
            return False, None, "Account is not active or not verified"
        
        # Check account lockout
        is_locked, unlock_time = self.check_account_lockout(user)
        if is_locked:
            return False, None, f"Account is locked until {unlock_time.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        
        # Verify password
        if not user.password_hash or not self.verify_password(password, user.password_hash):
            lockout_time = self.handle_failed_login(user)
            db_session.commit()
            
            if lockout_time:
                return False, None, f"Invalid email or password. Account locked until {lockout_time.strftime('%Y-%m-%d %H:%M:%S UTC')}"
            else:
                remaining_attempts = self.lockout_policy.max_attempts - user.failed_login_attempts
                return False, None, f"Invalid email or password. {remaining_attempts} attempts remaining"
        
        # Successful authentication
        self.handle_successful_login(user)
        db_session.commit()
        
        return True, user, None

class MFAProvider:
    """Multi-factor authentication provider using TOTP."""
    
    def __init__(self, issuer_name: str = "AI Workflow Platform"):
        self.issuer_name = issuer_name
    
    def generate_secret(self) -> str:
        """Generate a new TOTP secret."""
        return pyotp.random_base32()
    
    def generate_qr_code(self, secret: str, user_email: str) -> bytes:
        """Generate QR code for TOTP setup."""
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user_email,
            issuer_name=self.issuer_name
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        return img_buffer.getvalue()
    
    def verify_totp(self, secret: str, token: str, window: int = 1) -> bool:
        """Verify TOTP token."""
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(token, valid_window=window)
        except Exception:
            return False
    
    def generate_backup_codes(self, count: int = 10) -> List[str]:
        """Generate backup codes for account recovery."""
        codes = []
        for _ in range(count):
            # Generate 8-character alphanumeric code
            code = secrets.token_hex(4).upper()
            codes.append(f"{code[:4]}-{code[4:]}")
        return codes
    
    def hash_backup_codes(self, codes: List[str]) -> List[str]:
        """Hash backup codes for secure storage."""
        hashed_codes = []
        for code in codes:
            # Remove hyphens and convert to lowercase for hashing
            clean_code = code.replace('-', '').lower()
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(clean_code.encode('utf-8'), salt)
            hashed_codes.append(hashed.decode('utf-8'))
        return hashed_codes
    
    def verify_backup_code(self, code: str, hashed_codes: List[str]) -> tuple[bool, Optional[str]]:
        """
        Verify backup code and return the hash to remove.
        
        Returns:
            Tuple of (is_valid, hash_to_remove)
        """
        clean_code = code.replace('-', '').lower()
        
        for hashed_code in hashed_codes:
            try:
                if bcrypt.checkpw(clean_code.encode('utf-8'), hashed_code.encode('utf-8')):
                    return True, hashed_code
            except Exception:
                continue
        
        return False, None
    
    def setup_mfa(self, user, db_session) -> tuple[str, List[str], bytes]:
        """
        Set up MFA for a user.
        
        Returns:
            Tuple of (secret, backup_codes, qr_code_image)
        """
        # Generate secret and backup codes
        secret = self.generate_secret()
        backup_codes = self.generate_backup_codes()
        hashed_backup_codes = self.hash_backup_codes(backup_codes)
        
        # Generate QR code
        qr_code = self.generate_qr_code(secret, user.email)
        
        # Update user record
        user.mfa_secret = secret
        user.backup_codes = hashed_backup_codes
        user.mfa_enabled = True
        
        db_session.commit()
        
        return secret, backup_codes, qr_code
    
    def verify_mfa(self, user, token: str) -> tuple[bool, str]:
        """
        Verify MFA token (TOTP or backup code).
        
        Returns:
            Tuple of (is_valid, token_type)
        """
        if not user.mfa_enabled or not user.mfa_secret:
            return False, "mfa_not_enabled"
        
        # Try TOTP first
        if self.verify_totp(user.mfa_secret, token):
            return True, "totp"
        
        # Try backup codes
        if user.backup_codes:
            is_valid, hash_to_remove = self.verify_backup_code(token, user.backup_codes)
            if is_valid and hash_to_remove:
                # Remove used backup code
                user.backup_codes.remove(hash_to_remove)
                return True, "backup_code"
        
        return False, "invalid_token"

# Example usage
def create_local_auth_provider(config: Dict[str, Any]) -> LocalAuthProvider:
    """Create local authentication provider with configuration."""
    password_config = config.get('password_policy', {})
    lockout_config = config.get('lockout_policy', {})
    
    password_policy = PasswordPolicy(
        min_length=password_config.get('min_length', 8),
        max_length=password_config.get('max_length', 128),
        require_uppercase=password_config.get('require_uppercase', True),
        require_lowercase=password_config.get('require_lowercase', True),
        require_digits=password_config.get('require_digits', True),
        require_special=password_config.get('require_special', True),
        max_repeated_chars=password_config.get('max_repeated_chars', 3)
    )
    
    lockout_policy = AccountLockoutPolicy(
        max_attempts=lockout_config.get('max_attempts', 5),
        lockout_duration_minutes=lockout_config.get('lockout_duration_minutes', 30),
        progressive_lockout=lockout_config.get('progressive_lockout', True)
    )
    
    return LocalAuthProvider(
        password_policy=password_policy,
        lockout_policy=lockout_policy,
        bcrypt_rounds=config.get('bcrypt_rounds', 12)
    )

