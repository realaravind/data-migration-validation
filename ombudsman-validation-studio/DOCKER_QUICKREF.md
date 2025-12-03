# 🐳 Docker Quick Reference

## Start Services

### Development (Hot Reload)
```bash
docker-compose -f docker-compose.dev.yml up
```

### Production
```bash
docker-compose up
```

## Common Commands

| Action | Command |
|--------|---------|
| **Start with rebuild** | `docker-compose up --build` |
| **Start in background** | `docker-compose up -d` |
| **Stop services** | `docker-compose down` |
| **View logs** | `docker-compose logs -f` |
| **Restart service** | `docker-compose restart studio-backend` |
| **Shell into backend** | `docker-compose exec studio-backend /bin/bash` |
| **Shell into frontend** | `docker-compose exec studio-frontend /bin/sh` |

## Service URLs

- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Files Overview

```
ombudsman-validation-studio/
├── docker-compose.yml          # Production config
├── docker-compose.dev.yml      # Development config (use this!)
├── .dockerignore               # Files to exclude from builds
├── DOCKER.md                   # Full documentation
├── DOCKER_VALIDATION_REPORT.md # Validation results
├── backend/
│   ├── Dockerfile              # Backend container
│   └── requirements.txt        # Python dependencies
└── frontend/
    ├── Dockerfile              # Production frontend
    └── Dockerfile.dev          # Development frontend
```

## Troubleshooting

**Port in use?**
```bash
lsof -ti:3000 | xargs kill -9  # Kill frontend
lsof -ti:8000 | xargs kill -9  # Kill backend
```

**Not updating?**
```bash
docker-compose restart studio-frontend
```

**Clean slate?**
```bash
docker-compose down -v
docker system prune -a
```

---
📖 For detailed help, see [DOCKER.md](./DOCKER.md)
