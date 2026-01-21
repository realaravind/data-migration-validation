#!/bin/bash
# Ombudsman Validation Studio - Deployment Script
# Run as root or with sudo after install-dependencies.sh

set -e

# Configuration
DOMAIN="${1:-}"
EMAIL="${2:-}"
APP_DIR="/opt/ombudsman"
DATA_DIR="/var/lib/ombudsman"
LOG_DIR="/var/log/ombudsman"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check arguments
if [ -z "$DOMAIN" ]; then
    echo "Usage: $0 <domain> [email]"
    echo "  domain: Your domain name (e.g., ombudsman.example.com)"
    echo "  email:  Email for Let's Encrypt notifications (optional but recommended)"
    exit 1
fi

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo_error "Please run as root or with sudo"
    exit 1
fi

echo "=========================================="
echo "Ombudsman Validation Studio - Deployment"
echo "=========================================="
echo "Domain: $DOMAIN"
echo "Email:  ${EMAIL:-not provided}"
echo ""

# Verify dependencies are installed
echo_info "Verifying dependencies..."
command -v python3.11 >/dev/null 2>&1 || { echo_error "Python 3.11 not found. Run install-dependencies.sh first."; exit 1; }
command -v node >/dev/null 2>&1 || { echo_error "Node.js not found. Run install-dependencies.sh first."; exit 1; }
command -v nginx >/dev/null 2>&1 || { echo_error "Nginx not found. Run install-dependencies.sh first."; exit 1; }
command -v certbot >/dev/null 2>&1 || { echo_error "Certbot not found. Run install-dependencies.sh first."; exit 1; }
command -v ollama >/dev/null 2>&1 || { echo_error "Ollama not found. Run install-dependencies.sh first."; exit 1; }

# Step 1: Copy application code
echo_info "[1/10] Copying application code..."

# Copy backend
cp -r "$SOURCE_DIR/ombudsman-validation-studio/backend"/* "$APP_DIR/backend/"

# Copy core library
cp -r "$SOURCE_DIR/ombudsman_core/src"/* "$APP_DIR/core/src/"

# Copy frontend source for building
cp -r "$SOURCE_DIR/ombudsman-validation-studio/frontend"/* "$APP_DIR/frontend/"

# Step 2: Set up Python virtual environment
echo_info "[2/10] Setting up Python virtual environment..."
cd "$APP_DIR/backend"
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

# Step 3: Build frontend
echo_info "[3/10] Building frontend..."
cd "$APP_DIR/frontend"
npm ci
npm run build

# Step 4: Create data directories
echo_info "[4/10] Creating data directories..."
mkdir -p "$DATA_DIR/data/mapping_intelligence"
mkdir -p "$DATA_DIR/data/query_history"
mkdir -p "$DATA_DIR/data/pipeline_runs"
mkdir -p "$DATA_DIR/data/config_backups"
mkdir -p "$DATA_DIR/data/auth"
mkdir -p "$DATA_DIR/data/audit_logs"
mkdir -p "$DATA_DIR/data/batch_jobs"
mkdir -p "$DATA_DIR/data/projects"
mkdir -p "$DATA_DIR/data/pipelines"
mkdir -p "$DATA_DIR/data/workloads"
mkdir -p "$LOG_DIR"

# Copy default data if exists
if [ -d "$SOURCE_DIR/ombudsman-validation-studio/backend/data" ]; then
    cp -r "$SOURCE_DIR/ombudsman-validation-studio/backend/data"/* "$DATA_DIR/data/" 2>/dev/null || true
fi

# Create symlink from backend data to persistent storage
rm -rf "$APP_DIR/backend/data"
ln -s "$DATA_DIR/data" "$APP_DIR/backend/data"

# Step 5: Set up environment file
echo_info "[5/10] Setting up environment configuration..."
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$SCRIPT_DIR/.env.template" "$APP_DIR/.env"
    echo_warn "Environment file created at $APP_DIR/.env"
    echo_warn "Please edit this file with your database credentials!"
fi

# Step 6: Set ownership
echo_info "[6/10] Setting file ownership..."
chown -R ombudsman:ombudsman "$APP_DIR"
chown -R ombudsman:ombudsman "$DATA_DIR"
chown -R ombudsman:ombudsman "$LOG_DIR"

# Step 7: Install systemd services
echo_info "[7/10] Installing systemd services..."
cp "$SCRIPT_DIR/systemd/ombudsman-backend.service" /etc/systemd/system/
cp "$SCRIPT_DIR/systemd/ombudsman-frontend.service" /etc/systemd/system/

systemctl daemon-reload
systemctl enable ombudsman-backend
systemctl enable ombudsman-frontend

# Step 8: Configure Nginx
echo_info "[8/10] Configuring Nginx..."
# Replace domain placeholder in nginx config
sed "s/YOUR_DOMAIN/$DOMAIN/g" "$SCRIPT_DIR/nginx/ombudsman.conf" > /etc/nginx/sites-available/ombudsman

# Enable site
ln -sf /etc/nginx/sites-available/ombudsman /etc/nginx/sites-enabled/

# Remove default site if exists
rm -f /etc/nginx/sites-enabled/default

# Test nginx configuration
nginx -t

# Step 9: Obtain SSL certificate
echo_info "[9/10] Obtaining SSL certificate..."
mkdir -p /var/www/certbot

# Stop nginx temporarily for standalone certbot
systemctl stop nginx || true

if [ -n "$EMAIL" ]; then
    certbot certonly --standalone -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL"
else
    certbot certonly --standalone -d "$DOMAIN" --non-interactive --agree-tos --register-unsafely-without-email
fi

# Step 10: Start services
echo_info "[10/10] Starting services..."

# Start Ollama and pull model
systemctl enable ollama
systemctl start ollama

echo_info "Waiting for Ollama to start..."
sleep 5

# Pull the llama2 model for schema mapping
echo_info "Pulling llama2 model for AI-powered schema mapping..."
su - ombudsman -c "ollama pull llama2" || echo_warn "Failed to pull llama2 model. You can pull it later with: ollama pull llama2"

# Start application services
systemctl start ombudsman-backend
systemctl start ombudsman-frontend

# Start Nginx
systemctl start nginx
systemctl enable nginx

# Set up automatic certificate renewal
echo_info "Setting up automatic SSL certificate renewal..."
(crontab -l 2>/dev/null | grep -v certbot; echo "0 0,12 * * * /usr/bin/certbot renew --quiet --post-hook 'systemctl reload nginx'") | crontab -

echo ""
echo "=========================================="
echo -e "${GREEN}Deployment Complete!${NC}"
echo "=========================================="
echo ""
echo "Application URL: https://$DOMAIN"
echo ""
echo "Service Status:"
systemctl status ombudsman-backend --no-pager -l | head -5
echo ""
systemctl status ombudsman-frontend --no-pager -l | head -5
echo ""
echo "Important files:"
echo "  - Config:     $APP_DIR/.env"
echo "  - Data:       $DATA_DIR/data/"
echo "  - Logs:       $LOG_DIR/"
echo "  - Nginx:      /etc/nginx/sites-available/ombudsman"
echo ""
echo "Useful commands:"
echo "  - View backend logs:   journalctl -u ombudsman-backend -f"
echo "  - View frontend logs:  journalctl -u ombudsman-frontend -f"
echo "  - Restart backend:     systemctl restart ombudsman-backend"
echo "  - Restart frontend:    systemctl restart ombudsman-frontend"
echo ""
echo -e "${YELLOW}IMPORTANT:${NC} Edit $APP_DIR/.env with your database credentials!"
echo ""
