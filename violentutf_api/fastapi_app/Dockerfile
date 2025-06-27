# Multi-stage build for production
# Updated to Python 3.11 for PyRIT and Garak compatibility
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies for PyRIT and Garak (including Rust for base2048)
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

# Install Rust toolchain for base2048 dependency
ENV RUSTUP_HOME=/usr/local/rustup \
    CARGO_HOME=/usr/local/cargo \
    PATH=/usr/local/cargo/bin:$PATH

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
    sh -s -- -y --no-modify-path --profile minimal --default-toolchain stable && \
    chmod -R a+w $RUSTUP_HOME $CARGO_HOME

# Verify Rust installation
RUN rustc --version && cargo --version

# Copy requirements and install dependencies
COPY requirements.txt requirements-minimal.txt ./

# Install dependencies directly in builder stage to ensure they compile
RUN pip install --no-cache-dir -r requirements.txt && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies for PyRIT and Garak
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Rust for runtime compilation if needed
ENV RUSTUP_HOME=/usr/local/rustup \
    CARGO_HOME=/usr/local/cargo \
    PATH=/usr/local/cargo/bin:$PATH

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
    sh -s -- -y --no-modify-path --profile minimal --default-toolchain stable && \
    chmod -R a+w $RUSTUP_HOME $CARGO_HOME

# Copy wheels from builder and install
COPY --from=builder /build/wheels /wheels
COPY requirements.txt ./
RUN pip install --no-cache /wheels/*

# Verify PyRIT and Garak installation
COPY verify_redteam_install.py .
RUN python verify_redteam_install.py && \
    echo "✅ PyRIT and Garak verification completed successfully"

# Copy application
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p app_data config logs && \
    chmod 755 app_data config logs

# Create non-root user
RUN useradd -m -u 1000 fastapi && \
    chown -R fastapi:fastapi /app

# Switch to non-root user
USER fastapi

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]