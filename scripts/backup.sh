#!/usr/bin/env bash
# Daily PostgreSQL backup (cron: 0 2 * * * /path/scripts/backup.sh). Keeps 14 days.
set -euo pipefail
DIR="${BACKUP_DIR:-./backups}"; mkdir -p "$DIR"
FILE="$DIR/oncosphere_$(date +%Y%m%d_%H%M%S).sql.gz"
PGPASSWORD="${DB_PASSWORD:-postgres}" pg_dump -h "${DB_HOST:-localhost}" -U "${DB_USER:-postgres}" "${DB_NAME:-oncosphere}" | gzip > "$FILE"
find "$DIR" -name 'oncosphere_*.sql.gz' -mtime +14 -delete
echo "Backup written: $FILE"
# Restore:  gunzip -c FILE | psql -h HOST -U USER oncosphere
