#!/bin/bash
# ZOYA AI Backend — scheduled backup helper.
# Usage (cron, daily 03:00):  0 3 * * * /path/to/backend/scripts/backup_now.sh
# Requires: API_BASE, ADMIN_USER, ADMIN_PASS env vars, or edit the defaults.
set -e
API_BASE="${API_BASE:-http://127.0.0.1:8000}"
ADMIN_USER="${ADMIN_USER:-admin}"
ADMIN_PASS="${ADMIN_PASS:-}"

if [ -z "$ADMIN_PASS" ]; then
  echo "Set ADMIN_PASS env var to the admin password." >&2
  exit 1
fi

TOKEN=$(curl -s -X POST "$API_BASE/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$ADMIN_USER\",\"password\":\"$ADMIN_PASS\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -s -X POST "$API_BASE/backup/create" -H "Authorization: Bearer $TOKEN"
echo
echo "Backup done. Old backups are pruned by BACKUP_RETENTION_DAYS (see README)."
