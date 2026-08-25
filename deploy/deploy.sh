#!/bin/bash
#---------------------------------------------------------------------------
# Production deployment script for RideWise
#---------------------------------------------------------------------------
# Usage: ./deploy/deploy.sh
# Requires: .env file with Docker credentials and domain config
#---------------------------------------------------------------------------

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load environment
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Run: cp .env.example .env && nano .env"
    exit 1
fi

source .env

echo -e "${YELLOW}=== RideWise Production Deployment ===${NC}"

# Step 1: Validate configuration
echo -e "\n${YELLOW}[1/6] Validating configuration...${NC}"
if [ -z "$DOCKER_USERNAME" ] || [ -z "$DOCKER_PASSWORD" ]; then
    echo -e "${RED}Error: DOCKER_USERNAME and DOCKER_PASSWORD must be set in .env${NC}"
    exit 1
fi
if [ -z "$SERVER_DOMAIN" ]; then
    echo -e "${RED}Error: SERVER_DOMAIN must be set in .env${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Configuration valid${NC}"

# Step 2: Authenticate with Docker
echo -e "\n${YELLOW}[2/6] Authenticating with Docker Registry...${NC}"
echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
echo -e "${GREEN}✓ Docker login successful${NC}"

# Step 3: Pull latest images
echo -e "\n${YELLOW}[3/6] Pulling latest images...${NC}"
docker compose -f docker-compose.prod.yml pull
echo -e "${GREEN}✓ Images pulled${NC}"

# Step 4: Validate docker-compose config
echo -e "\n${YELLOW}[4/6] Validating docker-compose configuration...${NC}"
docker compose -f docker-compose.prod.yml config > /dev/null
echo -e "${GREEN}✓ Configuration valid${NC}"

# Step 5: Start services
echo -e "\n${YELLOW}[5/6] Starting services...${NC}"
docker compose -f docker-compose.prod.yml up -d
sleep 5
echo -e "${GREEN}✓ Services started${NC}"

# Step 6: Verify deployment
echo -e "\n${YELLOW}[6/6] Verifying deployment...${NC}"
docker compose -f docker-compose.prod.yml ps

# Health checks
echo -e "\n${YELLOW}Checking service health...${NC}"
if docker compose -f docker-compose.prod.yml exec api curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API is healthy${NC}"
else
    echo -e "${RED}✗ API health check failed${NC}"
    docker compose -f docker-compose.prod.yml logs api
    exit 1
fi

if docker compose -f docker-compose.prod.yml exec ui curl -f http://localhost:8501/_stcore/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ UI is healthy${NC}"
else
    echo -e "${RED}✗ UI health check failed${NC}"
    docker compose -f docker-compose.prod.yml logs ui
    exit 1
fi

if docker compose -f docker-compose.prod.yml exec nginx nginx -t > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Nginx config is valid${NC}"
else
    echo -e "${RED}✗ Nginx validation failed${NC}"
    docker compose -f docker-compose.prod.yml logs nginx
    exit 1
fi

echo -e "\n${GREEN}=== Deployment successful! ===${NC}"
echo -e "Services available at:"
echo -e "  API:       https://${SERVER_DOMAIN}/api/docs"
echo -e "  Dashboard: https://${SERVER_DOMAIN}/"
echo -e "\nView logs with:"
echo -e "  ${YELLOW}docker compose -f docker-compose.prod.yml logs -f${NC}"
