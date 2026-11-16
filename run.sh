#!/bin/bash
# ZOYA AI Backend — run the server (development).
# Usage: ./run.sh [port]
set -e
cd "$(dirname "$0")"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created .env from .env.example — edit SECRET_KEY before production use."
fi
PORT="${1:-8000}"
exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --log-level info
