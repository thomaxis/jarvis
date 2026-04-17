#!/bin/bash
# Deploy latest changes: pull, rebuild, restart
# Run from /opt/jarvis as the jarvis user

set -euo pipefail

DEPLOY_DIR="/opt/jarvis"
cd "$DEPLOY_DIR"

echo "=== Jarvis Deploy ==="
echo "$(date '+%Y-%m-%d %H:%M:%S')"

# Pull latest
echo "Pulling latest changes..."
git pull origin dev

# Rebuild and restart containers
echo "Rebuilding containers..."
docker compose -f infra/docker-compose.yml build --no-cache brain

echo "Restarting services..."
docker compose -f infra/docker-compose.yml up -d

# Wait for health check
echo "Waiting for brain to start..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8400/health > /dev/null 2>&1; then
        echo "Brain is healthy!"
        curl -s http://localhost:8400/health | python3 -m json.tool
        exit 0
    fi
    sleep 2
done

echo "ERROR: Brain failed to start within 60 seconds"
docker compose -f infra/docker-compose.yml logs --tail=50 brain
exit 1
