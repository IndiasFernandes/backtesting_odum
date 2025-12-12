# Stable Branch Agent Guide

> **Use this guide for agents working on the stable `main` branch (backtest system only)**

## Current State

**Active Branch**: `main` (stable backtest system)  
**Feature Branch**: `feature/live-execution` (DO NOT TOUCH - separate development)  
**Remotes**: 
- `origin` → https://github.com/IndiasFernandes/backtesting_odum.git
- `ickenna` → https://github.com/IggyIkenna/execution-services.git

## What You're Working On

**Stable Backtest System** - Production-ready backtesting infrastructure:
- ✅ Backtest engine (`backend/core/engine.py`, `backend/backtest_engine.py`)
- ✅ Execution algorithms (`backend/execution_algorithms.py`)
- ✅ Data processing (`backend/data/`, `backend/data_converter.py`)
- ✅ Results handling (`backend/results.py`, `backend/results/`)
- ✅ API server (`backend/api/server.py`) - Port 8000
- ✅ Frontend UI (`frontend/`)
- ✅ Catalog management (`backend/catalog_manager.py`)

## What You CANNOT Touch

**Live Execution System** - This is on a separate branch:
- ❌ `backend/live/` directory (doesn't exist on main)
- ❌ `backend/api/live_server.py` (doesn't exist on main)
- ❌ Live execution Docker services (not in main's docker-compose.yml)
- ❌ Any files in `docs/live/` that mention "live execution"

**If you see references to live execution**, you're on the wrong branch!

## Before Starting Work

### 1. Verify You're on Main Branch

```bash
git checkout main
git pull origin main
git status
# Should show: "On branch main" and "Your branch is up to date"
```

### 2. Verify Backtest System Works

```bash
# Check API is running (if Docker is up)
curl http://localhost:8000/api/health
# Expected: {"status":"healthy","service":"Odum Trader Backtest API"}

# Or start it
docker-compose up -d backend frontend
curl http://localhost:8000/api/health
```

### 3. Understand Current Structure

**Key Directories:**
- `backend/core/` - Core backtest engine
- `backend/data/` - Data loading and conversion
- `backend/execution/` - Execution algorithms
- `backend/results/` - Results processing
- `backend/api/` - Backtest API server (port 8000)
- `backend/instruments/` - Instrument management
- `frontend/` - React frontend

**Key Files:**
- `backend/backtest_engine.py` - Main backtest orchestrator
- `backend/run_backtest.py` - CLI entry point
- `backend/api/server.py` - FastAPI server
- `docker-compose.yml` - Docker services (backtest only)

## What You Can Change

### ✅ Safe Changes (Backtest System Only)

1. **Backtest Engine Improvements**
   - Performance optimizations
   - Bug fixes
   - Feature additions
   - Code refactoring

2. **Execution Algorithms**
   - New algorithms
   - Algorithm improvements
   - Bug fixes

3. **Data Processing**
   - Data loader improvements
   - Converter enhancements
   - Catalog management updates

4. **API Endpoints**
   - New endpoints for backtest
   - Endpoint improvements
   - Bug fixes

5. **Frontend**
   - UI improvements
   - New features
   - Bug fixes

6. **Documentation**
   - Backtest documentation
   - API documentation
   - User guides

7. **Dependencies**
   - Backend dependencies (requirements.txt)
   - Frontend dependencies (package.json)
   - Docker configuration

### ❌ What NOT to Change

1. **Don't add live execution code**
   - No `backend/live/` directory
   - No live execution endpoints
   - No live execution models

2. **Don't modify docker-compose.yml for live services**
   - Keep only backtest services (backend, frontend)
   - Don't add postgres, live-backend, etc.

3. **Don't touch feature branch**
   - Never merge `feature/live-execution` into main
   - Never cherry-pick from feature branch
   - Never reference live execution code

## Development Workflow

### 1. Create Feature Branch from Main

```bash
# Start from clean main
git checkout main
git pull origin main

# Create feature branch
git checkout -b fix/backtest-performance  # Example: fix/backtest-bug
# or
git checkout -b feat/new-algorithm  # Example: feat/new-feature
```

### 2. Make Changes

- Follow existing code patterns
- Maintain backward compatibility
- Update tests if needed
- Update documentation

### 3. Test Your Changes

```bash
# Test backtest API
docker-compose up -d backend frontend
curl http://localhost:8000/api/health

# Test imports
python3 -c "from backend.core.engine import BacktestEngine; print('✓ Imports work')"

# Test specific functionality
# ... run your tests ...
```

### 4. Commit Changes

```bash
git add .
git commit -m "fix(backtest): description of change"
# or
git commit -m "feat(backtest): description of new feature"
# or
git commit -m "docs: update backtest documentation"
```

**Commit Message Format:**
- `fix(backtest): ...` - Bug fixes
- `feat(backtest): ...` - New features
- `perf(backtest): ...` - Performance improvements
- `docs: ...` - Documentation updates
- `refactor(backtest): ...` - Code refactoring

### 5. Push and Create PR

```bash
git push origin fix/backtest-performance

# Create Pull Request: fix/backtest-performance → main
# Requirements:
# - All tests pass
# - Backtest system still works
# - Documentation updated if needed
```

## Testing Checklist

After ANY changes, verify:

- [ ] Backtest API responds: `curl http://localhost:8000/api/health`
- [ ] Docker services start: `docker-compose up -d backend frontend`
- [ ] No import errors: `python3 -c "from backend.core.engine import BacktestEngine"`
- [ ] Existing functionality still works
- [ ] New functionality works as expected
- [ ] No references to live execution code

## Common Tasks

### Task 1: Fix a Bug

```bash
git checkout main
git pull origin main
git checkout -b fix/backtest-bug-name
# ... fix bug ...
git add .
git commit -m "fix(backtest): fix bug description"
git push origin fix/backtest-bug-name
# Create PR
```

### Task 2: Add a Feature

```bash
git checkout main
git pull origin main
git checkout -b feat/backtest-feature-name
# ... implement feature ...
git add .
git commit -m "feat(backtest): add feature description"
git push origin feat/backtest-feature-name
# Create PR
```

### Task 3: Update Documentation

```bash
git checkout main
git pull origin main
git checkout -b docs/update-backtest-docs
# ... update docs ...
git add .
git commit -m "docs: update backtest documentation"
git push origin docs/update-backtest-docs
# Create PR
```

### Task 4: Update Dependencies

```bash
git checkout main
git pull origin main
git checkout -b chore/update-dependencies
# ... update requirements.txt or package.json ...
git add .
git commit -m "chore: update dependencies"
git push origin chore/update-dependencies
# Create PR
```

## Emergency Procedures

### If You Accidentally Touch Live Execution Code

```bash
# Check what you changed
git status
git diff

# If you see backend/live/ or live execution references:
git checkout -- backend/live/  # Discard changes
# or
git restore backend/live/  # Discard changes

# Verify you're on main
git branch
# Should show: * main
```

### If Main Branch is Broken

```bash
# Check what's broken
docker-compose logs backend | tail -50

# Revert to last known good commit
git log --oneline -10  # Find good commit
git reset --hard <good-commit-hash>

# Or revert specific commit
git revert <bad-commit-hash>
```

### If You Need to Sync with Remote

```bash
# Fetch latest
git fetch origin

# Check differences
git log main..origin/main --oneline

# Merge remote changes
git pull origin main

# If conflicts, resolve them (never merge feature/live-execution)
```

## Important Reminders

1. **Always work on `main` branch** (or feature branches from main)
2. **Never merge `feature/live-execution`** into main
3. **Test backtest system** after every change
4. **Keep commits atomic** - one logical change per commit
5. **Write clear commit messages** - follow conventional commits
6. **Update documentation** if you change behavior
7. **Maintain backward compatibility** when possible

## Reference Documents

- `README.md` - Project overview and setup
- `docs/ARCHITECTURE.md` - System architecture (backtest focused)
- `BACKTEST_SPEC.md` - Backtest specification (if exists)
- `backend/README.md` - Backend structure guide

## Quick Reference

```bash
# Check current branch
git branch

# Switch to main
git checkout main
git pull origin main

# Create feature branch
git checkout -b fix/backtest-issue-name

# Test changes
docker-compose up -d backend frontend
curl http://localhost:8000/api/health

# Commit and push
git add .
git commit -m "fix(backtest): description"
git push origin fix/backtest-issue-name

# Verify you're not touching live execution
git diff main | grep -i "live"  # Should show nothing
```

---

**Remember**: You're working on the **stable backtest system**. Keep it stable, tested, and working!

*Last updated: December 12, 2025*

