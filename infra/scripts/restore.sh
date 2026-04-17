#!/bin/bash
# Restore PostgreSQL from backup
# Usage: ./restore.sh /path/to/jarvis_20260417_120000.sql.gz

set -euo pipefail

if [ $# -eq 0 ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo ""
    echo "Available backups:"
    ls -lh /opt/jarvis/backups/jarvis_*.sql.gz 2>/dev/null || echo "  No backups found."
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "=== Jarvis Restore ==="
echo "Restoring from: $BACKUP_FILE"
echo ""
echo "WARNING: This will REPLACE all data in the jarvis database."
read -p "Are you sure? (type 'yes' to confirm): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

echo "Stopping brain..."
docker compose -f /opt/jarvis/infra/docker-compose.yml stop brain

echo "Dropping and recreating database..."
docker exec jarvis-postgres psql -U jarvis -c "DROP DATABASE IF EXISTS jarvis;"
docker exec jarvis-postgres psql -U jarvis -c "CREATE DATABASE jarvis;"

echo "Restoring backup..."
gunzip -c "$BACKUP_FILE" | docker exec -i jarvis-postgres psql -U jarvis jarvis

echo "Starting brain..."
docker compose -f /opt/jarvis/infra/docker-compose.yml start brain

echo "Restore complete."
