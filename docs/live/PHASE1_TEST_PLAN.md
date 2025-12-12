# Phase 1 Testing Plan

## Pre-Test Checklist

### 1. Verify Files Created
- [ ] All Python files exist
- [ ] All imports are correct
- [ ] No syntax errors

### 2. Verify Docker Compose
- [ ] Syntax is valid
- [ ] Profiles work correctly
- [ ] Backward compatibility maintained

### 3. Test Backtest System
- [ ] Backtest API still works
- [ ] No breaking changes

### 4. Test Live System (if Docker running)
- [ ] Live API can start
- [ ] Database connection works
- [ ] Migrations can run

---

## Test Commands

### File Verification
```bash
# Check all files exist
ls -la backend/live/
ls -la backend/api/live_server.py

# Check Python syntax
python3 -m py_compile backend/live/models.py
python3 -m py_compile backend/live/database.py
python3 -m py_compile backend/api/live_server.py
```

### Docker Compose Verification
```bash
# Validate syntax
docker-compose config

# Check services per profile
docker-compose config --services
docker-compose --profile live config --services
```

### Backtest System Test
```bash
# Verify backtest API
curl http://localhost:8000/api/health
```

### Live System Test (after Docker rebuild)
```bash
# Start live services
docker-compose --profile live up -d

# Check live API
curl http://localhost:8001/api/health

# Check database
docker-compose exec postgres psql -U user -d execution_db -c "\dt"

# Run migrations
docker-compose exec live-backend bash -c "cd backend/live && alembic upgrade head"
```

---

## Expected Results

1. All files should exist and have correct syntax
2. Docker Compose should validate without errors
3. Backtest API should still respond
4. Live API should start and respond on port 8001
5. Database migrations should run successfully

