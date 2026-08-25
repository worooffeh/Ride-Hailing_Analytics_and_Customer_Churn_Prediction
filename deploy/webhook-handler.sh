#!/bin/bash
#---------------------------------------------------------------------------
# GitHub Actions Webhook Handler for Automated Deployments
#---------------------------------------------------------------------------
# This is a simple example webhook receiver (deploy on your server)
# For production, use: ngrok, AWS Lambda, or a dedicated webhook service
#
# Setup on server:
#   1. Save this script: /opt/ridewise/webhook-handler.sh
#   2. Run as service: systemd service (see systemd/ridewise-webhook.service)
#   3. Set GitHub Actions secret: DEPLOY_WEBHOOK_URL=https://your-server/webhook
#---------------------------------------------------------------------------

#!/bin/bash

# Log file
LOG_FILE="/var/log/ridewise/webhook.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log "Webhook received: $1"

# Pull latest code and redeploy
cd /opt/ridewise || exit 1
git pull origin main
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d

log "Deployment complete"
echo "OK"
