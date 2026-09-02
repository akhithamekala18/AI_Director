# =============================================================================
# AI Director — Backend Dockerfile
# Multi-stage build: dependencies -> runtime
# =============================================================================

# --- Stage 1: Dependencies --------------------------------------------------
FROM python:3.12-slim AS deps
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./
RUN pip install --no-cache-dir . 2>/dev/null

# --- Stage 2: Runtime -------------------------------------------------------
FROM python:3.12-slim AS runtime
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/*
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin
COPY . .
RUN DJANGO_SECRET_KEY=build-placeholder DJANGO_ALLOWED_HOSTS=localhost CREDENTIAL_ENCRYPTION_KEY=build-placeholder python manage.py collectstatic --noinput 2>/dev/null || true
RUN adduser --disabled-password --gecos '' appuser
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/core/healthz/')" || exit 1
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]
