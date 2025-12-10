# Docker Logs Guide

## Quick Commands

### View All Container Logs
```bash
docker-compose logs
```

### View Specific Service Logs
```bash
# Backend logs
docker-compose logs backend

# Frontend logs
docker-compose logs frontend

# All services
docker-compose logs backend frontend
```

### View Last N Lines
```bash
# Last 50 lines
docker-compose logs --tail=50 backend

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Follow Logs in Real-Time (Like `tail -f`)
```bash
# Follow backend logs
docker-compose logs -f backend

# Follow all logs
docker-compose logs -f

# Follow last 50 lines and continue
docker-compose logs -f --tail=50 backend
```

### View Logs Since Specific Time
```bash
# Logs from last 10 minutes
docker-compose logs --since 10m backend

# Logs from last hour
docker-compose logs --since 1h backend

# Logs since specific time
docker-compose logs --since 2024-01-01T00:00:00 backend
```

### View Logs Between Times
```bash
# Logs between two times
docker-compose logs --since 2024-01-01T00:00:00 --until 2024-01-01T12:00:00 backend
```

## Direct Docker Commands (Alternative)

### View Container Logs by Name
```bash
# Backend
docker logs nautilus-backend

# Frontend
docker logs nautilus-frontend

# Follow logs
docker logs -f nautilus-backend

# Last N lines
docker logs --tail=50 nautilus-backend

# Since specific time
docker logs --since 10m nautilus-backend
```

## Useful Combinations

### Watch Backend Logs While Testing
```bash
# Terminal 1: Follow backend logs
docker-compose logs -f --tail=100 backend

# Terminal 2: Run your tests/requests
# You'll see logs appear in real-time in Terminal 1
```

### Check for Errors
```bash
# Search for errors in logs
docker-compose logs backend | grep -i error

# Search for validation errors
docker-compose logs backend | grep -i "validation\|error\|failed"

# Search for specific status messages
docker-compose logs backend | grep "Status:"
```

### Export Logs to File
```bash
# Save logs to file
docker-compose logs backend > backend_logs.txt

# Save with timestamps
docker-compose logs -t backend > backend_logs_with_timestamps.txt

# Append to file
docker-compose logs --tail=100 backend >> backend_logs.txt
```

## Common Use Cases

### 1. Check if Backend Started Successfully
```bash
docker-compose logs backend | grep -i "started\|ready\|listening"
```

### 2. Monitor API Requests
```bash
docker-compose logs -f backend | grep "GET\|POST\|PUT\|DELETE"
```

### 3. Check for Validation Errors
```bash
docker-compose logs backend | grep -A 5 "VALIDATION\|ERROR\|mismatch"
```

### 4. View Recent Backtest Execution Logs
```bash
docker-compose logs --tail=200 backend | grep -A 10 "Status:"
```

### 5. Check Container Health
```bash
docker-compose ps
docker-compose logs backend | tail -20
```

## Tips

- Use `-f` flag to follow logs in real-time (like `tail -f`)
- Use `--tail=N` to limit output to last N lines
- Combine with `grep` to filter for specific messages
- Use `| less` or `| more` to paginate long logs
- Press `Ctrl+C` to stop following logs

## Example: Monitor Backtest Execution

```bash
# Terminal 1: Follow logs
docker-compose logs -f --tail=50 backend

# Terminal 2: Run backtest via UI or API
# Watch logs appear in Terminal 1 in real-time
```

