# Multi-stage build for production with Zscaler certificate support
FROM python:3.11-slim as builder

WORKDIR /build

# Set shell for pipefail support
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install build dependencies with version pinning
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc=4:11.2.0-1ubuntu1 \
    g++=4:11.2.0-1ubuntu1 \
    git=1:2.34.1-1ubuntu1.11 \
    build-essential=12.9ubuntu3 \
    pkg-config=0.29.2-1ubuntu3 \
    curl=7.81.0-1ubuntu1.18 \
    libssl-dev=3.0.2-0ubuntu1.18 \
    ca-certificates=20240203~22.04.1 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Zscaler certificates if they exist
# Using a more Docker-friendly approach
COPY zscaler.cr[t] CA.cr[t] /usr/local/share/ca-certificates/
RUN update-ca-certificates || true

# Set environment to use system certificates
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

# Install Rust with proper certificate handling
ENV RUSTUP_HOME=/usr/local/rustup CARGO_HOME=/usr/local/cargo PATH=/usr/local/cargo/bin:$PATH
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
    sh -s -- -y --no-modify-path --profile minimal --default-toolchain stable && \
    chmod -R a+w $RUSTUP_HOME $CARGO_HOME

# Verify Rust installation
RUN rustc --version && cargo --version

# Copy and install requirements
COPY requirements.txt requirements-minimal.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Set shell for pipefail support
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install runtime dependencies with version pinning
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl=7.81.0-1ubuntu1.18 \
    git=1:2.34.1-1ubuntu1.11 \
    gcc=4:11.2.0-1ubuntu1 \
    g++=4:11.2.0-1ubuntu1 \
    build-essential=12.9ubuntu3 \
    ca-certificates=20240203~22.04.1 \
    && rm -rf /var/lib/apt/lists/*

# Copy certificates from builder stage
COPY --from=builder /usr/local/share/ca-certificates/ /usr/local/share/ca-certificates/
RUN update-ca-certificates || true

# Set environment to use system certificates
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

# Install Rust for runtime
ENV RUSTUP_HOME=/usr/local/rustup CARGO_HOME=/usr/local/cargo PATH=/usr/local/cargo/bin:$PATH
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
    sh -s -- -y --no-modify-path --profile minimal --default-toolchain stable && \
    chmod -R a+w $RUSTUP_HOME $CARGO_HOME

# Copy wheels and install
COPY --from=builder /build/wheels /wheels
COPY requirements.txt ./
RUN pip install --no-cache-dir /wheels/*

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
