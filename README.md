# Ombudsman Data Migration Validator

Complete data migration validation platform with core library and validation studio.

## 🚀 Quick Start

```bash
# Navigate to project root
cd /Users/aravind/sourcecode/projects/data-migration-validator

# Start in development mode (recommended)
make unified

# Access the application
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
# API Docs: http://localhost:8000/docs
```

## 📁 Project Structure

```
data-migration-validator/
├── ombudsman_core/                    # Core validation library
│   ├── src/ombudsman/                # Core Python package
│   └── Dockerfile                    # Core-only Docker build
│
├── ombudsman-validation-studio/      # Validation Studio application
│   ├── backend/                      # FastAPI backend
│   │   ├── main.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── frontend/                     # React + Vite frontend
│   │   ├── src/
│   │   ├── Dockerfile
│   │   └── package.json
│   ├── docker-compose.yml            # Production config
│   └── docker-compose.dev.yml        # Development config
│
├── Dockerfile.unified                # ⭐ Core + Backend together
├── Dockerfile.all-in-one            # ⭐ Everything in one
├── docker-compose.unified.yml        # ⭐ Unified deployment
├── docker-compose.all-in-one.yml    # ⭐ All-in-one deployment
├── Makefile                          # ⭐ Easy commands
└── Documentation/
    ├── QUICKSTART.md                 # Quick start guide
    ├── DOCKER_UNIFIED_GUIDE.md       # Complete Docker guide
    └── UNIFIED_DOCKER_SUMMARY.md     # Setup summary
```

## 🐳 Docker Deployment Options

### 1. Unified Backend (Development) ⭐ Recommended
Core and backend in one container, frontend separate. Best for active development.

```bash
make unified
# or
docker-compose -f docker-compose.unified.yml up --build
```

### 2. All-in-One (Production) ⭐ Recommended
Everything in a single container. Best for simple deployment.

```bash
make all-in-one
# or
docker-compose -f docker-compose.all-in-one.yml up --build
```

### 3. Separate Services (Microservices)
Core, backend, and frontend as independent services.

```bash
cd ombudsman-validation-studio
docker-compose -f docker-compose.dev.yml up --build
```

## 📚 Documentation

- **[QUICKSTART.md](./QUICKSTART.md)** - Get started in 2 minutes
- **[DOCKER_UNIFIED_GUIDE.md](./DOCKER_UNIFIED_GUIDE.md)** - Complete Docker guide
- **[UNIFIED_DOCKER_SUMMARY.md](./UNIFIED_DOCKER_SUMMARY.md)** - Architecture overview
- **[ombudsman-validation-studio/DOCKER.md](./ombudsman-validation-studio/DOCKER.md)** - Studio-specific docs

## 🛠️ Common Commands

```bash
# Development
make unified        # Start unified backend mode
make dev           # Start separate services mode

# Production
make all-in-one    # Start all-in-one container
make prod          # Start production mode

# Management
make stop          # Stop all services
make clean         # Remove all containers/volumes
make logs          # View logs
make rebuild       # Rebuild without cache

# Utilities
make shell-backend # Open backend shell
make validate      # Validate all configs
make help          # Show all commands
```

## 🌐 Service URLs

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 🏗️ Architecture

### Unified Backend (Development)
```
┌─────────────────────┐     ┌─────────────────┐
│  Backend Container  │     │ Frontend        │
│  ┌───────────────┐  │     │ Container       │
│  │ Core Library  │  │     │ ┌─────────────┐ │
│  └───────────────┘  │     │ │ React+Vite  │ │
│  ┌───────────────┐  │     │ └─────────────┘ │
│  │ Studio API    │  │     └─────────────────┘
│  │ (FastAPI)     │  │            ↓
│  └───────────────┘  │     http://localhost:3000
│         ↓           │
│  http://localhost:8000
└─────────────────────┘
```

### All-in-One (Production)
```
┌─────────────────────────────┐
│   Single Container          │
│  ┌───────────────────────┐  │
│  │   Core Library        │  │
│  └───────────────────────┘  │
│  ┌───────────────────────┐  │
│  │   Backend API :8000   │  │
│  └───────────────────────┘  │
│  ┌───────────────────────┐  │
│  │   Frontend :3000      │  │
│  └───────────────────────┘  │
└─────────────────────────────┘
```

## 🔧 Development Workflow

1. **Make changes** to core or studio code
2. **Auto-reload** picks up changes (in unified mode)
3. **Test** at http://localhost:3000
4. **Commit** when ready

## 📦 Components

### Ombudsman Core
- Database connectors (MySQL, PostgreSQL, SQL Server)
- Validation engine
- Rule builder
- Metadata extraction

### Validation Studio
- **Backend**: FastAPI REST API
- **Frontend**: React + TypeScript + Material-UI
- **Features**:
  - Pipeline YAML editor
  - Validation dashboard
  - Metadata extraction
  - Rule builder
  - Mermaid diagram editor

## 🧪 Testing

```bash
# Run tests in backend container
make test

# Or manually
docker-compose -f docker-compose.unified.yml exec studio-backend pytest
```

## 🐛 Troubleshooting

### Port Conflicts
```bash
lsof -ti:3000 | xargs kill -9
lsof -ti:8000 | xargs kill -9
```

### Services Won't Start
```bash
make clean
make unified
```

### Core Changes Not Reflected
```bash
make rebuild
```

### View Logs
```bash
make logs
```

## 📝 Environment Variables

Create `.env` file in project root:

```env
# Backend
PYTHONPATH=/app:/core/src
DATABASE_URL=postgresql://user:pass@localhost/dbname

# Frontend
VITE_API_URL=http://localhost:8000
NODE_ENV=development
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with `make unified`
5. Submit a pull request

## 📄 License

[Your License Here]

## 🆘 Support

- **Documentation**: See `/docs` directory
- **Issues**: [GitHub Issues](your-repo-url)
- **Quick Help**: Run `make help`

---

**Ready to start?** Run `make unified` and you're good to go! 🚀
