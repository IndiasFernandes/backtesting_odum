# Docker Troubleshooting Guide

## Disk Space Issues

If you see errors like:
```
E: You don't have enough free space in /var/cache/apt/archives/.
```

### Solution 1: Clean Docker Disk Space

```bash
# Remove unused containers, networks, images, and build cache
docker system prune -a --volumes

# Or more aggressively (removes everything not currently running):
docker system prune -a --volumes --force
```

### Solution 2: Increase Docker Desktop Disk Space

1. Open Docker Desktop
2. Go to Settings → Resources → Advanced
3. Increase "Disk image size" (default is often 64GB)
4. Click "Apply & Restart"

### Solution 3: Clean Build Cache Only

```bash
# Remove build cache (saves ~10GB typically)
docker builder prune -a --force
```

### Solution 4: Remove Unused Images

```bash
# See what's using space
docker system df

# Remove specific unused images
docker image prune -a
```

## Build Issues

### Rebuild from Scratch

```bash
cd unified-cloud-services
docker compose build --no-cache
```

### Check Docker Disk Usage

```bash
docker system df
```

Expected output shows:
- Images: Should be reasonable (< 10GB for this project)
- Build Cache: Can be cleaned if > 5GB
- Volumes: Should be minimal

## Common Issues

### "Cannot connect to Docker daemon"

- Make sure Docker Desktop is running
- Check: `docker ps` should work

### "Permission denied" errors

- On macOS/Linux, you might need to add your user to docker group
- Or use `sudo` (not recommended)

### Build fails with network errors

```bash
# Restart Docker Desktop
# Or check your network connection
docker compose build --progress=plain
```

