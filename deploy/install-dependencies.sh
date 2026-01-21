#!/bin/bash
# Ombudsman Validation Studio - Ubuntu 24.04 Dependency Installation Script
# Run as root or with sudo

set -e

echo "=========================================="
echo "Ombudsman Validation Studio - Dependencies"
echo "Ubuntu 24.04 LTS Installation Script"
echo "=========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root or with sudo"
    exit 1
fi

# Update system
echo "[1/8] Updating system packages..."
apt-get update && apt-get upgrade -y

# Install base dependencies
echo "[2/8] Installing base dependencies..."
apt-get install -y \
    curl \
    wget \
    gnupg \
    ca-certificates \
    apt-transport-https \
    software-properties-common \
    build-essential \
    git \
    unzip

# Install Python 3.11
echo "[3/8] Installing Python 3.11..."
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update
apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Set Python 3.11 as default python3
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Install Node.js 20.x
echo "[4/8] Installing Node.js 20.x..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# Install ODBC drivers for SQL Server
echo "[5/8] Installing Microsoft ODBC Driver 18 for SQL Server..."
apt-get install -y unixodbc unixodbc-dev

# Add Microsoft repository
curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg
curl -fsSL https://packages.microsoft.com/config/ubuntu/24.04/prod.list -o /etc/apt/sources.list.d/mssql-release.list
sed -i 's|http://|[signed-by=/usr/share/keyrings/microsoft-prod.gpg] http://|' /etc/apt/sources.list.d/mssql-release.list

apt-get update
ACCEPT_EULA=Y apt-get install -y msodbcsql18 mssql-tools18

# Add mssql-tools to PATH for all users
echo 'export PATH="$PATH:/opt/mssql-tools18/bin"' >> /etc/profile.d/mssql-tools.sh
chmod +x /etc/profile.d/mssql-tools.sh

# Install Nginx
echo "[6/8] Installing Nginx..."
apt-get install -y nginx

# Install Certbot for Let's Encrypt SSL
echo "[7/8] Installing Certbot for SSL..."
apt-get install -y certbot python3-certbot-nginx

# Install Ollama
echo "[8/8] Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

# Install serve globally for frontend
npm install -g serve

# Create application user
echo "Creating application user 'ombudsman'..."
if ! id "ombudsman" &>/dev/null; then
    useradd -r -m -s /bin/bash ombudsman
fi

# Create application directories
echo "Creating application directories..."
mkdir -p /opt/ombudsman
mkdir -p /opt/ombudsman/backend
mkdir -p /opt/ombudsman/frontend
mkdir -p /opt/ombudsman/core
mkdir -p /var/lib/ombudsman/data
mkdir -p /var/log/ombudsman

# Set ownership
chown -R ombudsman:ombudsman /opt/ombudsman
chown -R ombudsman:ombudsman /var/lib/ombudsman
chown -R ombudsman:ombudsman /var/log/ombudsman

echo "=========================================="
echo "Dependencies installed successfully!"
echo ""
echo "Next steps:"
echo "1. Copy application code to /opt/ombudsman/"
echo "2. Configure environment variables"
echo "3. Run deploy.sh to complete setup"
echo "=========================================="
