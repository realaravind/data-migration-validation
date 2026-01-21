#!/bin/bash

# Ombudsman Validation Studio - Monitoring Script
# This script provides real-time monitoring of the deployed system

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_header() {
    echo -e "${BLUE}=================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=================================================${NC}"
}

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

# Clear screen
clear

print_header "Ombudsman Validation Studio - System Monitor"
echo ""

# Function to check service health
check_health() {
    local response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null)
    if [ "$response" = "200" ]; then
        print_success "Backend Health: OK (HTTP $response)"
        return 0
    else
        print_error "Backend Health: FAILED (HTTP $response)"
        return 1
    fi
}

# Function to get container stats
get_container_stats() {
    echo ""
    print_header "Container Status"
    docker ps --filter "name=ombudsman-validation-studio" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""
}

# Function to show resource usage
show_resource_usage() {
    print_header "Resource Usage"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" \
        $(docker ps --filter "name=ombudsman-validation-studio" -q) 2>/dev/null || echo "No containers found"
    echo ""
}

# Function to show recent logs
show_recent_logs() {
    print_header "Recent Logs (Last 20 lines)"
    docker logs --tail=20 ombudsman-validation-studio-studio-backend-1 2>/dev/null || echo "Container not found"
    echo ""
}

# Function to check disk usage
check_disk_usage() {
    print_header "Data Directory Usage"
    du -sh backend/data/* 2>/dev/null | while read size path; do
        echo "  $path: $size"
    done
    echo ""
}

# Function to check API endpoints
check_endpoints() {
    print_header "API Endpoint Status"

    # Root endpoint
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        print_success "Root endpoint: Accessible"
    else
        print_error "Root endpoint: Not accessible"
    fi

    # Health endpoint
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        print_success "Health endpoint: Accessible"
    else
        print_error "Health endpoint: Not accessible"
    fi

    # Features endpoint
    if curl -s http://localhost:8000/features > /dev/null 2>&1; then
        print_success "Features endpoint: Accessible"
    else
        print_error "Features endpoint: Not accessible"
    fi

    # API docs
    if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
        print_success "API Documentation: Accessible"
    else
        print_error "API Documentation: Not accessible"
    fi

    echo ""
}

# Main monitoring function
if [ "$1" = "--watch" ]; then
    # Continuous monitoring mode
    print_info "Starting continuous monitoring (Ctrl+C to stop)..."
    echo ""

    while true; do
        clear
        print_header "Ombudsman Validation Studio - Live Monitor"
        echo ""
        date
        echo ""

        check_health
        echo ""
        get_container_stats
        show_resource_usage

        echo ""
        print_info "Press Ctrl+C to stop monitoring"
        sleep 5
    done
else
    # Single check mode
    check_health
    echo ""
    get_container_stats
    show_resource_usage
    check_disk_usage
    check_endpoints
    show_recent_logs

    echo ""
    print_header "Monitoring Commands"
    echo ""
    echo "Available commands:"
    echo "  ./monitor.sh              - Run single monitoring check"
    echo "  ./monitor.sh --watch      - Continuous monitoring (updates every 5s)"
    echo "  docker-compose logs -f    - Follow live logs"
    echo "  docker stats             - Live resource monitoring"
    echo ""
    print_header "Useful URLs"
    echo ""
    echo "  API Documentation: http://localhost:8000/docs"
    echo "  Health Check:      http://localhost:8000/health"
    echo "  Feature List:      http://localhost:8000/features"
    echo ""
fi
