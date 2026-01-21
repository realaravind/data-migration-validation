#!/bin/bash
set -e

# Ombudsman Validation Studio - Ubuntu VM Installation Script
# This script installs Docker, Docker Compose, and sets up the application

echo "================================================"
echo "Ombudsman Validation Studio - Ubuntu Installer"
echo "================================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Please run as root (use sudo)"
    exit 1
fi

# Get the actual user (in case running via sudo)
ACTUAL_USER=${SUDO_USER:-$USER}
ACTUAL_HOME=$(eval echo ~$ACTUAL_USER)

echo "Installing as user: $ACTUAL_USER"
echo ""

# Update system
echo "Step 1/7: Updating system packages..."
apt-get update -qq
apt-get upgrade -y -qq

# Install prerequisites
echo "Step 2/7: Installing prerequisites..."
apt-get install -y -qq \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    nano \
    net-tools

# Install Docker
echo "Step 3/7: Installing Docker..."
if ! command -v docker &> /dev/null; then
    # Add Docker's official GPG key
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    # Add Docker repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker Engine
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Add user to docker group
    usermod -aG docker $ACTUAL_USER

    echo "Docker installed successfully!"
else
    echo "Docker is already installed."
fi

# Start Docker service
echo "Step 4/7: Starting Docker service..."
systemctl enable docker
systemctl start docker

# Verify Docker installation
echo "Step 5/7: Verifying Docker installation..."
docker --version
docker compose version

# Create application directory
echo "Step 6/7: Setting up application directory..."
APP_DIR="/opt/ombudsman-validation-studio"
mkdir -p $APP_DIR
cd $APP_DIR

# Copy application files (if running from the repo)
if [ -d "$ACTUAL_HOME/ombudsman-validation-studio" ]; then
    echo "Copying application files from $ACTUAL_HOME/ombudsman-validation-studio..."
    cp -r $ACTUAL_HOME/ombudsman-validation-studio/* $APP_DIR/
elif [ -d "/vagrant/ombudsman-validation-studio" ]; then
    echo "Copying application files from /vagrant/ombudsman-validation-studio..."
    cp -r /vagrant/ombudsman-validation-studio/* $APP_DIR/
else
    echo "WARNING: Application files not found. Please copy them manually to $APP_DIR"
fi

# Set ownership
chown -R $ACTUAL_USER:$ACTUAL_USER $APP_DIR

# Create .env file if it doesn't exist
if [ ! -f "$APP_DIR/.env" ]; then
    echo "Step 7/7: Creating .env configuration file..."
    cat > $APP_DIR/.env << 'EOF'
# Ombudsman Validation Studio Configuration

# SQL Server Configuration
SQL_SERVER_HOST=your-sqlserver-host
SQL_SERVER_PORT=1433
SQL_SERVER_USER=sa
SQL_SERVER_PASSWORD=YourStrong!Passw0rd
SQL_SERVER_DATABASE=SampleDW

# Snowflake Configuration (Optional)
SNOWFLAKE_ACCOUNT=your-account
SNOWFLAKE_USER=your-user
SNOWFLAKE_PASSWORD=your-password
SNOWFLAKE_WAREHOUSE=your-warehouse
SNOWFLAKE_DATABASE=SAMPLEDW
SNOWFLAKE_SCHEMA=PUBLIC

# Application Configuration
BACKEND_PORT=8000
FRONTEND_PORT=3000

# Database for OVS Studio (Authentication, Projects, etc.)
OVS_DB_HOST=your-sqlserver-host
OVS_DB_PORT=1433
OVS_DB_NAME=ovs_studio
OVS_DB_USER=sa
OVS_DB_PASSWORD=YourStrong!Passw0rd

# JWT Secret (Change this to a random string)
JWT_SECRET_KEY=change-this-to-a-random-secret-key-at-least-32-characters-long
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
EOF
    chown $ACTUAL_USER:$ACTUAL_USER $APP_DIR/.env
    echo "Created .env file at $APP_DIR/.env"
    echo "IMPORTANT: Please edit $APP_DIR/.env with your actual database credentials!"
else
    echo "Step 7/7: .env file already exists, skipping..."
fi

# Create systemd service for auto-start
echo ""
echo "Creating systemd service for auto-start..."
cat > /etc/systemd/system/ombudsman-studio.service << EOF
[Unit]
Description=Ombudsman Validation Studio
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
User=$ACTUAL_USER

[Install]
WantedBy=multi-user.target
EOF

# Enable service
systemctl daemon-reload
systemctl enable ombudsman-studio.service

echo ""
echo "================================================"
echo "Installation Complete!"
echo "================================================"
echo ""
echo "Next Steps:"
echo "1. Edit configuration: sudo nano $APP_DIR/.env"
echo "2. Update database credentials in .env file"
echo "3. Start the application:"
echo "   cd $APP_DIR"
echo "   docker compose up -d"
echo ""
echo "Or use systemd service:"
echo "   sudo systemctl start ombudsman-studio"
echo ""
echo "Access the application:"
echo "   Frontend: http://$(hostname -I | awk '{print $1}'):3000"
echo "   Backend API: http://$(hostname -I | awk '{print $1}'):8000"
echo "   API Docs: http://$(hostname -I | awk '{print $1}'):8000/docs"
echo ""
echo "View logs:"
echo "   docker compose logs -f"
echo ""
echo "IMPORTANT: If you just installed Docker, you may need to log out"
echo "and log back in for group permissions to take effect."
echo "================================================"
