# =============================================================================
# Ombudsman Validation Studio - Makefile
# Simplified commands for Docker deployment
# =============================================================================

.PHONY: help up down restart logs shell-backend shell-frontend rebuild clean test status

# Default target
help:
	@echo "🐳 Ombudsman Validation Studio - Docker Commands"
	@echo ""
	@echo "Quick Start:"
	@echo "  make up           - Start all services"
	@echo "  make down         - Stop all services"
	@echo "  make restart      - Restart all services"
	@echo "  make logs         - View logs (all services)"
	@echo ""
	@echo "Development:"
	@echo "  make logs-backend - View backend logs only"
	@echo "  make logs-frontend- View frontend logs only"
	@echo "  make shell-backend - Open shell in backend container"
	@echo "  make shell-frontend- Open shell in frontend container"
	@echo "  make rebuild      - Rebuild without cache"
	@echo ""
	@echo "Maintenance:"
	@echo "  make status       - Show container status"
	@echo "  make clean        - Stop and remove all containers/volumes"
	@echo "  make prune        - Clean up Docker system"
	@echo ""
	@echo "Testing:"
	@echo "  make test         - Run tests in backend"
	@echo ""

# =============================================================================
# Main Commands
# =============================================================================

up:
	@echo "🚀 Starting Ombudsman Validation Studio..."
	cd ombudsman-validation-studio && docker-compose up -d
	@echo "✅ Services started!"
	@echo ""
	@echo "Frontend: http://localhost:3000"
	@echo "Backend:  http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"

down:
	@echo "🛑 Stopping all services..."
	cd ombudsman-validation-studio && docker-compose down
	@echo "✅ Services stopped"

restart:
	@echo "🔄 Restarting services..."
	cd ombudsman-validation-studio && docker-compose restart
	@echo "✅ Services restarted"

status:
	@echo "📊 Container Status:"
	@cd ombudsman-validation-studio && docker-compose ps

# =============================================================================
# Logs
# =============================================================================

logs:
	cd ombudsman-validation-studio && docker-compose logs -f

logs-backend:
	cd ombudsman-validation-studio && docker-compose logs -f studio-backend

logs-frontend:
	cd ombudsman-validation-studio && docker-compose logs -f studio-frontend

# =============================================================================
# Shell Access
# =============================================================================

shell-backend:
	cd ombudsman-validation-studio && docker-compose exec studio-backend /bin/bash

shell-frontend:
	cd ombudsman-validation-studio && docker-compose exec studio-frontend /bin/sh

# =============================================================================
# Build & Maintenance
# =============================================================================

rebuild:
	@echo "🔨 Rebuilding without cache..."
	cd ombudsman-validation-studio && docker-compose build --no-cache
	@echo "✅ Rebuild complete"

clean:
	@echo "🧹 Cleaning up all containers and volumes..."
	cd ombudsman-validation-studio && docker-compose down -v
	@echo "✅ Cleanup complete"

prune:
	@echo "🧹 Pruning Docker system..."
	docker system prune -af
	docker volume prune -f
	@echo "✅ Prune complete"

# =============================================================================
# Testing
# =============================================================================

test:
	@echo "🧪 Running tests..."
	cd ombudsman-validation-studio && docker-compose exec studio-backend pytest
	@echo "✅ Tests complete"

# =============================================================================
# Deployment (Ubuntu/Windows VM)
# =============================================================================

deploy-ubuntu:
	@echo "📦 See deployment/ubuntu/README.md for Ubuntu deployment instructions"

deploy-windows:
	@echo "📦 See deployment/windows/README.md for Windows deployment instructions"
