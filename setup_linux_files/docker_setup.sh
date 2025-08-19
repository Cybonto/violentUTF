#!/usr/bin/env bash
# docker_setup.sh - Docker installation and setup for Linux

# Function to install Docker on various Linux distributions
install_docker() {
    local distro=$(detect_distro)
    
    log_progress "Installing Docker for $distro..."
    
    case "$distro" in
        ubuntu|debian)
            install_docker_debian
            ;;
        fedora|centos|rhel)
            install_docker_rhel
            ;;
        arch|manjaro)
            install_docker_arch
            ;;
        opensuse*)
            install_docker_opensuse
            ;;
        *)
            log_error "Unsupported distribution: $distro"
            log_info "Please install Docker manually from https://docs.docker.com/install/"
            return 1
            ;;
    esac
}

# Function to install Docker on Debian/Ubuntu
install_docker_debian() {
    log_detail "Installing Docker on Debian/Ubuntu..."
    
    # Update package index
    apt-get update
    
    # Install prerequisites
    apt-get install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release
    
    # Add Docker's official GPG key
    curl -fsSL https://download.docker.com/linux/$(lsb_release -is | tr '[:upper:]' '[:lower:]')/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # Set up the stable repository
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/$(lsb_release -is | tr '[:upper:]' '[:lower:]') \
        $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Update package index again
    apt-get update
    
    # Install Docker Engine
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    
    log_success "Docker installed successfully on Debian/Ubuntu"
}

# Function to install Docker on RHEL/CentOS/Fedora
install_docker_rhel() {
    log_detail "Installing Docker on RHEL/CentOS/Fedora..."
    
    # Remove old versions
    yum remove -y docker \
        docker-client \
        docker-client-latest \
        docker-common \
        docker-latest \
        docker-latest-logrotate \
        docker-logrotate \
        docker-engine
    
    # Install required packages
    yum install -y yum-utils
    
    # Set up the repository
    yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    
    # Install Docker Engine
    yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    
    log_success "Docker installed successfully on RHEL/CentOS/Fedora"
}

# Function to install Docker on Arch Linux
install_docker_arch() {
    log_detail "Installing Docker on Arch Linux..."
    
    # Install Docker
    pacman -Sy --noconfirm docker docker-compose
    
    log_success "Docker installed successfully on Arch Linux"
}

# Function to install Docker on openSUSE
install_docker_opensuse() {
    log_detail "Installing Docker on openSUSE..."
    
    # Install Docker
    zypper install -y docker docker-compose
    
    log_success "Docker installed successfully on openSUSE"
}

# Function to verify Docker installation
verify_docker_setup() {
    log_progress "Verifying Docker installation..."
    
    # Check if Docker is installed
    if ! command_exists docker; then
        log_error "Docker is not installed"
        return 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info >/dev/null 2>&1; then
        log_warn "Docker daemon is not running"
        
        # Try to start Docker
        log_progress "Starting Docker daemon..."
        systemctl start docker
        
        # Enable Docker to start on boot
        systemctl enable docker
        
        # Check again
        if ! docker info >/dev/null 2>&1; then
            log_error "Failed to start Docker daemon"
            return 1
        fi
    fi
    
    # Check Docker version
    local docker_version=$(docker --version | awk '{print $3}' | sed 's/,$//')
    log_success "Docker $docker_version is installed and running"
    
    # Check if docker-compose is available
    if docker compose version >/dev/null 2>&1; then
        local compose_version=$(docker compose version | awk '{print $4}')
        log_success "Docker Compose $compose_version is available"
        export DOCKER_COMPOSE_CMD="docker compose"
    elif command_exists docker-compose; then
        local compose_version=$(docker-compose --version | awk '{print $3}' | sed 's/,$//')
        log_success "Docker Compose $compose_version is available (standalone)"
        export DOCKER_COMPOSE_CMD="docker-compose"
    else
        log_error "Docker Compose is not available"
        return 1
    fi
    
    # Add current user to docker group if not already
    if ! groups | grep -q docker; then
        log_progress "Adding current user to docker group..."
        usermod -aG docker $SUDO_USER
        log_warn "You may need to log out and back in for group changes to take effect"
    fi
    
    return 0
}

# Function to create shared Docker network
create_shared_network() {
    log_progress "Creating shared Docker network: $SHARED_NETWORK_NAME"
    
    if docker network ls | grep -q "$SHARED_NETWORK_NAME"; then
        log_detail "Network $SHARED_NETWORK_NAME already exists"
    else
        docker network create "$SHARED_NETWORK_NAME"
        log_success "Created shared network: $SHARED_NETWORK_NAME"
    fi
}

# Function to handle SSL certificate issues
handle_ssl_certificate_issues() {
    log_detail "Checking for SSL certificate issues..."
    
    # Install ca-certificates if not present
    if ! command_exists update-ca-certificates; then
        log_progress "Installing ca-certificates..."
        install_packages ca-certificates
    fi
    
    # Update CA certificates
    log_progress "Updating CA certificates..."
    update-ca-certificates
    
    log_success "SSL certificates updated"
}