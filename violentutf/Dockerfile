# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Determine the correct Python command (python3 or python) and upgrade pip
# This script checks for python3 first, then python.
# It then uses the determined command to upgrade pip.
RUN if command -v python3 >/dev/null 2>&1; then \
        PYTHON_EXECUTABLE="python3"; \
    elif command -v python >/dev/null 2>&1; then \
        PYTHON_EXECUTABLE="python"; \
    else \
        echo "ERROR: Neither python3 nor python found in PATH." >&2; \
        exit 1; \
    fi && \
    echo "Using $PYTHON_EXECUTABLE to upgrade pip" && \
    $PYTHON_EXECUTABLE -m pip install --no-cache-dir --upgrade pip

# Install curl, build-essential (if not already present, needed for Rust), then Rust and Cargo
# Adjust package manager commands (apt-get) if your base image is not Debian/Ubuntu-based
RUN apt-get update && apt-get install -y curl build-essential \
    && curl https://sh.rustup.rs -sSf | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Install system dependencies
# libgraphviz-dev is needed for pygraphviz, which might be a sub-dependency of pyrit/garak
# pkg-config is often needed for building some Python packages with C extensions
RUN apt-get update && \
    apt-get install -y --no-install-recommends libgraphviz-dev pkg-config gcc && \
    rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# --no-cache-dir reduces image size
# --default-timeout can be increased if pip has issues downloading large packages on slow connections
RUN pip install --no-cache-dir --default-timeout=300 -r requirements.txt

# Copy the rest of the application code into the container
# This includes Home.py, pages/, app_data/, custom_targets/, etc.
# Ensure .dockerignore is present in the context directory (./violentutf)
# to exclude unnecessary files from being copied.
COPY . .

# Create app_logs directory (logs will be written here and can be mounted as a volume)
RUN mkdir -p /app/app_logs

# Make port 8501 available to the world outside this container (Streamlit default port)
EXPOSE 8501

# Run Home.py when the container launches
# Using a list format for CMD is preferred
ENTRYPOINT ["streamlit", "run", "Home.py", "--server.port=8501", "--server.address=0.0.0.0"]
