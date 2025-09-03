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

# Copy corporate certificates if they exist (Zscaler, enterprise CA, etc.)
# Support multiple certificate file formats and names based on existing docs
COPY zscaler.cr[t] CA.cr[t] zscaler.pe[m] enterprise-ca.cr[t] corporate.cr[t] /usr/local/share/ca-certificates/
RUN update-ca-certificates || true

# Set environment to use system certificates
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

# Install Rust with comprehensive corporate firewall/Zscaler support
ENV RUSTUP_HOME=/usr/local/rustup CARGO_HOME=/usr/local/cargo PATH=/usr/local/cargo/bin:$PATH

# Corporate environment: Global SSL bypass for all curl operations
# Create system-wide curl configuration
RUN echo "insecure" > ~/.curlrc && \
    echo "insecure" > /etc/curlrc && \
    mkdir -p /root/.config && \
    echo "insecure" > /root/.config/curlrc

# Set comprehensive environment variables for SSL bypass
ENV CURL_CA_BUNDLE=""
ENV RUSTUP_USE_CURL=1
ENV RUSTUP_INIT_SKIP_PATH_CHECK=yes

# Corporate environment: Skip Rust installer entirely and download toolchain directly
# This bypasses all SSL certificate issues with rustup's internal downloads
RUN set -e && \
    # Detect architecture
    ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then \
        RUST_ARCH="x86_64-unknown-linux-gnu"; \
    elif [ "$ARCH" = "aarch64" ]; then \
        RUST_ARCH="aarch64-unknown-linux-gnu"; \
    else \
        echo "Unsupported architecture: $ARCH" && exit 1; \
    fi && \
    echo "Installing Rust for architecture: $RUST_ARCH" && \
    \
    # Download Rust toolchain directly without rustup installer
    RUST_VERSION="1.70.0" && \
    RUST_URL="https://static.rust-lang.org/dist/rust-${RUST_VERSION}-${RUST_ARCH}.tar.gz" && \
    echo "Downloading Rust from: $RUST_URL" && \
    curl --insecure -sSfL "$RUST_URL" -o /tmp/rust.tar.gz && \
    \
    # Extract and install Rust
    WORKDIR /tmp && \
    tar -xzf rust.tar.gz && \
    WORKDIR "rust-\${RUST_VERSION}-\${RUST_ARCH}" && \
    ./install.sh --prefix=/usr/local && \
    \
    # Cleanup
    WORKDIR / && \
    rm -rf /tmp/rust* && \
    \
    # Set up environment
    echo "export PATH=\"/usr/local/bin:\$PATH\"" >> /etc/profile && \
    chmod -R a+w /usr/local/lib/rustlib || true

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

# Hugging Face and ML model download SSL bypass for corporate environments
ENV HF_HUB_DISABLE_SSL=1
ENV TRANSFORMERS_OFFLINE=0
ENV HF_DATASETS_OFFLINE=0
ENV TORCH_HOME=/tmp/torch_cache
ENV TRANSFORMERS_CACHE=/tmp/transformers_cache
ENV HF_HOME=/tmp/hf_cache

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

# Install Rust for runtime with comprehensive corporate firewall support
ENV RUSTUP_HOME=/usr/local/rustup CARGO_HOME=/usr/local/cargo PATH=/usr/local/cargo/bin:$PATH

# Corporate environment: Global SSL bypass for all curl operations (runtime)
RUN echo "insecure" > ~/.curlrc && \
    echo "insecure" > /etc/curlrc && \
    mkdir -p /root/.config && \
    echo "insecure" > /root/.config/curlrc

# Set comprehensive environment variables for SSL bypass (runtime)
ENV CURL_CA_BUNDLE=""
ENV RUSTUP_USE_CURL=1
ENV RUSTUP_INIT_SKIP_PATH_CHECK=yes

# Corporate environment: Skip Rust installer entirely and download toolchain directly (runtime)
# This bypasses all SSL certificate issues with rustup's internal downloads
RUN set -e && \
    # Detect architecture
    ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then \
        RUST_ARCH="x86_64-unknown-linux-gnu"; \
    elif [ "$ARCH" = "aarch64" ]; then \
        RUST_ARCH="aarch64-unknown-linux-gnu"; \
    else \
        echo "Unsupported architecture: $ARCH" && exit 1; \
    fi && \
    echo "Installing Rust for architecture: $RUST_ARCH" && \
    \
    # Download Rust toolchain directly without rustup installer
    RUST_VERSION="1.70.0" && \
    RUST_URL="https://static.rust-lang.org/dist/rust-${RUST_VERSION}-${RUST_ARCH}.tar.gz" && \
    echo "Downloading Rust from: $RUST_URL" && \
    curl --insecure -sSfL "$RUST_URL" -o /tmp/rust.tar.gz && \
    \
    # Extract and install Rust
    WORKDIR /tmp && \
    tar -xzf rust.tar.gz && \
    WORKDIR "rust-\${RUST_VERSION}-\${RUST_ARCH}" && \
    ./install.sh --prefix=/usr/local && \
    \
    # Cleanup
    WORKDIR / && \
    rm -rf /tmp/rust* && \
    \
    # Set up environment
    echo "export PATH=\"/usr/local/bin:\$PATH\"" >> /etc/profile && \
    chmod -R a+w /usr/local/lib/rustlib || true

# Copy wheels and install
COPY --from=builder /build/wheels /wheels
COPY requirements.txt ./
RUN pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --no-cache-dir /wheels/*

# Verify PyRIT and Garak installation with SSL bypass
COPY verify_redteam_install.py .
RUN PYTHONHTTPSVERIFY=0 SSL_VERIFY=false python verify_redteam_install.py && \
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
