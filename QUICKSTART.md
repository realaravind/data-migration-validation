# Quick Start - Unified Docker Setup

## 🎯 Choose Your Deployment Mode

### 1️⃣ **Unified Backend** (Recommended for Development)
Best for: Active development on both core and studio

```bash
# Using Makefile
make unified

# Or directly
docker-compose -f docker-compose.unified.yml up --build
```

**What you get:**
- ✅ Core + Backend in one container
- ✅ Frontend in separate container
- ✅ Hot reload enabled
- ✅ Fast iteration

---

### 2️⃣ **All-in-One** (Recommended for Production)
Best for: Simple deployment, production use

```bash
# Using Makefile
make all-in-one

# Or directly
docker-compose -f docker-compose.all-in-one.yml up --build
```

**What you get:**
- ✅ Everything in one container
- ✅ Smallest footprint
- ✅ Easiest to deploy
- ✅ Production optimized

---

## 🚀 Super Quick Start

```bash
# 1. Navigate to project root
cd /Users/aravind/sourcecode/projects/data-migration-validator

# 2. Start unified mode (development)
make unified

# 3. Access the application
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
# API Docs: http://localhost:8000/docs
```

---

## 📋 Common Commands

```bash
# Start services
make unified        # Development mode
make all-in-one     # Production mode

# Stop services
make stop

# View logs
make logs

# Clean everything
make clean

# Rebuild from scratch
make rebuild

# See all commands
make help
```

---

## 🏗️ Architecture Comparison

### Unified Backend
```
┌─────────────────┐     ┌─────────────────┐
│   Backend       │     │   Frontend      │
│  ┌──────────┐   │     │  ┌──────────┐   │
│  │  Core    │   │     │  │  React   │   │
│  └──────────┘   │     │  └──────────┘   │
│  ┌──────────┐   │     └─────────────────┘
│  │  Studio  │   │
│  └──────────┘   │
└─────────────────┘
```

### All-in-One
```
┌─────────────────────────────┐
│   Single Container          │
│  ┌──────────┐               │
│  │  Core    │               │
│  └──────────┘               │
│  ┌──────────┐               │
│  │  Backend │ :8000         │
│  └──────────┘               │
│  ┌──────────┐               │
│  │ Frontend │ :3000         │
│  └──────────┘               │
└─────────────────────────────┘
```

---

## 📁 File Locations

All unified Docker files are in the **project root**:

```
data-migration-validator/
├── Makefile                      # ⭐ Use this for easy commands
├── Dockerfile.unified            # Unified backend build
├── Dockerfile.all-in-one         # All-in-one build
├── docker-compose.unified.yml    # Unified compose
├── docker-compose.all-in-one.yml # All-in-one compose
└── DOCKER_UNIFIED_GUIDE.md       # Full documentation
```

---

## 🐛 Troubleshooting

**Services won't start?**
```bash
make clean
make unified
```

**Port already in use?**
```bash
lsof -ti:3000 | xargs kill -9
lsof -ti:8000 | xargs kill -9
```

**Need to rebuild?**
```bash
make rebuild
```

---

## 📖 Full Documentation

For complete details, see:
- [`DOCKER_UNIFIED_GUIDE.md`](./DOCKER_UNIFIED_GUIDE.md) - Complete guide
- [`Makefile`](./Makefile) - All available commands

---

**Ready to start?** Run `make unified` and you're good to go! 🚀
