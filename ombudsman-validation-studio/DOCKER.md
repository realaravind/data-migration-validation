# Docker Setup Guide

## Quick Start

### Development Mode (with hot reload)
```bash
docker-compose -f docker-compose.dev.yml up --build
```

### Production Mode
```bash
docker-compose up --build
```

## Services

- **Backend**: FastAPI application running on `http://localhost:8000`
- **Frontend**: Vite React application running on `http://localhost:3000`

## Docker Files Overview

### Development
- `docker-compose.dev.yml` - Development setup with hot reload
- `frontend/Dockerfile.dev` - Frontend dev container with Vite dev server
- `backend/Dockerfile` - Backend container with uvicorn reload

### Production
- `docker-compose.yml` - Production-optimized setup
- `frontend/Dockerfile` - Multi-stage build for optimized frontend
- `backend/Dockerfile` - Production backend container

## Common Commands

### Start services
```bash
# Development with hot reload
docker-compose -f docker-compose.dev.yml up

# Production
docker-compose up
```

### Rebuild after changes
```bash
# Development
docker-compose -f docker-compose.dev.yml up --build

# Production
docker-compose up --build
```

### Stop services
```bash
docker-compose down
```

### View logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f studio-backend
docker-compose logs -f studio-frontend
```

### Execute commands in containers
```bash
# Backend shell
docker-compose exec studio-backend /bin/bash

# Frontend shell
docker-compose exec studio-frontend /bin/sh

# Run backend tests
docker-compose exec studio-backend pytest

# Install new npm package
docker-compose exec studio-frontend npm install <package-name>
```

### Clean up
```bash
# Stop and remove containers, networks
docker-compose down

# Also remove volumes
docker-compose down -v

# Remove all images
docker-compose down --rmi all
```

## Environment Variables

Create a `.env` file in the project root for environment-specific configuration:

```env
# Backend
PYTHONPATH=/app:/core/src
DATABASE_URL=postgresql://user:pass@localhost/dbname

# Frontend
VITE_API_URL=http://localhost:8000
NODE_ENV=development
```

## Troubleshooting

### Port already in use
```bash
# Find and kill process using port 8000
lsof -ti:8000 | xargs kill -9

# Find and kill process using port 3000
lsof -ti:3000 | xargs kill -9
```

### Permission issues with volumes
```bash
# Fix permissions
sudo chown -R $USER:$USER ./backend ./frontend
```

### Clear Docker cache
```bash
# Remove all stopped containers
docker container prune

# Remove all unused images
docker image prune -a

# Remove all unused volumes
docker volume prune

# Nuclear option - remove everything
docker system prune -a --volumes
```

### Frontend not updating
If you're in development mode and changes aren't reflecting:
1. Make sure you're using `docker-compose.dev.yml`
2. Check that volumes are mounted correctly
3. Restart the frontend container: `docker-compose restart studio-frontend`

### Backend not updating
1. Ensure `--reload` flag is in the uvicorn command
2. Check volume mounts in docker-compose
3. Restart: `docker-compose restart studio-backend`

## Network

Both services are on the `ovs-net` bridge network and can communicate using service names:
- Backend can be reached at `http://studio-backend:8000` from frontend
- Frontend can be reached at `http://studio-frontend:3000` from backend

## Health Checks

Add health checks to docker-compose.yml:

```yaml
services:
  studio-backend:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```
