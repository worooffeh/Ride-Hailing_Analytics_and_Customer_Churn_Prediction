#---------------------------------------------------------------------------
# Quick Registry Push Guide
#---------------------------------------------------------------------------

## Option 1: Docker Hub (Recommended for Public Projects)

### Prerequisites
- Docker Hub account: https://hub.docker.com/signup
- Access token: https://hub.docker.com/settings/security

### Manual Push

```bash
# 1. Authenticate
docker login -u your_username

# 2. Tag your local images
docker tag ridewise-api:latest your_username/ridewise-api:latest
docker tag ridewise-api:latest your_username/ridewise-api:v1.0.0

docker tag ridewise-ui:latest your_username/ridewise-ui:latest
docker tag ridewise-ui:latest your_username/ridewise-ui:v1.0.0

# 3. Push to Docker Hub
docker push your_username/ridewise-api:latest
docker push your_username/ridewise-api:v1.0.0
docker push your_username/ridewise-ui:latest
docker push your_username/ridewise-ui:v1.0.0
```

### Verify
```bash
# View on Docker Hub
open https://hub.docker.com/r/your_username/ridewise-api
open https://hub.docker.com/r/your_username/ridewise-ui

# Pull and test
docker pull your_username/ridewise-api:latest
```

---

## Option 2: GitHub Container Registry (ghcr.io) - Free Private Repos

### Prerequisites
- GitHub Personal Access Token: https://github.com/settings/tokens
  - Scopes: `write:packages`, `read:packages`, `delete:packages`

### Manual Push

```bash
# 1. Authenticate
echo $GH_TOKEN | docker login ghcr.io -u your_github_username --password-stdin

# 2. Tag images
docker tag ridewise-api:latest ghcr.io/your_github_username/ridewise-api:latest
docker tag ridewise-ui:latest ghcr.io/your_github_username/ridewise-ui:latest

# 3. Push
docker push ghcr.io/your_github_username/ridewise-api:latest
docker push ghcr.io/your_github_username/ridewise-ui:latest
```

### Verify
```bash
# View on GitHub Packages
open https://github.com/your_username/ridewise/pkgs/container/ridewise-api

# Pull and test
docker pull ghcr.io/your_github_username/ridewise-api:latest
```

---

## Option 3: AWS ECR (Elastic Container Registry)

### Prerequisites
- AWS Account with ECR service enabled
- AWS CLI configured: `aws configure`

### Setup

```bash
# Create ECR repositories
aws ecr create-repository --repository-name ridewise-api --region us-east-1
aws ecr create-repository --repository-name ridewise-ui --region us-east-1

# Get repository URLs
aws ecr describe-repositories --region us-east-1 --query 'repositories[*].repositoryUri'
# Output: 123456789.dkr.ecr.us-east-1.amazonaws.com/ridewise-api
```

### Push

```bash
# Get login token (expires after 12 hours)
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com

# Tag images
docker tag ridewise-api:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/ridewise-api:latest
docker tag ridewise-ui:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/ridewise-ui:latest

# Push
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/ridewise-api:latest
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/ridewise-ui:latest
```

---

## GitHub Actions Automation (Recommended)

### Setup

1. **Create personal access token (if using Docker Hub or ECR):**
   - Docker Hub: https://hub.docker.com/settings/security
   - ECR: Use AWS credentials

2. **Add GitHub repository secrets:**
   ```
   Settings → Secrets and variables → Actions → New repository secret
   
   DOCKER_USERNAME=your_username
   DOCKER_PASSWORD=your_access_token_or_pat
   
   Optional:
   DEPLOY_WEBHOOK_URL=https://your-server.com/webhook
   ```

3. **Workflow automatically triggered on:**
   - Push to `main` branch
   - Push to `develop` branch
   - Tag push: `git push origin v1.0.0`
   - Pull requests (build only, no push)

4. **Workflow runs:**
   - ✅ Build API & UI images (cached)
   - ✅ Push to Docker Hub
   - ✅ Add tags: `latest`, `v1.0.0`, `main`, `develop`, `sha-abc123`
   - ✅ Scan for vulnerabilities (Trivy)
   - ✅ Send webhook to production server (optional)

### Example CI/CD Usage

```bash
# 1. Commit code
git add -A
git commit -m "feat: add churn prediction endpoint"

# 2. Create release tag
git tag -a v1.0.1 -m "Release v1.0.1"
git push origin v1.0.1

# 3. GitHub Actions automatically:
#    - Builds images with tag v1.0.1
#    - Pushes to your_username/ridewise-api:v1.0.1
#    - Also tags as latest, v1.0.1, main, sha-...
#    - Runs security scans
#    - Deploys to production (if webhook configured)

# 4. On production server:
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

---

## Pull from Registry in docker-compose.prod.yml

```yaml
# docker-compose.prod.yml
services:
  api:
    image: your_username/ridewise-api:latest
    # or
    image: ghcr.io/your_username/ridewise-api:latest
    # or
    image: 123456789.dkr.ecr.us-east-1.amazonaws.com/ridewise-api:latest
```

---

## Troubleshooting

### Push fails: "denied: unauthorized"
```bash
# Re-authenticate
docker logout
docker login -u your_username
```

### Images not found after push
```bash
# Verify image was pushed
docker images | grep ridewise

# Check registry
# Docker Hub: https://hub.docker.com/r/your_username/ridewise-api
# GitHub: https://github.com/your_username/ridewise/pkgs
```

### GitHub Actions workflow fails
- Check workflow logs: GitHub → Actions → build-and-push → click run
- Verify secrets are set: Settings → Secrets
- Check docker-compose syntax: `docker-compose config`

---

## Best Practices

✅ Use semantic versioning for tags: `v1.0.0`, `v2.1.3-beta`
✅ Always tag with `latest` for production deployments
✅ Use branch name tags for dev/staging: `develop`, `staging`
✅ Include git SHA for immutability: `sha-a1b2c3d`
✅ Clean up old images: `docker image prune -a`
✅ Sign images (Docker Content Trust): `export DOCKER_CONTENT_TRUST=1`
✅ Keep images small: multi-stage builds, minimize layers
