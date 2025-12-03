# =============================================================================
# Ombudsman Validation Studio - Makefile
# Simplifies Docker operations for all deployment modes
# =============================================================================

.PHONY: help dev prod unified all-in-one clean logs shell test

# Default target
help:
	@echo "🐳 Ombudsman Validation Studio - Docker Commands"
	@echo ""
	@echo "Development:"
	@echo "  make dev          - Start in development mode (separate services)"
	@echo "  make unified      - Start with unified backend (core + studio)"
	@echo "  make complete     - Start COMPLETE system (core app + studio + data) ⭐"
	@echo ""
	@echo "Production:"
	@echo "  make prod         - Start in production mode"
	@echo "  make all-in-one   - Start all-in-one container"
	@echo ""
	@echo "Management:"
	@echo "  make stop         - Stop all services"
	@echo "  make clean        - Stop and remove all containers/volumes"
	@echo "  make logs         - View logs (all services)"
	@echo "  make logs-backend - View backend logs only"
	@echo "  make logs-frontend- View frontend logs only"
	@echo ""
	@echo "Utilities:"
	@echo "  make shell-backend - Open shell in backend container"
	@echo "  make shell-frontend- Open shell in frontend container"
	@echo "  make rebuild      - Rebuild without cache"
	@echo "  make test         - Run tests"
	@echo "  make validate     - Validate all Docker configs"
	@echo ""

# =============================================================================
# Development Modes
# =============================================================================

dev:
	@echo "🚀 Starting in development mode (separate services)..."
	cd ombudsman-validation-studio && docker-compose -f docker-compose.dev.yml up --build

unified:
	@echo "🚀 Starting with unified backend (core + studio)..."
	docker-compose -f docker-compose.unified.yml up --build

complete:
	@echo "🚀 Starting COMPLETE system (core web app + studio + sample data)..."
	docker-compose -f docker-compose.complete.yml up --build

# =============================================================================
# Production Modes
# =============================================================================

prod:
	@echo "🚀 Starting in production mode..."
	cd ombudsman-validation-studio && docker-compose up --build -d

all-in-one:
	@echo "🚀 Starting all-in-one container..."
	docker-compose -f docker-compose.all-in-one.yml up --build -d

# =============================================================================
# Management Commands
# =============================================================================

stop:
	@echo "🛑 Stopping all services..."
	-docker-compose -f docker-compose.complete.yml down
	-docker-compose -f docker-compose.unified.yml down
	-docker-compose -f docker-compose.all-in-one.yml down
	-cd ombudsman-validation-studio && docker-compose down
	-cd ombudsman-validation-studio && docker-compose -f docker-compose.dev.yml down

clean:
	@echo "🧹 Cleaning up all containers, volumes, and networks..."
	-docker-compose -f docker-compose.unified.yml down -v
	-docker-compose -f docker-compose.all-in-one.yml down -v
	-cd ombudsman-validation-studio && docker-compose down -v
	-cd ombudsman-validation-studio && docker-compose -f docker-compose.dev.yml down -v
	@echo "✅ Cleanup complete"

rebuild:
	@echo "🔨 Rebuilding without cache..."
	docker-compose -f docker-compose.unified.yml build --no-cache
	@echo "✅ Rebuild complete"

# =============================================================================
# Logs
# =============================================================================

logs:
	docker-compose -f docker-compose.unified.yml logs -f

logs-backend:
	docker-compose -f docker-compose.unified.yml logs -f studio-backend

logs-frontend:
	docker-compose -f docker-compose.unified.yml logs -f studio-frontend

logs-all-in-one:
	docker-compose -f docker-compose.all-in-one.yml logs -f

# =============================================================================
# Shell Access
# =============================================================================

shell-backend:
	docker-compose -f docker-compose.unified.yml exec studio-backend /bin/bash

shell-frontend:
	docker-compose -f docker-compose.unified.yml exec studio-frontend /bin/sh

shell-all-in-one:
	docker-compose -f docker-compose.all-in-one.yml exec ombudsman-studio /bin/bash

# =============================================================================
# Testing & Validation
# =============================================================================

test:
	@echo "🧪 Running tests..."
	docker-compose -f docker-compose.unified.yml exec studio-backend pytest

validate:
	@echo "✅ Validating Docker configurations..."
	@docker-compose -f docker-compose.unified.yml config > /dev/null && echo "  ✓ unified config valid"
	@docker-compose -f docker-compose.all-in-one.yml config > /dev/null && echo "  ✓ all-in-one config valid"
	@cd ombudsman-validation-studio && docker-compose config > /dev/null && echo "  ✓ production config valid"
	@cd ombudsman-validation-studio && docker-compose -f docker-compose.dev.yml config > /dev/null && echo "  ✓ dev config valid"
	@echo "✅ All configurations are valid"

# =============================================================================
# Quick Actions
# =============================================================================

# Start unified in background
up:
	docker-compose -f docker-compose.unified.yml up -d

# Restart services
restart:
	docker-compose -f docker-compose.unified.yml restart

# View status
status:
	docker-compose -f docker-compose.unified.yml ps

# Pull latest images
pull:
	docker-compose -f docker-compose.unified.yml pull

# =============================================================================
# Cleanup
# =============================================================================

prune:
	@echo "🧹 Pruning Docker system..."
	docker system prune -af
	docker volume prune -f
	@echo "✅ Prune complete"
