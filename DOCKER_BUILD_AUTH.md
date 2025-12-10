# Docker Build Authentication Guide

## Problem
The Docker build fails when installing `unified-cloud-services` from a private GitHub repository because authentication is required.

## Quick Start (Easiest Method)

**Option 1: Use the helper script**
```bash
# 1. Get a GitHub token (see instructions below)
# 2. Set it and run the helper script
export GITHUB_TOKEN=your_token_here
./build.sh
```

**Option 2: Direct docker-compose**
```bash
export GITHUB_TOKEN=your_token_here
docker-compose build backend
docker-compose up -d
```

## Getting a GitHub Token

1. Go to: https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Name it: "Docker Build"
4. Select scope: **`repo`** (Full control of private repositories)
5. Click "Generate token"
6. **Copy the token immediately** (you won't see it again!)

## Solutions

### Solution 1: GitHub Personal Access Token (Recommended for Development)

**Step 1: Create a GitHub Personal Access Token**
1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate a new token with `repo` scope
3. Copy the token

**Step 2: Build with Token**

**Option A: Using docker-compose**
```bash
# Set token as environment variable
export GITHUB_TOKEN=your_github_token_here

# Build
docker-compose build backend

# Or build and start
docker-compose up -d --build
```

**Option B: Using docker build directly**
```bash
docker build \
  --build-arg GITHUB_TOKEN=your_github_token_here \
  -f backend/Dockerfile \
  -t data_downloads-backend \
  .
```

**Option C: Using .env file (not recommended for tokens)**
Create `.env` file (add to `.gitignore`):
```
GITHUB_TOKEN=your_github_token_here
```
Then run:
```bash
docker-compose build backend
```

### Solution 2: SSH Keys (Recommended for CI/CD)

**Step 1: Generate SSH Key (if needed)**
```bash
ssh-keygen -t ed25519 -C "docker-build" -f ~/.ssh/docker_build_key
```

**Step 2: Add SSH Key to GitHub**
1. Copy public key: `cat ~/.ssh/docker_build_key.pub`
2. Add to GitHub → Settings → SSH and GPG keys → New SSH key

**Step 3: Update requirements.txt**
Change line 7 from:
```
git+https://github.com/IggyIkenna/unified-cloud-services.git
```
to:
```
git+ssh://git@github.com/IggyIkenna/unified-cloud-services.git
```

**Step 4: Update Dockerfile**
Add SSH key mounting (requires BuildKit):
```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.11-slim

# ... existing code ...

# Mount SSH key for private repo access
RUN --mount=type=ssh \
    pip install --no-cache-dir -r requirements.txt
```

**Step 5: Build with SSH**
```bash
# Enable BuildKit
export DOCKER_BUILDKIT=1

# Build with SSH agent
docker build \
  --ssh default \
  -f backend/Dockerfile \
  -t data_downloads-backend \
  .
```

### Solution 3: Local Package Copy (For Offline/Controlled Environments)

**Step 1: Clone repository locally**
```bash
git clone git@github.com:IggyIkenna/unified-cloud-services.git /tmp/unified-cloud-services
```

**Step 2: Update Dockerfile**
Add before pip install:
```dockerfile
# Copy local package
COPY unified-cloud-services /tmp/unified-cloud-services
RUN pip install --no-cache-dir /tmp/unified-cloud-services
```

**Step 3: Update requirements.txt**
Remove or comment out:
```
# git+https://github.com/IggyIkenna/unified-cloud-services.git
```

### Solution 4: Docker BuildKit Secrets (Most Secure)

**Step 1: Create secret file**
```bash
echo "your_github_token_here" > .github_token
```

**Step 2: Update Dockerfile**
```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.11-slim

# ... existing code ...

RUN --mount=type=secret,id=github_token \
    GITHUB_TOKEN=$(cat /run/secrets/github_token) && \
    sed -i "s|git+https://github.com/IggyIkenna/unified-cloud-services.git|git+https://${GITHUB_TOKEN}@github.com/IggyIkenna/unified-cloud-services.git|g" /app/requirements.txt && \
    pip install --no-cache-dir -r requirements.txt
```

**Step 3: Build with secret**
```bash
export DOCKER_BUILDKIT=1
docker build \
  --secret id=github_token,src=.github_token \
  -f backend/Dockerfile \
  -t data_downloads-backend \
  .
```

## Recommended Approach

- **Development**: Use Solution 1 (GitHub Token via environment variable)
- **CI/CD**: Use Solution 2 (SSH Keys) or Solution 4 (BuildKit Secrets)
- **Offline/Controlled**: Use Solution 3 (Local Copy)

## Security Notes

1. **Never commit tokens or secrets to git**
2. **Use environment variables or secret management tools**
3. **Rotate tokens regularly**
4. **Use minimal required scopes for tokens**
5. **Consider using GitHub App tokens instead of personal tokens for CI/CD**

## Troubleshooting

**Error: "could not read Username"**
- Token not set or invalid
- Check token has `repo` scope
- Verify token hasn't expired

**Error: "Permission denied (publickey)"**
- SSH key not added to GitHub
- SSH agent not running
- Wrong SSH key used

**Error: "Repository not found"**
- Token doesn't have access to private repo
- Repository name/path incorrect
- Token expired or revoked

