#!/bin/bash
# Backup PostgreSQL database
# Run daily via cron or manually

set -euo pipefail

DEPLOY_DIR="/opt/jarvis"
BACKUP_DIR="$DEPLOY_DIR/backups"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_FILE="$BACKUP_DIR/jarvis_${TIMESTAMP}.sql.gz"
RETAIN_DAYS=30

mkdir -p "$BACKUP_DIR"

echo "=== Jarvis Backup ==="
echo "$(date '+%Y-%m-%d %H:%M:%S')"

# Dump PostgreSQL
echo "Dumping database..."
docker exec jarvis-postgres pg_dump -U jarvis jarvis | gzip > "$BACKUP_FILE"

if [ -f "$BACKUP_FILE" ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "Backup created: $BACKUP_FILE ($SIZE)"
else
    echo "ERROR: Backup file not created"
    exit 1
fi

# Remove old backups
echo "Cleaning backups older than ${RETAIN_DAYS} days..."
find "$BACKUP_DIR" -name "jarvis_*.sql.gz" -mtime +$RETAIN_DAYS -delete

echo "Backup complete."
