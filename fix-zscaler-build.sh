#!/bin/bash
# Fix for Zscaler SSL certificate issues during Docker build

echo "Fixing Zscaler SSL certificate issues..."

# Option 1: Use Dockerfile without certificate validation for Rust
echo "Creating simplified Dockerfile without SSL validation for Rust installation..."

cat > violentutf_api/fastapi_app/Dockerfile.simple << 'EOF'
# Multi-stage build for production
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ git build-essential pkg-config curl libssl-dev ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Rust with SSL verification disabled (for Zscaler environments)
ENV RUSTUP_HOME=/usr/local/rustup CARGO_HOME=/usr/local/cargo PATH=/usr/local/cargo/bin:$PATH
RUN curl -k --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
    sh -s -- -y --no-modify-path --profile minimal --default-toolchain stable && \
    chmod -R a+w $RUSTUP_HOME $CARGO_HOME

# Copy and install requirements
COPY requirements.txt requirements-minimal.txt ./
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git gcc g++ build-essential ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Rust for runtime
ENV RUSTUP_HOME=/usr/local/rustup CARGO_HOME=/usr/local/cargo PATH=/usr/local/cargo/bin:$PATH
RUN curl -k --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
    sh -s -- -y --no-modify-path --profile minimal --default-toolchain stable && \
    chmod -R a+w $RUSTUP_HOME $CARGO_HOME

# Copy wheels and install
COPY --from=builder /build/wheels /wheels
COPY requirements.txt ./
RUN pip install --no-cache /wheels/*

# Copy application
COPY . .

# Create directories and user
RUN mkdir -p app_data config logs && chmod 755 app_data config logs
RUN useradd -m -u 1000 fastapi && chown -R fastapi:fastapi /app
USER fastapi

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
EOF

# Backup original Dockerfile
cp violentutf_api/fastapi_app/Dockerfile violentutf_api/fastapi_app/Dockerfile.original

# Use simple Dockerfile
cp violentutf_api/fastapi_app/Dockerfile.simple violentutf_api/fastapi_app/Dockerfile

echo "✅ Created simplified Dockerfile that bypasses SSL verification"
echo ""
echo "You can now run: ./setup_macos.sh"
echo ""
echo "To restore original Dockerfile later:"
echo "  mv violentutf_api/fastapi_app/Dockerfile.original violentutf_api/fastapi_app/Dockerfile"
