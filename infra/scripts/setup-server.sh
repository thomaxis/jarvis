#!/bin/bash
# First-time VPS setup: install Docker, create user, configure firewall
# Run as root on a fresh Debian 12 server

set -euo pipefail

echo "=== Jarvis OS Server Setup ==="

# Update system
apt-get update && apt-get upgrade -y

# Install essentials
apt-get install -y curl git ufw fail2ban unattended-upgrades

# Create non-root user (if not exists)
if ! id "jarvis" &>/dev/null; then
    useradd -m -s /bin/bash jarvis
    usermod -aG sudo jarvis
    echo "Created user 'jarvis'. Set a password with: passwd jarvis"
fi

# Install Docker
if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | bash
    usermod -aG docker jarvis
    systemctl enable docker
    echo "Docker installed."
fi

# Install Docker Compose plugin
if ! docker compose version &>/dev/null; then
    apt-get install -y docker-compose-plugin
fi

# Configure firewall
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP (redirect to HTTPS)
ufw allow 443/tcp   # HTTPS + WSS
ufw --force enable
echo "Firewall configured: 22, 80, 443 open."

# Disable root SSH login
sed -i 's/^PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^#PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart sshd

# Install certbot for Let's Encrypt
apt-get install -y certbot

# Create project directory
mkdir -p /opt/jarvis
chown jarvis:jarvis /opt/jarvis

# Setup daily backup cron
cat > /etc/cron.daily/jarvis-backup << 'CRON'
#!/bin/bash
/opt/jarvis/infra/scripts/backup.sh >> /var/log/jarvis-backup.log 2>&1
CRON
chmod +x /etc/cron.daily/jarvis-backup

echo ""
echo "=== Setup complete ==="
echo "Next steps:"
echo "1. Copy SSH key: ssh-copy-id jarvis@$(hostname -I | awk '{print $1}')"
echo "2. Clone repo to /opt/jarvis"
echo "3. Copy .env.example to .env and fill in secrets"
echo "4. Run: docker compose -f infra/docker-compose.yml up -d"
echo "5. Set up TLS: certbot certonly --standalone -d jarvis.yourdomain.com"
echo "6. Install and configure Nginx with infra/nginx/jarvis.conf"
