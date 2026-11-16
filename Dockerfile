# ZOYA AI Backend — Docker image (Phase 1)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static
COPY .env.example ./.env.example
COPY run.sh ./run.sh

# Data dirs (SQLite file, backups, logs) — create them so SQLite can open the DB file.
RUN mkdir -p /app/data /app/backups /app/logs
ENV DATABASE_URL=sqlite:////app/data/zoya.db \
    BACKUP_DIR=/app/backups

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
