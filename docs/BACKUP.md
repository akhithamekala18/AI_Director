# AI Director — Backup & Retention Policy

**Version:** 1.0 | **Last Updated:** 2026-09-02

## 1. Backup Tiers

### Tier 1 — Critical (RPO: 1hr, RTO: 4hr)
- PostgreSQL database (audit, publishing, credentials)
- Encryption keys (never change, never commit)
- Audit logs (immutable, append-only)

### Tier 2 — Important (RPO: 24hr, RTO: 24hr)
- User-uploaded media
- Celery task results
- Frontend build artifacts

### Tier 3 — Configuration (On change, RTO: 1hr)
- Environment variables (encrypt before storing)
- Docker Compose / Nginx configs

## 2. Automated Backup (Recommended)

```bash
# Daily database backup (cron: 0 2 * * *)
docker compose exec -T postgres pg_dump -U ai_director ai_director | gzip > /backups/db_$(date +%Y%m%d).sql.gz

# Daily media backup
docker compose exec -T backend tar czf - /app/media > /backups/media_$(date +%Y%m%d).tar.gz
```

## 3. Retention Policy

| Backup Type | Retention |
|-------------|-----------|
| Database (daily) | 30 days |
| Database (weekly) | 12 weeks |
| Database (monthly) | 12 months |
| Media (daily) | 7 days |
| Media (weekly) | 6 months |
| Config | All versions 30 days, then latest |

## 4. Recovery

```bash
# Full database restore
docker compose stop backend celery-worker celery-beat
docker compose exec postgres dropdb -U ai_director ai_director
docker compose exec postgres createdb -U ai_director ai_director
gunzip -c backup.sql.gz | docker compose exec -T postgres psql -U ai_director ai_director
docker compose up -d backend celery-worker celery-beat
```

## 5. Audit Trail Preservation

Per Project Overview §5.8:
- Audit records are append-only in PostgreSQL
- Backups include all audit tables
- Audit data is never deleted by retention policies
- Audit tables backed up with Tier 1 priority

## 6. Disaster Recovery

| Scenario | Target RTO | Target RPO |
|----------|------------|------------|
| Database corruption | 4 hours | 1 hour |
| Server failure | 2 hours | 1 hour |
| Infrastructure loss | 8 hours | 24 hours |
| Credential compromise | 1 hour | Immediate |

Procedure: provision new infra → restore DB → restore media → restore config → rebuild containers → verify.
