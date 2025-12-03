# 🐳 Unified Docker Deployment Guide

This directory contains multiple Docker deployment strategies for the Ombudsman Validation Studio.

## 📁 Available Configurations

### 1. **Unified Backend** (Recommended for Development)
**Files**: `Dockerfile.unified` + `docker-compose.unified.yml`

Builds `ombudsman_core` and `studio backend` together in one container, frontend separate.

```bash
docker-compose -f docker-compose.unified.yml up --build
```

**Pros:**
- ✅ Core and backend always in sync
- ✅ Easier dependency management
- ✅ Hot reload for both core and studio
- ✅ Separate frontend for faster rebuilds

**Use when:**
- Developing both core and studio simultaneously
- Need to test core changes with studio immediately

---

### 2. **All-in-One** (Recommended for Production)
**Files**: `Dockerfile.all-in-one` + `docker-compose.all-in-one.yml`

Single container with core, backend, AND frontend.

```bash
docker-compose -f docker-compose.all-in-one.yml up --build
```

**Pros:**
- ✅ Single container to deploy
- ✅ Smallest deployment footprint
- ✅ Simplest production setup
- ✅ All services start together

**Use when:**
- Deploying to production
- Need simplest possible deployment
- Running on resource-constrained environments

---

### 3. **Separate Services** (Original)
**Files**: `ombudsman-validation-studio/docker-compose.yml`

Core, backend, and frontend as separate services.

```bash
cd ombudsman-validation-studio
docker-compose up --build
```

**Pros:**
- ✅ Independent scaling
- ✅ Separate updates
- ✅ Best for microservices architecture

**Use when:**
- Need to scale services independently
- Core library is stable and rarely changes
- Running in Kubernetes or orchestrated environment

---

## 🚀 Quick Start

### Development (Unified Backend)
```bash
# From project root
docker-compose -f docker-compose.unified.yml up --build
```

### Production (All-in-One)
```bash
# From project root
docker-compose -f docker-compose.all-in-one.yml up -d --build
```

### Traditional (Separate Services)
```bash
# From studio directory
cd ombudsman-validation-studio
docker-compose -f docker-compose.dev.yml up --build
```

---

## 📊 Comparison Table

| Feature | Unified Backend | All-in-One | Separate Services |
|---------|----------------|------------|-------------------|
| **Containers** | 2 (backend+core, frontend) | 1 (everything) | 3 (core, backend, frontend) |
| **Build Time** | Medium | Longest | Fastest (cached) |
| **Hot Reload** | ✅ Yes | ❌ No | ✅ Yes |
| **Production Ready** | ⚠️ Partial | ✅ Yes | ✅ Yes |
| **Easy Deployment** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **Development** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| **Resource Usage** | Medium | Low | High |
| **Scalability** | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## 🔧 Configuration Details

### Unified Backend Architecture
```
┌─────────────────────────────────┐
│   Container: studio-backend     │
│  ┌──────────────────────────┐   │
│  │   ombudsman_core         │   │
│  │   (installed as package) │   │
│  └──────────────────────────┘   │
│  ┌──────────────────────────┐   │
│  │   studio backend         │   │
│  │   (FastAPI app)          │   │
│  └──────────────────────────┘   │
└─────────────────────────────────┘
┌─────────────────────────────────┐
│   Container: studio-frontend    │
│  ┌──────────────────────────┐   │
│  │   React + Vite           │   │
│  └──────────────────────────┘   │
└─────────────────────────────────┘
```

### All-in-One Architecture
```
┌─────────────────────────────────┐
│   Container: ombudsman-studio   │
│  ┌──────────────────────────┐   │
│  │   ombudsman_core         │   │
│  └──────────────────────────┘   │
│  ┌──────────────────────────┐   │
│  │   Backend (port 8000)    │   │
│  └──────────────────────────┘   │
│  ┌──────────────────────────┐   │
│  │   Frontend (port 3000)   │   │
│  └──────────────────────────┘   │
└─────────────────────────────────┘
```

---

## 🌐 Access URLs

After starting any configuration:

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

---

## 📝 Common Commands

### Build and Start
```bash
# Unified
docker-compose -f docker-compose.unified.yml up --build

# All-in-One
docker-compose -f docker-compose.all-in-one.yml up --build

# Separate
cd ombudsman-validation-studio && docker-compose up --build
```

### Stop Services
```bash
docker-compose -f docker-compose.unified.yml down
docker-compose -f docker-compose.all-in-one.yml down
```

### View Logs
```bash
# Unified
docker-compose -f docker-compose.unified.yml logs -f

# All-in-One
docker-compose -f docker-compose.all-in-one.yml logs -f
```

### Rebuild from Scratch
```bash
# Unified
docker-compose -f docker-compose.unified.yml down -v
docker-compose -f docker-compose.unified.yml build --no-cache
docker-compose -f docker-compose.unified.yml up

# All-in-One
docker-compose -f docker-compose.all-in-one.yml down -v
docker-compose -f docker-compose.all-in-one.yml build --no-cache
docker-compose -f docker-compose.all-in-one.yml up
```

---

## 🐛 Troubleshooting

### Core Changes Not Reflected
If you modify `ombudsman_core` and changes don't appear:

```bash
# Rebuild with no cache
docker-compose -f docker-compose.unified.yml build --no-cache studio-backend
docker-compose -f docker-compose.unified.yml up
```

### Port Conflicts
```bash
# Kill processes on ports
lsof -ti:3000 | xargs kill -9
lsof -ti:8000 | xargs kill -9
```

### Container Won't Start
```bash
# Check logs
docker-compose -f docker-compose.unified.yml logs studio-backend

# Check health
docker ps
docker inspect <container-id>
```

---

## 💡 Best Practices

### Development
1. Use **Unified Backend** configuration
2. Mount volumes for hot reload
3. Use `--build` flag when core changes
4. Monitor logs with `-f` flag

### Production
1. Use **All-in-One** configuration
2. Don't mount volumes (use built code)
3. Set restart policies
4. Enable health checks
5. Use environment files for secrets

### CI/CD
```bash
# Build and test
docker-compose -f docker-compose.all-in-one.yml build
docker-compose -f docker-compose.all-in-one.yml up -d
# Run tests
docker-compose -f docker-compose.all-in-one.yml down
```

---

## 📦 File Structure

```
data-migration-validator/
├── Dockerfile.unified              # Backend with core
├── Dockerfile.all-in-one          # Everything in one
├── docker-compose.unified.yml     # Unified backend compose
├── docker-compose.all-in-one.yml  # All-in-one compose
├── ombudsman_core/                # Core library
│   ├── src/
│   └── Dockerfile
└── ombudsman-validation-studio/   # Studio application
    ├── backend/
    │   ├── Dockerfile
    │   └── requirements.txt
    ├── frontend/
    │   ├── Dockerfile
    │   └── Dockerfile.dev
    ├── docker-compose.yml
    └── docker-compose.dev.yml
```

---

## 🎯 Recommendations

- **Local Development**: Use `docker-compose.unified.yml`
- **Production Deployment**: Use `docker-compose.all-in-one.yml`
- **Microservices/K8s**: Use separate services in `ombudsman-validation-studio/`

---

**Need help?** Check the individual README files in each directory or open an issue.
