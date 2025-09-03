# Multi-stage build for production with Zscaler certificate support
FROM python:3.11-slim as builder

WORKDIR /build

# Corporate environment SSL certificate handling for Zscaler/corporate proxies
# These help bypass SSL verification issues during build
ENV PYTHONHTTPSVERIFY=0
ENV CURL_CA_BUNDLE=""
ENV REQUESTS_CA_BUNDLE=""
ENV SSL_VERIFY=false

# Set shell for pipefail support
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install build dependencies with version pinning
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    git \
    build-essential \
    pkg-config \
    curl \
    libssl-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Zscaler certificates if they exist
# Using a more Docker-friendly approach
COPY zscaler.cr[t] CA.cr[t] /usr/local/share/ca-certificates/
RUN update-ca-certificates || true

# Set environment to use system certificates
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

# Install Rust with corporate firewall/Zscaler support
ENV RUSTUP_HOME=/usr/local/rustup CARGO_HOME=/usr/local/cargo PATH=/usr/local/cargo/bin:$PATH

# Corporate environment SSL handling for Rust installation
# Try with certificates first, fallback to insecure if needed
RUN set +e && \
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
    sh -s -- -y --no-modify-path --profile minimal --default-toolchain stable; \
    if [ $? -ne 0 ]; then \
        echo "Standard SSL failed, trying with insecure connection (corporate environment)..."; \
        curl --proto '=https' --tlsv1.2 -sSf -k https://sh.rustup.rs | \
        sh -s -- -y --no-modify-path --profile minimal --default-toolchain stable; \
    fi && \
    chmod -R a+w $RUSTUP_HOME $CARGO_HOME

# Verify Rust installation
RUN rustc --version && cargo --version

# Copy and install requirements
# Copy and install requirements with corporate SSL bypass
COPY requirements.txt requirements-minimal.txt ./
RUN pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --no-cache-dir -r requirements.txt && \
    pip wheel --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Corporate environment SSL certificate handling (runtime stage)
ENV PYTHONHTTPSVERIFY=0
ENV CURL_CA_BUNDLE=""
ENV REQUESTS_CA_BUNDLE=""
ENV SSL_VERIFY=false

# Set shell for pipefail support
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install runtime dependencies without version pinning for compatibility
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    gcc \
    g++ \
    build-essential \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy certificates from builder stage
COPY --from=builder /usr/local/share/ca-certificates/ /usr/local/share/ca-certificates/
RUN update-ca-certificates || true

# Set environment to use system certificates
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

# Install Rust for runtime with corporate firewall support
ENV RUSTUP_HOME=/usr/local/rustup CARGO_HOME=/usr/local/cargo PATH=/usr/local/cargo/bin:$PATH
RUN set +e && \
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
    sh -s -- -y --no-modify-path --profile minimal --default-toolchain stable; \
    if [ $? -ne 0 ]; then \
        echo "Standard SSL failed, trying with insecure connection (corporate environment)..."; \
        curl --proto '=https' --tlsv1.2 -sSf -k https://sh.rustup.rs | \
        sh -s -- -y --no-modify-path --profile minimal --default-toolchain stable; \
    fi && \
    chmod -R a+w $RUSTUP_HOME $CARGO_HOME

# Copy wheels and install
COPY --from=builder /build/wheels /wheels
COPY requirements.txt ./
RUN pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --no-cache-dir /wheels/*

# Verify PyRIT and Garak installation
COPY verify_redteam_install.py .
RUN python verify_redteam_install.py && \
    echo "✅ PyRIT and Garak verification completed successfully"

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
