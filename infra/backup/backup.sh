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

# Şifreleme (opt-in — BACKUP_GPG_PASSPHRASE set edilmezse atlanır, dosyalar düz kalır)
if [ -n "${BACKUP_GPG_PASSPHRASE:-}" ]; then
    echo "[$(date)] Encrypting backups (GPG AES256)..."
    for f in "$BACKUP_DIR/nexstream-db-${TIMESTAMP}.sql.gz" "$BACKUP_DIR/nexstream-chroma-${TIMESTAMP}.tar.gz"; do
        if [ -f "$f" ]; then
            gpg --batch --yes --passphrase "$BACKUP_GPG_PASSPHRASE" --symmetric --cipher-algo AES256 -o "${f}.gpg" "$f"
            rm -f "$f"
            echo "[$(date)] Encrypted: ${f}.gpg"
        fi
    done
else
    echo "[$(date)] BACKUP_GPG_PASSPHRASE not set — backups stored unencrypted."
fi

# Offsite upload (opt-in — RCLONE_REMOTE set edilmezse atlanır, sadece local kalır)
# rclone.conf, /root/.config/rclone/rclone.conf'a mount edilmiş olmalı (bkz. docker-compose.prod.yml).
if [ -n "${RCLONE_REMOTE:-}" ]; then
    echo "[$(date)] Uploading this run's backups to offsite remote: ${RCLONE_REMOTE}..."
    if rclone copy "$BACKUP_DIR" "$RCLONE_REMOTE" --include "nexstream-*-${TIMESTAMP}.*"; then
        echo "[$(date)] Offsite upload complete."
    else
        echo "[$(date)] WARNING: offsite upload failed — local backup retained, will retry next run."
    fi
else
    echo "[$(date)] RCLONE_REMOTE not set — skipping offsite upload (local-only backup)."
fi

# Cleanup old backups
echo "[$(date)] Cleaning backups older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -name "nexstream-*" -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true

# Summary
echo "[$(date)] Backup complete. Contents:"
ls -lh "$BACKUP_DIR"/nexstream-* 2>/dev/null || echo "  (no backups found)"
echo "[$(date)] Done."
