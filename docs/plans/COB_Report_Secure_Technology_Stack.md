# COB Report Enhancement - Secure Technology Stack

## Recommended Technology Changes for Security & Reliability

Based on security analysis, here are the recommended technology changes from the original proposal:

## 1. Task Scheduling (CRITICAL CHANGE)

### ❌ Original: Celery + Redis
**Problems:**
- Redis default config has no authentication
- External service = additional attack surface
- Celery pickle vulnerabilities
- Complex deployment

### ✅ Recommended: APScheduler + PostgreSQL
**Benefits:**
- No external services required
- Uses existing secured PostgreSQL
- Native Python integration
- Built-in misfire handling
- Better async/await support

```python
# Secure scheduling implementation
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

scheduler = AsyncIOScheduler(
    jobstores={
        'default': SQLAlchemyJobStore(url=secure_db_url)
    },
    job_defaults={
        'coalesce': True,
        'max_instances': 3,
        'misfire_grace_time': 30
    }
)
```

## 2. PDF Generation (SECURITY CHANGE)

### ❌ Original: ReportLab
**Problems:**
- XSS vulnerabilities with user input
- No built-in sanitization
- PDF injection risks

### ✅ Recommended: WeasyPrint + Bleach
**Benefits:**
- Automatic HTML sanitization
- CSS-based styling (more secure)
- Better HTML/CSS compliance
- No code injection vectors

```python
# Secure PDF generation
from weasyprint import HTML, CSS
import bleach

def secure_pdf_generation(html_content: str) -> bytes:
    # Sanitize HTML to prevent injection
    safe_html = bleach.clean(
        html_content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True
    )
    
    return HTML(string=safe_html).write_pdf()
```

## 3. Database Access (IMPROVEMENT)

### ❌ Original: Raw SQL with asyncpg
**Problems:**
- Manual SQL construction
- SQL injection risks
- No migration management

### ✅ Recommended: SQLAlchemy 2.0 + Alembic
**Benefits:**
- Automatic SQL injection prevention
- Type-safe query building
- Migration management
- Connection pooling

```python
# Secure database models
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, validates
import jsonschema

class ReportTemplate(Base):
    __tablename__ = 'cob_report_templates'
    
    template_config = Column(JSON, nullable=False)
    
    @validates('template_config')
    def validate_config(self, key, value):
        jsonschema.validate(value, TEMPLATE_SCHEMA)
        return value
```

## 4. AI Integration (SECURITY ENHANCEMENT)

### ❌ Original: Basic aiohttp calls
**Problems:**
- API keys in memory
- SSL verification disabled
- No rate limiting
- No request signing

### ✅ Recommended: Secure AI Client
**Benefits:**
- Encrypted API key storage
- Request signing
- Rate limiting
- SSL certificate verification

```python
# Secure AI integration
class SecureAIClient:
    def __init__(self):
        self.encryption_key = load_encryption_key()
        self.rate_limiter = AsyncRateLimiter(10, 60)
    
    async def make_request(self, provider: str, payload: dict):
        await self.rate_limiter.acquire()
        
        # Get encrypted API key
        api_key = self.decrypt_api_key(provider)
        
        # SSL verification enabled
        ssl_context = ssl.create_default_context()
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        
        # Sign request for integrity
        signature = self.sign_request(payload, api_key)
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'X-Signature': signature,
            'X-Request-ID': str(uuid.uuid4())
        }
        
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=ssl_context)
        ) as session:
            return await session.post(endpoint, json=payload, headers=headers)
```

## 5. Dependencies (SUPPLY CHAIN SECURITY)

### Recommended Secure Dependencies:

```toml
[tool.poetry.dependencies]
python = "^3.11"                    # Latest stable Python
fastapi = "^0.104.0"               # Latest FastAPI
sqlalchemy = "^2.0.0"              # SQLAlchemy 2.0 with async
weasyprint = "^60.0"               # Secure PDF generation
bleach = "^6.1.0"                  # HTML sanitization
cryptography = "^41.0.0"           # Encryption/decryption
pydantic = "^2.5.0"                # Data validation
python-jose = "^3.3.0"             # JWT handling
passlib = "^1.7.4"                 # Password hashing
apscheduler = "^3.10.0"            # Task scheduling
aiohttp = "^3.9.0"                 # HTTP client
tenacity = "^8.2.0"                # Retry logic
jsonschema = "^4.20.0"             # JSON validation
markupsafe = "^2.1.0"              # Template security

[tool.poetry.group.security.dependencies]
bandit = "^1.7.0"                  # Security linting
safety = "^3.0.0"                  # Vulnerability scanning
pip-audit = "^2.6.0"               # Dependency auditing
```

## 6. Container Security

### Secure Dockerfile:

```dockerfile
# Use specific version, not latest
FROM python:3.11.6-slim-bookworm

# Security updates
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && \
    useradd -r -g appuser -u 1000 appuser

# Install dependencies as root
COPY pyproject.toml poetry.lock ./
RUN pip install --no-cache-dir poetry && \
    poetry install --no-dev --no-interaction

# Switch to non-root user
USER appuser

# Copy application with proper ownership
COPY --chown=appuser:appuser . .

# Security environment
ENV PYTHONHASHSEED=random
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=3s \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 7. Security Scanning Pipeline

### GitHub Actions Security Workflow:

```yaml
name: Security Scan

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install --with security
      
      - name: Run Bandit security scan
        run: poetry run bandit -r . -f json -o bandit-report.json
      
      - name: Run pip-audit
        run: poetry run pip-audit --desc --format=json
      
      - name: Run Safety check
        run: poetry run safety check --json
      
      - name: Container vulnerability scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
```

## 8. Secret Management

### Secure Configuration:

```python
from pydantic import BaseSettings, SecretStr
from cryptography.fernet import Fernet
import hvac

class SecureSettings(BaseSettings):
    # Environment variables are encrypted
    database_url: SecretStr
    jwt_secret_key: SecretStr
    openai_api_key: SecretStr
    
    # Vault integration for production
    vault_url: str = "https://vault.company.com"
    vault_token: SecretStr
    
    def get_secret(self, key: str) -> str:
        """Retrieve secret from Vault or encrypted env var"""
        if self.vault_url and self.vault_token:
            client = hvac.Client(
                url=self.vault_url,
                token=self.vault_token.get_secret_value()
            )
            response = client.secrets.kv.v2.read_secret_version(
                path=f"cob-reports/{key}"
            )
            return response['data']['data']['value']
        
        # Fallback to encrypted environment variable
        encrypted_value = getattr(self, f"{key}_encrypted")
        fernet = Fernet(self.encryption_key)
        return fernet.decrypt(encrypted_value.encode()).decode()

settings = SecureSettings()
```

## 9. Runtime Security

### Security Headers and Middleware:

```python
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()

# Security middleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["violentutf.company.com", "localhost"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://violentutf.company.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response
```

## Implementation Priority

1. **Phase 1**: Replace Celery with APScheduler (Week 1)
2. **Phase 2**: Implement SQLAlchemy with migrations (Week 2)
3. **Phase 3**: Replace ReportLab with WeasyPrint (Week 3)
4. **Phase 4**: Add security scanning pipeline (Week 4)
5. **Phase 5**: Implement secret management (Week 5)

## Security Validation Checklist

- [ ] No hardcoded secrets in code
- [ ] All user input sanitized
- [ ] SQL injection prevention with ORM
- [ ] XSS prevention in PDF generation
- [ ] HTTPS enforced for all external calls
- [ ] Container runs as non-root user
- [ ] Dependencies scanned for vulnerabilities
- [ ] Security headers implemented
- [ ] Authentication and authorization enforced
- [ ] Audit logging enabled

This secure technology stack maintains all the original functionality while significantly improving security posture and reliability.