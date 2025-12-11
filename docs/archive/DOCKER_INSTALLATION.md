# Docker Installation Guide

## Prerequisites

### System Requirements
- **Docker**: Version 20.10 or later
- **Docker Compose**: Version 2.0 or later (or Docker Compose V2 plugin)
- **Disk Space**: At least 5GB free
- **Memory**: At least 4GB RAM recommended
- **Operating System**: macOS, Linux, or Windows (with WSL2)

### Verify Installation

```bash
# Check Docker version
docker --version

# Check Docker Compose version
docker compose version
# OR (older versions)
docker-compose --version
```

## Installation Steps

### 1. Clone the Repository

```bash
git clone <repository-url>
cd execution-services/data_downloads
```

### 2. Verify Directory Structure

Ensure the following directories exist:
- `data_downloads/` - Contains raw tick data and configs
- `backend/` - Backend Python code
- `frontend/` - Frontend React code
- `external/data_downloads/configs/` - Configuration files

### 3. Build Docker Images

```bash
# Build all services
docker compose build

# Or build individually
docker compose build backend
docker compose build frontend
```

### 4. Start Services

```bash
# Start all services in detached mode
docker compose up -d

# View logs
docker compose logs -f

# View logs for specific service
docker compose logs -f backend
docker compose logs -f frontend
```

### 5. Verify Services Are Running

```bash
# Check container status
docker compose ps

# Check health
curl http://localhost:8000/api/health
curl http://localhost:5173
```

### 6. Run Infrastructure Tests

```bash
# Run comprehensive test suite
./backend/scripts/test_docker_infrastructure.sh
```

## Service Ports

- **Backend API**: http://localhost:8000
- **Backend API Docs**: http://localhost:8000/docs
- **Frontend**: http://localhost:5173
- **Redis** (optional): localhost:6379

## Volume Mounts

### Read-Only Volumes
- `./data_downloads` → `/app/data_downloads` (raw tick data)
- `./external/data_downloads/configs` → `/app/external/data_downloads/configs` (config files)

### Read-Write Volumes
- `./backend/data/parquet` → `/app/backend/data/parquet` (Parquet catalog)
- `./backend/backtest_results` → `/app/backend/backtest_results` (backtest results)
- `./frontend/public/tickdata` → `/app/frontend/public/tickdata` (tick exports)

## Environment Variables

### Backend Environment Variables

Set in `docker-compose.yml`:
- `UNIFIED_CLOUD_LOCAL_PATH=/app/data_downloads`
- `UNIFIED_CLOUD_SERVICES_USE_PARQUET=true`
- `UNIFIED_CLOUD_SERVICES_USE_DIRECT_GCS=false`
- `DATA_CATALOG_PATH=/app/backend/data/parquet`
- `PYTHONPATH=/app`

### Frontend Environment Variables

- `VITE_API_URL=http://localhost:8000`

### GCS FUSE Configuration (Optional)

- `USE_GCS_FUSE=false` (set to `true` to enable)
- `GCS_FUSE_BUCKET=<your-bucket-name>`
- `GCS_SERVICE_ACCOUNT_KEY=<base64-encoded-key>`

## Common Operations

### Start Services
```bash
docker compose up -d
```

### Stop Services
```bash
docker compose stop
```

### Restart Services
```bash
docker compose restart
```

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f frontend
```

### Rebuild After Code Changes
```bash
docker compose up -d --build
```

### Stop and Remove Containers
```bash
docker compose down
```

### Stop and Remove Containers + Volumes
```bash
docker compose down -v
```

### Execute Commands in Containers
```bash
# Backend shell
docker compose exec backend bash

# Frontend shell
docker compose exec frontend sh

# Run Python script in backend
docker compose exec backend python backend/run_backtest.py --help
```

## Health Checks

All services have health checks configured:

- **Backend**: Checks `/api/health` endpoint every 30 seconds
- **Frontend**: Checks HTTP response on port 5173 every 30 seconds
- **Redis**: Checks `redis-cli ping` every 30 seconds (if enabled)

View health status:
```bash
docker compose ps
docker inspect --format='{{.State.Health.Status}}' nautilus-backend
docker inspect --format='{{.State.Health.Status}}' nautilus-frontend
```

## Troubleshooting

### Port Conflicts

If ports 8000 or 5173 are already in use:

1. Find the process using the port:
```bash
# macOS/Linux
lsof -i :8000
lsof -i :5173

# Or use netstat
netstat -an | grep 8000
```

2. Stop the conflicting service or change ports in `docker-compose.yml`

### Build Failures

If builds fail:

1. Check Docker has enough resources:
```bash
docker system df
docker system prune  # Clean up unused resources
```

2. Check logs for specific errors:
```bash
docker compose build --no-cache backend
docker compose build --no-cache frontend
```

### Container Won't Start

1. Check logs:
```bash
docker compose logs backend
docker compose logs frontend
```

2. Verify volumes exist:
```bash
ls -la data_downloads/
ls -la backend/data/parquet/
ls -la backend/backtest_results/
```

3. Check permissions:
```bash
ls -la backend/scripts/start.sh
chmod +x backend/scripts/start.sh
```

### Health Checks Failing

1. Wait for services to fully start (health checks have a start period)
2. Check if services are actually running:
```bash
docker compose exec backend curl http://localhost:8000/api/health
docker compose exec frontend wget -O- http://localhost:5173
```

3. Check service logs for errors

### Volume Mount Issues

1. Verify paths exist on host:
```bash
test -d data_downloads && echo "OK" || echo "Missing"
test -d backend/data/parquet && echo "OK" || echo "Missing"
```

2. Check volume mounts in container:
```bash
docker compose exec backend ls -la /app/data_downloads
docker compose exec backend ls -la /app/backend/data/parquet
```

3. Verify read-only volumes are actually read-only:
```bash
docker compose exec backend touch /app/data_downloads/test.txt
# Should fail if read-only
```

## Production Considerations

### Security

1. **Non-root user**: Consider running containers as non-root users
2. **Secrets**: Use Docker secrets or environment files for sensitive data
3. **Network**: Use internal networks, limit exposed ports
4. **Images**: Use minimal base images, scan for vulnerabilities

### Performance

1. **Resource limits**: Set memory and CPU limits in `docker-compose.yml`
2. **Logging**: Configure log rotation to prevent disk fill
3. **Caching**: Use Docker layer caching for faster builds

### Monitoring

1. **Health checks**: Already configured, monitor health status
2. **Logs**: Set up log aggregation (e.g., ELK stack)
3. **Metrics**: Consider adding Prometheus metrics endpoints

## Next Steps

After installation:
1. Run the test suite: `./backend/scripts/test_docker_infrastructure.sh`
2. Verify API endpoints: Visit http://localhost:8000/docs
3. Access frontend: Visit http://localhost:5173
4. Review architecture: See `ARCHITECTURE.md`

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Architecture Documentation](./ARCHITECTURE.md)
- [Troubleshooting Guide](./DOCKER_TROUBLESHOOTING.md)

