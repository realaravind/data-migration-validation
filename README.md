# Ombudsman Validation Studio

**Intelligent Data Migration Validation Platform**

Ombudsman Validation Studio is a comprehensive platform for validating data migrations between databases, with specialized support for SQL Server to Snowflake migrations.

---

## 🚀 Quick Start

### Using Makefile (Recommended)

```bash
# Start all services
make up

# View logs
make logs

# Stop all services
make down
```

### Using Docker Compose

```bash
cd ombudsman-validation-studio
docker-compose up -d
```

### Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

---

## 📚 Documentation

### Essential Guides
- **[User Manual](USER_MANUAL.md)** - Complete end-user guide (32,000+ words)
- **[Technical Manual](TECHNICAL_MANUAL.md)** - Developer and architecture documentation
- **[Architecture Guide](ARCHITECTURE.md)** - System architecture and design details
- **[Architecture Diagrams](ARCHITECTURE_DIAGRAM.md)** - Visual system diagrams (Mermaid)

### Deployment Guides
- **[Ubuntu Deployment](deployment/ubuntu/README.md)** - Deploy on Ubuntu VM
- **[Windows Deployment](deployment/windows/README.md)** - Deploy on Windows Server

---

## 📁 Project Structure

```
.
├── ombudsman-validation-studio/    # Main application
│   ├── backend/                    # FastAPI backend (Python 3.11)
│   ├── frontend/                   # React frontend (TypeScript)
│   └── docker-compose.yml          # Service orchestration
│
├── ombudsman_core/                 # Core validation library
│   └── src/ombudsman/
│       ├── core/                   # Core services
│       ├── pipeline/               # Pipeline engine
│       └── validation/             # 30+ validation modules
│
├── deployment/                     # VM deployment scripts
│   ├── ubuntu/                     # Ubuntu automated installer
│   └── windows/                    # Windows automated installer
│
├── obsolete/                       # Archived files
│
├── Makefile                        # Docker shortcuts
├── README.md                       # This file
├── USER_MANUAL.md                  # End-user guide
├── TECHNICAL_MANUAL.md             # Developer guide
├── ARCHITECTURE.md                 # Architecture documentation
└── ARCHITECTURE_DIAGRAM.md         # Visual diagrams
```

---

## ✨ Key Features

### 30+ Built-in Validators
- **Schema**: Column existence, data types, nullability
- **Data Quality**: Counts, nulls, uniqueness, statistics, distributions
- **Referential Integrity**: Foreign key validation
- **Dimensions**: SCD Type 1/2, business keys, surrogate keys
- **Facts**: Fact-dimension conformance, late arriving facts
- **Metrics**: Sums, averages, ratios
- **Time Series**: Continuity, duplicates, drift

### Intelligent Features
- **Workload Analysis**: Analyzes SQL Server Query Store
- **Smart Suggestions**: Auto-generates validation pipelines
- **Fuzzy Mapping**: Automatic table/column mapping
- **Comparison Viewer**: Row-by-row difference analysis
- **Visual Pipeline Builder**: Drag-and-drop workflows

### User Features
- **Project Management**: Organize by project
- **JWT Authentication**: Secure user management
- **Results Viewer**: Detailed drill-down
- **Metadata Extraction**: Auto-discover schemas

---

## 🛠️ Makefile Commands

```bash
# Quick Start
make up              # Start all services
make down            # Stop all services
make restart         # Restart all services
make status          # Show container status

# Development
make logs            # View all logs
make logs-backend    # View backend logs only
make logs-frontend   # View frontend logs only
make shell-backend   # Open backend shell
make shell-frontend  # Open frontend shell

# Maintenance
make rebuild         # Rebuild without cache
make clean           # Remove containers/volumes
make prune           # Clean up Docker system

# Testing
make test            # Run backend tests

# Help
make help            # Show all commands
```

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────┐
│              Ombudsman.AI Platform                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  React Frontend  ←→  FastAPI Backend               │
│    (Port 3000)        (Port 8000)                  │
│                            ↓                        │
│                    Core Library                     │
│                   (30+ Validators)                  │
│                            ↓                        │
│        ┌───────────────────┼──────────────┐         │
│        ↓                   ↓              ↓         │
│   SQL Server          Snowflake       OVS DB       │
│   (Source)            (Target)      (App Data)     │
└─────────────────────────────────────────────────────┘
```

---

## 🔧 Development

### Prerequisites
- Docker Engine 24.0+
- Docker Compose 2.20+
- 4GB RAM (8GB+ recommended)
- SQL Server access
- Snowflake account

### Environment Setup

**IMPORTANT**: The system uses a single unified configuration file to eliminate ambiguity.

Copy the example environment file:
```bash
cp ombudsman-validation-studio/.env.example ombudsman-validation-studio/.env
```

Edit `.env` with your database credentials:
```bash
# SQL Server Configuration
MSSQL_HOST=your-server
MSSQL_PORT=1433
MSSQL_DATABASE=your-database
MSSQL_USER=your-user
MSSQL_PASSWORD=your-password

# Snowflake Configuration
SNOWFLAKE_ACCOUNT=xyz.region.cloud
SNOWFLAKE_USER=your-user
SNOWFLAKE_PASSWORD=your-password
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=your-database
SNOWFLAKE_SCHEMA=your-schema

# JWT Secret
JWT_SECRET_KEY=change-this-to-random-32-chars
```

**Configuration Architecture**:
- **Single Source of Truth**: `ombudsman-validation-studio/.env`
- **Symlinked**: `ombudsman_core/.env` → `ombudsman-validation-studio/.env`
- **Project Overrides**: Managed via UI in each project's configuration
- **No Duplication**: You only need to configure database credentials once

### Run Tests

```bash
make test
```

---

## 🚀 Deployment

### Single VM Deployment

**Ubuntu 22.04:**
```bash
cd deployment/ubuntu
sudo ./pre-check.sh    # Verify system
sudo ./install.sh      # Install
./verify.sh            # Verify
```

**Windows Server 2022:**
```powershell
cd deployment\windows
.\install.ps1
```

See detailed guides:
- [Ubuntu Deployment Guide](deployment/ubuntu/README.md)
- [Windows Deployment Guide](deployment/windows/README.md)

---

## 📖 Usage Overview

1. **Create Project** - Configure source/target databases
2. **Map Databases** - Map schemas, tables, columns
3. **Extract Metadata** - Auto-discover database structure
4. **Build Pipeline** - Add validation steps
5. **Execute Pipeline** - Run validations
6. **View Results** - Analyze pass/fail results

For detailed usage, see [User Manual](USER_MANUAL.md).

---

## 🧪 Testing

```bash
# Run all tests
make test

# Run specific test
cd ombudsman-validation-studio
docker-compose exec studio-backend pytest tests/test_auth.py

# Run with coverage
docker-compose exec studio-backend pytest --cov
```

---

## 🛠️ Technology Stack

**Frontend:**
- React 18 + TypeScript
- Material-UI 6
- Vite build tool
- React Router 7

**Backend:**
- FastAPI 0.115
- Python 3.11
- JWT Authentication
- Uvicorn ASGI

**Database Drivers:**
- pyodbc 5.2 (SQL Server)
- snowflake-connector-python

**Infrastructure:**
- Docker & Docker Compose
- Systemd (auto-start)

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Run tests: `make test`
5. Submit pull request

---

## 📄 License

Copyright © 2025 Ombudsman.AI. All rights reserved.

---

## 📞 Support

- **User Guide**: [USER_MANUAL.md](USER_MANUAL.md)
- **Tech Guide**: [TECHNICAL_MANUAL.md](TECHNICAL_MANUAL.md)
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)

---

**Made with ❤️ by the Ombudsman.AI Team**
