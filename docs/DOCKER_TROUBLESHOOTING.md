# Docker Troubleshooting Guide

## Common Issues and Solutions

### Issue: Port Already in Use

**Symptoms:**
```
Error: bind: address already in use
```

**Solutions:**

1. Find and stop the conflicting process:
```bash
# Find process using port 8000
lsof -i :8000
# Kill the process (replace PID)
kill -9 <PID>

# Or for port 5173
lsof -i :5173
kill -9 <PID>
```

2. Change ports in `docker-compose.yml`:
```yaml
ports:
  - "8001:8000"  # Use 8001 instead of 8000
```

### Issue: Container Exits Immediately

**Symptoms:**
- Container starts but exits with code 0 or 1
- `docker compose ps` shows "Exited"

**Diagnosis:**
```bash
# Check logs
docker compose logs backend
docker compose logs frontend

# Check exit code
docker compose ps
```

**Common Causes:**

1. **Startup script fails:**
   - Check `backend/scripts/start.sh` exists and is executable
   - Verify Python dependencies are installed

2. **Missing dependencies:**
   - Rebuild with `--no-cache`:
   ```bash
   docker compose build --no-cache backend
   ```

3. **Environment variable issues:**
   - Verify all required env vars are set in `docker-compose.yml`

### Issue: Health Checks Failing

**Symptoms:**
- Health status shows "unhealthy"
- Services appear to be running but health checks fail

**Diagnosis:**
```bash
# Check health status
docker inspect --format='{{.State.Health.Status}}' nautilus-backend

# Check health check logs
docker inspect --format='{{json .State.Health}}' nautilus-backend | jq
```

**Solutions:**

1. **Increase start period:**
   - Services may need more time to start
   - Already configured with `start_period: 10s` for backend

2. **Verify health check endpoint:**
   ```bash
   # Test manually
   docker compose exec backend curl http://localhost:8000/api/health
   ```

3. **Check if service is actually running:**
   ```bash
   docker compose exec backend ps aux
   docker compose exec backend netstat -tlnp
   ```

### Issue: Volume Mounts Not Working

**Symptoms:**
- Files not visible in container
- Permission denied errors
- Data not persisting

**Diagnosis:**
```bash
# Check if volumes are mounted
docker compose exec backend ls -la /app/data_downloads
docker compose exec backend mount | grep data_downloads

# Check host paths exist
ls -la data_downloads/
ls -la backend/data/parquet/
```

**Solutions:**

1. **Verify paths exist on host:**
   ```bash
   mkdir -p data_downloads/raw_tick_data
   mkdir -p backend/data/parquet
   mkdir -p backend/backtest_results
   ```

2. **Check permissions:**
   ```bash
   # Ensure directories are readable
   chmod -R 755 data_downloads/
   chmod -R 755 backend/data/parquet/
   ```

3. **Verify volume syntax in docker-compose.yml:**
   ```yaml
   volumes:
     - ./data_downloads:/app/data_downloads:ro  # Correct
     # NOT: - data_downloads:/app/data_downloads  # Wrong (named volume)
   ```

### Issue: Build Failures

**Symptoms:**
- `docker compose build` fails
- Dependency installation errors

**Common Causes:**

1. **Network issues:**
   - Check internet connection
   - Verify Docker can reach registries

2. **Out of disk space:**
   ```bash
   docker system df
   docker system prune  # Clean up
   ```

3. **Dockerfile syntax errors:**
   - Check Dockerfile syntax
   - Verify COPY paths are correct

**Solutions:**

1. **Clean build:**
   ```bash
   docker compose build --no-cache
   ```

2. **Build individually:**
   ```bash
   docker compose build backend
   docker compose build frontend
   ```

3. **Check Dockerfile:**
   ```bash
   docker build -t test-backend -f backend/Dockerfile .
   ```

### Issue: Frontend Can't Reach Backend

**Symptoms:**
- Frontend loads but API calls fail
- CORS errors in browser console

**Diagnosis:**
```bash
# Test from frontend container
docker compose exec frontend wget -O- http://backend:8000/api/health

# Check network
docker network inspect data_downloads_backtest-network
```

**Solutions:**

1. **Verify services are on same network:**
   - Check `docker-compose.yml` - both should use `backtest-network`

2. **Check VITE_API_URL:**
   - Should be `http://localhost:8000` for browser access
   - Internal container communication uses `http://backend:8000`

3. **Verify CORS is configured:**
   - Check `backend/api/server.py` has CORS middleware

### Issue: Permission Denied Errors

**Symptoms:**
- `Permission denied` when accessing files
- Can't write to volumes

**Solutions:**

1. **Check file permissions:**
   ```bash
   ls -la backend/scripts/start.sh
   chmod +x backend/scripts/start.sh
   ```

2. **Check volume permissions:**
   ```bash
   # Ensure writable volumes have correct permissions
   chmod -R 777 backend/data/parquet/  # Development only!
   ```

3. **Run as correct user:**
   - Containers run as root by default
   - Consider adding non-root user to Dockerfile

### Issue: Out of Memory

**Symptoms:**
- Containers killed unexpectedly
- `OOMKilled` in `docker compose ps`

**Solutions:**

1. **Increase Docker memory limit:**
   - Docker Desktop: Settings → Resources → Memory
   - Increase to at least 4GB

2. **Add memory limits to docker-compose.yml:**
   ```yaml
   services:
     backend:
       deploy:
         resources:
           limits:
             memory: 2G
   ```

3. **Monitor memory usage:**
   ```bash
   docker stats
   ```

### Issue: Slow Performance

**Symptoms:**
- Containers are slow to start
- API responses are slow

**Diagnosis:**
```bash
# Check resource usage
docker stats

# Check disk I/O
docker compose exec backend iostat
```

**Solutions:**

1. **Allocate more resources to Docker**
2. **Use SSD for volumes** (if possible)
3. **Enable Docker BuildKit:**
   ```bash
   export DOCKER_BUILDKIT=1
   docker compose build
   ```

### Issue: GCS FUSE Mount Fails

**Symptoms:**
- FUSE mount errors in logs
- Data not accessible

**Solutions:**

1. **Enable privileged mode:**
   ```yaml
   services:
     backend:
       privileged: true  # Required for FUSE
   ```

2. **Verify GCS credentials:**
   ```bash
   # Check environment variables
   docker compose exec backend printenv | grep GCS
   ```

3. **Check mount script:**
   ```bash
   docker compose exec backend bash /app/backend/scripts/mount_gcs.sh
   ```

### Issue: Logs Too Verbose

**Symptoms:**
- Logs fill up disk
- Hard to find important messages

**Solutions:**

1. **Configure log rotation in docker-compose.yml:**
   ```yaml
   services:
     backend:
       logging:
         driver: "json-file"
         options:
           max-size: "10m"
           max-file: "3"
   ```

2. **Clean up old logs:**
   ```bash
   docker compose logs --tail=100  # View only recent logs
   ```

## Diagnostic Commands

### General Diagnostics
```bash
# Container status
docker compose ps

# Resource usage
docker stats

# Disk usage
docker system df

# Network inspection
docker network inspect data_downloads_backtest-network
```

### Service-Specific Diagnostics
```bash
# Backend
docker compose exec backend ps aux
docker compose exec backend env
docker compose exec backend python --version

# Frontend
docker compose exec frontend ps aux
docker compose exec frontend env
docker compose exec frontend node --version
```

### Volume Diagnostics
```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect <volume-name>

# Check mount points
docker compose exec backend mount
```

## Getting Help

1. **Check logs first:**
   ```bash
   docker compose logs > docker-logs.txt
   ```

2. **Run test suite:**
   ```bash
   ./backend/scripts/test_docker_infrastructure.sh
   ```

3. **Collect system information:**
   ```bash
   docker --version
   docker compose version
   docker system info
   ```

4. **Review documentation:**
   - `ARCHITECTURE.md` - System architecture
   - `DOCKER_INSTALLATION.md` - Installation guide
   - `README.md` - General documentation

## Prevention Tips

1. **Regular maintenance:**
   ```bash
   # Clean up unused resources
   docker system prune -a

   # Remove old images
   docker image prune -a
   ```

2. **Monitor resources:**
   - Set up alerts for disk space
   - Monitor container health

3. **Keep updated:**
   - Update Docker regularly
   - Keep base images updated

4. **Use health checks:**
   - Already configured
   - Monitor health status regularly

