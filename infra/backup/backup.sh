#!/bin/bash
set -euo pipefail

BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y-%m-%d_%H%M)
RETENTION_DAYS=${RETENTION_DAYS:-7}

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup..."

# PostgreSQL dump
echo "[$(date)] Dumping PostgreSQL..."
PGPASSWORD="$DB_PASSWORD" pg_dump \
    -h "$DB_HOST" \
    -p "${DB_PORT:-5432}" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --no-owner \
    --no-privileges \
    | gzip > "$BACKUP_DIR/nexstream-db-${TIMESTAMP}.sql.gz"

echo "[$(date)] PostgreSQL dump complete: nexstream-db-${TIMESTAMP}.sql.gz"

# ChromaDB volume backup
if [ -d "/chroma-data" ]; then
    echo "[$(date)] Backing up ChromaDB volume..."
    tar czf "$BACKUP_DIR/nexstream-chroma-${TIMESTAMP}.tar.gz" -C /chroma-data .
    echo "[$(date)] ChromaDB backup complete: nexstream-chroma-${TIMESTAMP}.tar.gz"
else
    echo "[$(date)] ChromaDB data directory not mounted, skipping."
fi

# Cleanup old backups
echo "[$(date)] Cleaning backups older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -name "nexstream-*" -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true

# Summary
echo "[$(date)] Backup complete. Contents:"
ls -lh "$BACKUP_DIR"/nexstream-* 2>/dev/null || echo "  (no backups found)"
echo "[$(date)] Done."
