# AI Director — Deployment Runbook

**Version:** 1.0 | **Last Updated:** 2026-09-02

## 1. Prerequisites

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 vCPUs | 4 vCPUs |
| RAM | 4 GB | 8 GB |
| Storage | 20 GB SSD | 50 GB SSD |
| Database | PostgreSQL 16 | PostgreSQL 16+ |
| Cache/Queue | Redis 7 | Redis 7+ |

Required: Docker 24+, Docker Compose v2, Node.js 20+ (for frontend builds)

## 2. Environment Setup

```bash
git clone <repo-url> && cd ai-director
cd backend && cp .env.example .env
# Edit .env with production values (see .env.example comments)
```

### Required Environment Variables

| Variable | Description |
|----------|-------------|
| `DJANGO_SECRET_KEY` | Cryptographic secret (>=50 chars) |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames |
| `DATABASE_URL` | PostgreSQL URL |
| `REDIS_URL` | Redis URL |
| `CREDENTIAL_ENCRYPTION_KEY` | Fernet key for credential encryption |
| `OPENAI_API_KEY` | OpenAI API key |

## 3. First Deployment

```bash
# Start infrastructure
docker compose up -d postgres redis
# Wait for health checks
docker compose ps
# Apply migrations
docker compose run --rm backend python manage.py migrate
# Create admin user
docker compose run --rm backend python manage.py createsuperuser
# Build frontend
cd frontend && npm install && npm run build && cd ..
# Start all services
docker compose up -d --build
```

### Verify

```bash
curl http://localhost/api/core/healthz/
# Expected: {"status": "ok", "service": "ai-director-backend"}
curl -s http://localhost/ | head -5
# Expected: HTML from React SPA
```

## 4. Regular Deployments

```bash
git pull origin feature/day-1-foundation
cd frontend && npm run build && cd ..
docker compose up -d --build backend celery-worker celery-beat frontend
docker compose exec backend python manage.py migrate  # if migrations changed
```

## 5. Rollback

```bash
# Application rollback
git checkout <previous-commit>
docker compose up -d --build

# Database rollback (backup first!)
docker compose exec backend python manage.py migrate <app_name> <previous_migration>
```

## 6. Health Checks

- **Endpoint:** `GET /api/core/healthz/` — returns `{"status": "ok"}`
- **Docker:** `docker compose ps` — all services should show "healthy"
- **Logs:** `docker compose logs -f backend celery-worker`

## 7. Key Metrics

| Metric | Alert Threshold | Action |
|--------|----------------|--------|
| Health response time | > 5s | Check database |
| Celery queue depth | > 100 | Scale workers |
| Disk usage | > 85% | Clean old data |
| Error rate (5xx) | > 1% | Check logs |

## 8. Backup

```bash
# Database backup
docker compose exec postgres pg_dump -U ai_director ai_director | gzip > backup_$(date +%Y%m%d).sql.gz
# Restore
gunzip -c backup.sql.gz | docker compose exec -T postgres psql -U ai_director ai_director
```

Retain: 30 days daily, 12 weeks weekly. See docs/BACKUP.md for full policy.

## 9. Post-Deployment Checklist

- [ ] Health endpoint returns ok
- [ ] Frontend loads without console errors
- [ ] Login/register flow works
- [ ] Celery worker is processing tasks
- [ ] No Django errors in logs
- [ ] Migrations are applied
- [ ] Static files served correctly
