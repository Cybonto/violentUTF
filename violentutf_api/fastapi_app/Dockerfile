# Multi-stage build for production with SSL bypass for corporate environments
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ git build-essential pkg-config curl libssl-dev ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Rust with SSL verification disabled (for Zscaler/corporate proxy environments)
ENV RUSTUP_HOME=/usr/local/rustup CARGO_HOME=/usr/local/cargo PATH=/usr/local/cargo/bin:$PATH
RUN curl -k --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
    sh -s -- -y --no-modify-path --profile minimal --default-toolchain stable && \
    chmod -R a+w $RUSTUP_HOME $CARGO_HOME

# Verify Rust installation
RUN rustc --version && cargo --version

# Copy and install requirements with trusted hosts
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

# Install Rust for runtime with SSL bypass
ENV RUSTUP_HOME=/usr/local/rustup CARGO_HOME=/usr/local/cargo PATH=/usr/local/cargo/bin:$PATH
RUN curl -k --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
    sh -s -- -y --no-modify-path --profile minimal --default-toolchain stable && \
    chmod -R a+w $RUSTUP_HOME $CARGO_HOME

# Copy wheels and install
COPY --from=builder /build/wheels /wheels
COPY requirements.txt ./
RUN pip install --no-cache /wheels/*

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