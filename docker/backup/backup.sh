#!/usr/bin/env sh
# АППК — резервное копирование базы данных
# Запускается из контейнера backup по расписанию cron.
# Ротация: хранит последние 7 дней.

set -e

BACKUP_DIR="/backups"
DB_HOST="${POSTGRES_HOST:-db}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-appk}"
DB_USER="${POSTGRES_USER:-appk}"
PGPASSWORD="${POSTGRES_PASSWORD:-appk}"
KEEP_DAYS=7

export PGPASSWORD

DATE=$(date +"%Y%m%d_%H%M%S")
FILENAME="${BACKUP_DIR}/appk_${DATE}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup: $FILENAME"

pg_dump \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  --no-password \
  --format=plain \
  | gzip -9 > "$FILENAME"

echo "[$(date)] Backup complete: $(du -sh "$FILENAME" | cut -f1)"

# Ротация: удаляем файлы старше KEEP_DAYS дней
find "$BACKUP_DIR" -name "appk_*.sql.gz" -mtime +"$KEEP_DAYS" -delete
echo "[$(date)] Old backups rotated (kept last ${KEEP_DAYS} days)"
