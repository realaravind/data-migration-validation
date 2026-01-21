#!/bin/bash

# Ombudsman Validation Studio - Deployment Script
# This script handles the complete deployment process

set -e  # Exit on error

echo "=================================================="
echo "Ombudsman Validation Studio - Deployment Script"
echo "=================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "ℹ $1"
}

# Check if Docker is running
echo "Step 1: Checking Docker status..."
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker Desktop and try again."
    exit 1
fi
print_success "Docker is running"
echo ""

# Check if .env file exists
echo "Step 2: Checking environment configuration..."
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_warning "Please update .env with your database credentials before continuing."
        print_info "Press Enter to continue after updating .env, or Ctrl+C to exit..."
        read
    else
        print_error ".env.example not found. Cannot create .env file."
        exit 1
    fi
else
    print_success "Environment file found"
fi
echo ""

# Stop any running containers
echo "Step 3: Stopping existing containers..."
docker-compose down 2>/dev/null || true
print_success "Stopped existing containers"
echo ""

# Check if backend image exists, if not build it
echo "Step 4: Checking backend image..."
if docker images | grep -q "ombudsman-validation-studio-studio-backend"; then
    print_success "Backend image exists"
else
    print_warning "Backend image not found. Building..."
    docker-compose build studio-backend
    print_success "Backend image built"
fi
echo ""

# Create data directories
echo "Step 5: Creating data directories..."
mkdir -p backend/data/mapping_intelligence
mkdir -p backend/data/query_history
mkdir -p backend/data/pipeline_runs
mkdir -p backend/data/config_backups
mkdir -p backend/data/auth
print_success "Data directories created"
echo ""

# Start backend service
echo "Step 6: Starting backend service..."
docker-compose up -d studio-backend
if [ $? -eq 0 ]; then
    print_success "Backend container started"
else
    print_error "Failed to start backend container"
    exit 1
fi
echo ""

# Wait for backend to be healthy
echo "Step 7: Waiting for backend to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        print_success "Backend is healthy and responding"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -n "."
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    print_error "Backend failed to start within timeout"
    echo ""
    echo "Checking logs:"
    docker-compose logs --tail=50 studio-backend
    exit 1
fi
echo ""

# Show service status
echo "Step 8: Checking service status..."
docker-compose ps
echo ""

# Display access information
echo "=================================================="
echo "✓ Deployment Complete!"
echo "=================================================="
echo ""
echo "Backend API:"
echo "  - URL: http://localhost:8000"
echo "  - Health: http://localhost:8000/health"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - Features: http://localhost:8000/features"
echo ""
echo "Useful Commands:"
echo "  - View logs: docker-compose logs -f studio-backend"
echo "  - Stop services: docker-compose down"
echo "  - Restart: docker-compose restart studio-backend"
echo ""
echo "=================================================="
