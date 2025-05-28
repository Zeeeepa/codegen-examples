# 🔐 Security & Authentication System

A comprehensive enterprise-grade security and authentication system for the AI Workflow Platform. This system provides secure access control, multi-factor authentication, secret management, and comprehensive audit logging with compliance reporting capabilities.

## 🌟 Features

### Authentication & Authorization
- **Multi-factor Authentication (MFA)** - TOTP-based with backup codes
- **OAuth2 Integration** - Google, GitHub, Microsoft providers
- **SAML 2.0 Support** - Enterprise SSO integration
- **Local Authentication** - Secure password-based auth with bcrypt
- **Role-Based Access Control (RBAC)** - Granular permission system
- **API Key Management** - Secure generation, rotation, and validation

### Secret Management
- **HashiCorp Vault Integration** - Secure secret storage and rotation
- **AWS Secrets Manager Support** - Cloud-native secret management
- **Automatic Secret Rotation** - Scheduled rotation with zero downtime
- **Encryption at Rest** - AES-256 encryption for sensitive data

### Security Features
- **JWT Token Management** - Secure token generation and validation
- **Session Management** - Comprehensive session tracking and control
- **Rate Limiting** - Protection against brute force attacks
- **Account Lockout** - Progressive lockout policies
- **Security Headers** - OWASP-compliant security headers

### Audit & Compliance
- **Comprehensive Audit Logging** - All security events tracked
- **Compliance Reporting** - SOC2, GDPR, PCI DSS, HIPAA support
- **Event Correlation** - Related event tracking and analysis
- **Real-time Monitoring** - Security event alerting

### Frontend Components
- **React Authentication UI** - Modern, responsive login forms
- **MFA Setup Components** - User-friendly MFA configuration
- **User Management Dashboard** - Admin interface for user management
- **Audit Dashboard** - Security event visualization

## 🏗️ Architecture

```
security-system/
├── auth/                    # Authentication core
│   ├── providers/          # Auth providers (OAuth2, SAML, local)
│   ├── middleware/         # FastAPI middleware
│   ├── models/            # Database models
│   └── services/          # Business logic services
├── secrets/               # Secret management
│   ├── vault_client.py    # HashiCorp Vault client
│   ├── aws_secrets.py     # AWS Secrets Manager
│   └── rotation_scheduler.py # Automatic rotation
├── audit/                 # Audit logging system
│   ├── audit_logger.py    # Core logging service
│   ├── event_processor.py # Event processing
│   └── compliance_reporter.py # Compliance reports
├── security/              # Security utilities
│   ├── vulnerability_scanner.py # Security scanning
│   ├── threat_detector.py # Threat detection
│   └── security_policies.py # Policy enforcement
├── frontend/              # React components
│   ├── components/        # UI components
│   └── services/         # API services
└── deployment/           # Deployment configs
    ├── vault-config/     # Vault configuration
    ├── security-policies/ # Security policies
    └── compliance-templates/ # Compliance templates
```

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL 12+
- Redis 6+
- HashiCorp Vault (optional)
- Node.js 18+ (for frontend)

### Installation

1. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

2. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Initialize database:**
```bash
alembic upgrade head
```

4. **Start the services:**
```bash
# Start FastAPI server
uvicorn main:app --reload

# Start Redis (for caching and rate limiting)
redis-server

# Start Vault (optional)
vault server -dev
```

### Configuration

#### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost/security_db

# JWT Configuration
JWT_SECRET_KEY=your-super-secret-jwt-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# OAuth2 Providers
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret

# SAML Configuration
SAML_ENTITY_ID=https://your-app.com
SAML_ACS_URL=https://your-app.com/auth/saml/acs
SAML_SSO_URL=https://idp.example.com/sso
SAML_IDP_CERT=path/to/idp-cert.pem

# Vault Configuration
VAULT_URL=https://vault.example.com:8200
VAULT_TOKEN=your-vault-token

# AWS Secrets Manager
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-west-2

# Redis
REDIS_URL=redis://localhost:6379

# Email Configuration (for notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

## 📚 Usage Examples

### Basic Authentication

```python
from fastapi import FastAPI, Depends
from security_system.auth.middleware import require_auth, require_permission

app = FastAPI()

@app.get("/protected")
async def protected_endpoint(user = Depends(require_auth)):
    return {"message": f"Hello {user.email}!"}

@app.get("/admin-only")
async def admin_endpoint(user = Depends(require_permission("system:manage"))):
    return {"message": "Admin access granted"}
```

### MFA Setup

```python
from security_system.auth.providers.local_auth import MFAProvider

mfa_provider = MFAProvider()

# Setup MFA for user
secret, backup_codes, qr_code = mfa_provider.setup_mfa(user, db_session)

# Verify MFA token
is_valid, token_type = mfa_provider.verify_mfa(user, "123456")
```

### Secret Management

```python
from security_system.secrets.vault_client import VaultClient

vault = VaultClient(
    url="https://vault.example.com:8200",
    auth_method="token",
    auth_config={"token": "hvs.CAESIJ..."}
)

# Store secret
vault.write_secret("myapp/database", {
    "username": "dbuser",
    "password": "secure-password"
})

# Retrieve secret
secret_data = vault.read_secret("myapp/database")
```

### Audit Logging

```python
from security_system.audit.audit_logger import AuditLogger, AuditEventType, AuditSeverity

audit_logger = AuditLogger(db_session_factory)

# Log authentication event
audit_logger.log_authentication_event(
    AuditEventType.LOGIN_SUCCESS,
    user_id="user-123",
    ip_address="192.168.1.100",
    user_agent="Mozilla/5.0...",
    outcome="success"
)

# Log resource access
audit_logger.log_resource_access(
    user_id="user-123",
    resource_type="secret",
    resource_id="myapp/database",
    action="read",
    ip_address="192.168.1.100"
)
```

## 🔧 API Endpoints

### Authentication Endpoints

- `POST /auth/login` - Local authentication
- `POST /auth/logout` - Logout user
- `POST /auth/refresh` - Refresh access token
- `GET /auth/oauth2/{provider}/url` - Get OAuth2 auth URL
- `POST /auth/oauth2/{provider}/callback` - Handle OAuth2 callback
- `GET /auth/saml/{provider}/url` - Get SAML auth URL
- `POST /auth/saml/{provider}/callback` - Handle SAML callback

### MFA Endpoints

- `POST /auth/mfa/setup` - Setup MFA
- `POST /auth/mfa/enable` - Enable MFA
- `POST /auth/mfa/disable` - Disable MFA
- `POST /auth/mfa/verify` - Verify MFA token

### User Management

- `GET /auth/profile` - Get user profile
- `PUT /auth/profile` - Update user profile
- `POST /auth/change-password` - Change password
- `GET /auth/sessions` - Get user sessions
- `DELETE /auth/sessions/{id}` - Revoke session

### API Key Management

- `GET /auth/api-keys` - List API keys
- `POST /auth/api-keys` - Create API key
- `DELETE /auth/api-keys/{id}` - Delete API key

## 🛡️ Security Features

### Password Policy

- Minimum 8 characters
- Requires uppercase, lowercase, digits, and special characters
- Prevents common passwords
- Prevents personal information in passwords
- Maximum 3 repeated characters

### Account Lockout

- 5 failed attempts trigger lockout
- Progressive lockout duration (30min, 1hr, 2hr, 4hr, 8hr, 24hr max)
- Automatic reset after 60 minutes of inactivity

### Session Security

- Secure session tokens with entropy
- Session expiration and renewal
- Device fingerprinting
- IP address tracking
- Concurrent session limits

### API Security

- Rate limiting (100 requests/minute per IP)
- API key authentication with scopes
- Request/response validation
- CORS protection
- Security headers (HSTS, CSP, etc.)

## 📊 Compliance & Reporting

### Supported Frameworks

- **SOC 2** - System and Organization Controls
- **GDPR** - General Data Protection Regulation
- **PCI DSS** - Payment Card Industry Data Security Standard
- **HIPAA** - Health Insurance Portability and Accountability Act

### Audit Events

All security-relevant events are logged with:
- Event type and severity
- User identification
- Timestamp and IP address
- Resource and action details
- Compliance framework tags
- Correlation IDs for related events

### Reports

- User access reports
- Failed login attempts
- Permission changes
- Secret access logs
- Compliance violation alerts

## 🔄 Secret Rotation

### Automatic Rotation

```python
from security_system.secrets.rotation_scheduler import RotationScheduler

scheduler = RotationScheduler(vault_client)

# Schedule daily rotation for database passwords
scheduler.schedule_rotation(
    secret_path="myapp/database",
    rotation_interval="daily",
    rotation_function=rotate_database_password
)
```

### Manual Rotation

```python
# Rotate specific secret
new_secret = vault.rotate_secret("myapp/api-key")

# Rotate with custom generator
vault.rotate_secret("myapp/password", generator=generate_strong_password)
```

## 🧪 Testing

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=security_system --cov-report=html

# Run specific test categories
pytest tests/auth/
pytest tests/secrets/
pytest tests/audit/
```

### Test Configuration

```python
# tests/conftest.py
import pytest
from security_system.auth.models import User, Role
from security_system.test_utils import create_test_user

@pytest.fixture
def test_user(db_session):
    return create_test_user(
        email="test@example.com",
        password="TestPassword123!",
        roles=["user"]
    )
```

## 📈 Monitoring & Alerting

### Metrics

- Authentication success/failure rates
- MFA adoption rates
- API key usage statistics
- Session duration analytics
- Security event frequencies

### Alerts

- Multiple failed login attempts
- Privilege escalation attempts
- Unusual access patterns
- Secret access violations
- Compliance policy violations

## 🚀 Deployment

### Docker Deployment

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: security-system
spec:
  replicas: 3
  selector:
    matchLabels:
      app: security-system
  template:
    metadata:
      labels:
        app: security-system
    spec:
      containers:
      - name: security-system
        image: security-system:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: security-secrets
              key: database-url
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:
- Create an issue in the GitHub repository
- Contact the security team at security@company.com
- Check the documentation at https://docs.company.com/security

## 🔗 Related Projects

- [AI Workflow Platform](https://github.com/company/ai-workflow-platform)
- [Task Manager MCP](https://github.com/company/task-manager-mcp)
- [Webhook Orchestrator](https://github.com/company/webhook-orchestrator)

