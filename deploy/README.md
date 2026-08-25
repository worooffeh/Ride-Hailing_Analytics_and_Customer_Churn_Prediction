# Production Deployment Guide

## Overview

This directory contains production-ready deployment configuration for RideWise:
- Nginx reverse proxy (HTTP/HTTPS)
- Docker Compose production stack
- SSL/TLS setup with Let's Encrypt
- GitHub Actions CI/CD automation

## Quick Start

### 1. Registry & Credentials Setup

**Docker Hub:**
```bash
# Create a Docker Hub account and access token
# Go to Docker Hub → Account Settings → Security → New Access Token

# Store secrets in GitHub repository
# Settings → Secrets and Variables → Actions → New Repository Secret
DOCKER_USERNAME=your_username
DOCKER_PASSWORD=your_access_token
DEPLOY_WEBHOOK_URL=https://your-server.com/webhook (optional)
```

**GitHub Container Registry (alternative to Docker Hub):**
```bash
# Uses automatic GITHUB_TOKEN, no setup needed
# Just modify `.github/workflows/build-and-push.yml`:
# Change REGISTRY: ghcr.io
# Change IMAGE_NAME: ghcr.io/${{ github.repository_owner }}/ridewise-api
```

### 2. Production Server Setup

```bash
# SSH into your EC2 / VPS
ssh ubuntu@your-server-ip

# Install Docker & Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Certbot (for SSL)
sudo apt-get update && sudo apt-get install -y certbot python3-certbot-nginx

# Clone your repository
git clone https://github.com/your-username/ridewise.git
cd ridewise
```

### 3. SSL Certificate Setup (Let's Encrypt)

```bash
# Request initial certificate
sudo certbot certonly --standalone -d ridewise.example.com -d www.ridewise.example.com \
  --non-interactive --agree-tos --email admin@example.com

# Auto-renewal (run daily via cron)
sudo certbot renew --quiet

# Verify renewal
sudo certbot certificates
```

### 4. Configure Environment

```bash
# Copy and edit environment file
cp .env.example .env

# Edit .env with your values
nano .env

# Verify critical variables
grep DOCKER_REGISTRY_URL .env
grep DOCKER_USERNAME .env
grep SERVER_DOMAIN .env
```

### 5. Deploy & Start Services

```bash
# Authenticate with Docker registry
echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin

# Pull latest images
docker compose -f docker-compose.prod.yml pull

# Start the stack
docker compose -f docker-compose.prod.yml up -d

# Verify services are running
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f nginx
```

### 6. Verify Deployment

```bash
# Check API health
curl -I https://ridewise.example.com/api/health

# Check Streamlit is reachable
curl -I https://ridewise.example.com/

# View logs
docker compose -f docker-compose.prod.yml logs api ui nginx

# Monitor resource usage
docker stats
```

## CI/CD Workflow

### Automated Build & Push

**Trigger:** Push to `main` branch or tag `v*`

```bash
# Create a release (triggers workflow)
git tag v1.0.0
git push origin v1.0.0
```

**Workflow Steps:**
1. Build API & UI images (multi-stage, cached)
2. Push to Docker Hub with tags: `latest`, `v1.0.0`, `main`, `sha-abc123`
3. Run Trivy vulnerability scanner
4. Send webhook to production server (optional)

### Manual Trigger

```bash
# GitHub CLI
gh workflow run build-and-push.yml -f branch=main

# Or via GitHub UI: Actions → Build and Push → Run Workflow
```

## Nginx Configuration

**Location:** `/etc/nginx/conf.d/ridewise.conf`

**Key Features:**
- ✅ HTTP → HTTPS redirect
- ✅ Modern SSL/TLS (A+ rating)
- ✅ Security headers (HSTS, CSP, etc.)
- ✅ WebSocket support (Streamlit real-time)
- ✅ Reverse proxy to internal services
- ✅ Gzip compression
- ✅ Rate limiting (optional)

**Testing:**
```bash
# Validate Nginx config
sudo nginx -t

# Reload without downtime
sudo systemctl reload nginx

# Check SSL grade
# https://www.ssllabs.com/ssltest/
```

## Monitoring & Logging

### Container Logs

```bash
# Follow real-time logs
docker compose -f docker-compose.prod.yml logs -f

# View specific service
docker compose -f docker-compose.prod.yml logs api
docker compose -f docker-compose.prod.yml logs ui
docker compose -f docker-compose.prod.yml logs nginx

# Last 100 lines
docker compose -f docker-compose.prod.yml logs --tail 100
```

### Nginx Logs

```bash
# Access logs
sudo tail -f logs/nginx/ridewise-access.log

# Error logs
sudo tail -f logs/nginx/ridewise-error.log

# Parse common errors
grep "502\|503\|504" logs/nginx/ridewise-access.log
```

### System Monitoring

```bash
# Resource usage
docker stats

# Disk space
df -h

# Memory pressure
free -h

# Container health
docker ps --format "table {{.Names}}\t{{.Status}}"
```

## Updating Deployment

### Pull Latest Images

```bash
# Fetch latest from registry
docker compose -f docker-compose.prod.yml pull

# Restart services with new images
docker compose -f docker-compose.prod.yml up -d

# Verify rollout
docker compose -f docker-compose.prod.yml ps
```

### Rollback

```bash
# Revert to previous image tag
docker compose -f docker-compose.prod.yml down
# Edit docker-compose.prod.yml: change image tags to previous version
docker compose -f docker-compose.prod.yml up -d
```

## Troubleshooting

### Services won't start

```bash
# Check logs
docker compose -f docker-compose.prod.yml logs

# Common issues:
# - Port 80/443 already in use: sudo lsof -i :80
# - Memory limit: increase Docker's memory allocation
# - Network issues: docker network inspect ridewise-net
```

### 502 Bad Gateway (Nginx → API)

```bash
# Check if API is healthy
docker compose -f docker-compose.prod.yml exec api curl http://localhost:8000/health

# Check Nginx config
sudo nginx -t
sudo systemctl reload nginx

# Check container networking
docker inspect ridewise-api | grep -A 5 NetworkSettings
```

### SSL Certificate Issues

```bash
# Check certificate status
sudo certbot certificates

# Renew manually
sudo certbot renew --force-renewal

# View certificate details
openssl x509 -in /etc/letsencrypt/live/ridewise.example.com/fullchain.pem -text -noout
```

### High CPU/Memory Usage

```bash
# Identify heavy container
docker stats

# Increase limits (optional, in docker-compose.prod.yml)
# deploy:
#   resources:
#     limits:
#       cpus: '1'
#       memory: 2G

# Restart stack
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d
```

## Backup & Recovery

```bash
# Backup docker volumes (if using persistent storage)
docker run --rm -v ridewise-data:/data -v $(pwd)/backups:/backup \
  ubuntu tar czf /backup/ridewise-$(date +%Y%m%d).tar.gz -C /data .

# Restore from backup
tar xzf backups/ridewise-20240101.tar.gz -C /docker-volume-path/
```

## Security Best Practices

- ✅ Use environment variables for secrets (never commit .env)
- ✅ Run containers as non-root (appuser)
- ✅ Enable firewall: `sudo ufw allow 80,443/tcp`
- ✅ Set up fail2ban for Nginx: `sudo apt-get install fail2ban`
- ✅ Regular vulnerability scans: Trivy (auto-run in CI/CD)
- ✅ Monitor for exposed credentials: `git-secrets`
- ✅ Keep Docker images updated: `docker system prune -a`

## Production Checklist

- [ ] GitHub secrets configured (DOCKER_USERNAME, DOCKER_PASSWORD)
- [ ] .env file created and populated (not committed)
- [ ] SSL certificate obtained and renewed
- [ ] Nginx config deployed and tested
- [ ] Services reachable: API health check passes, UI loads
- [ ] Logs are being collected and monitored
- [ ] Backups automated (if using persistent storage)
- [ ] Firewall rules configured
- [ ] DNS A record points to server IP
- [ ] Monitoring/alerting set up (Prometheus, New Relic, etc.)

## Support

For issues, check logs or open an issue on GitHub.
