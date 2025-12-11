# Agent Execution Guide

## Quick Answer: Can I Run All at the Same Time?

**Yes, with a recommended order:**

1. **Agent 3 first** (5-10 minutes) - Verify Docker setup works
2. **Then Agents 1, 2, and 5 in parallel** - They can all run simultaneously

## Execution Strategy

### Phase 1: Foundation (Run First)
**Agent 3: Docker & Infrastructure** ⏱️ ~10 minutes
- **Why first?** Ensures system is ready for other agents
- **What it does:** Verifies Docker Compose works, services start, volumes mount
- **Blocking?** Yes - other agents need working system
- **Can run in parallel?** No - must complete first

### Phase 2: Parallel Testing (Run Simultaneously)
Once Agent 3 passes, run these **in parallel**:

**Agent 1: Backtest Testing** ⏱️ ~30-45 minutes
- Tests backtest execution (CLI + API)
- Verifies calculations
- Tests trade execution
- **Independent:** Doesn't conflict with others

**Agent 2: UI Testing** ⏱️ ~20-30 minutes  
- Tests all UI components
- Tests CLI-frontend alignment
- Tests form validation
- **Independent:** Uses different endpoints/pages

**Agent 5: Performance Optimization** ⏱️ ~30-60 minutes
- Profiles performance
- Takes baseline measurements
- Identifies bottlenecks
- **Independent:** Can run while others test

### Phase 3: Skip
**Agent 4: FUSE Integration** - Skip (requires GCS bucket access)

## Recommended Execution Order

### Step 1: Start System
```bash
# Start Docker services
docker-compose up -d

# Wait for services to be healthy
sleep 10

# Verify services are running
docker-compose ps
curl http://localhost:8000/api/health
curl http://localhost:5173
```

### Step 2: Run Agent 3 (Foundation)
```bash
# Follow AGENT_3_DOCKER_INFRASTRUCTURE.md
# This should take ~10 minutes
# Verify all checks pass before proceeding
```

### Step 3: Run Agents 1, 2, and 5 in Parallel

**Option A: Separate Terminal Windows/Tabs**
```bash
# Terminal 1: Agent 1
# Follow AGENT_1_BACKTEST_TESTING.md

# Terminal 2: Agent 2  
# Follow AGENT_2_UI_TESTING.md

# Terminal 3: Agent 5
# Follow AGENT_5_PERFORMANCE_OPTIMIZATION.md
```

**Option B: Background Processes**
```bash
# Run Agent 1 in background
(bash -c 'source AGENT_1_BACKTEST_TESTING.md; execute_tests' > agent1.log 2>&1) &

# Run Agent 2 in background  
(bash -c 'source AGENT_2_UI_TESTING.md; execute_tests' > agent2.log 2>&1) &

# Run Agent 5 in background
(bash -c 'source AGENT_5_PERFORMANCE_OPTIMIZATION.md; execute_tests' > agent5.log 2>&1) &

# Wait for all to complete
wait

# Check results
tail -f agent1.log agent2.log agent5.log
```

## Resource Considerations

### Can They Conflict?

**No conflicts expected:**
- ✅ Agent 1: Uses API endpoints (different backtest runs)
- ✅ Agent 2: Uses UI pages (different user interactions)
- ✅ Agent 5: Profiles system (read-only monitoring)

**Potential considerations:**
- ⚠️ **API Load:** Agents 1 and 2 both hit API, but should be fine for testing
- ⚠️ **Backtest Runs:** Agent 1 runs multiple backtests - may take time
- ⚠️ **UI Interactions:** Agent 2 interacts with UI - may interfere if manual testing

### Recommended Approach

**For Production Testing:**
1. Run Agent 3 first (foundation)
2. Run Agents 1 and 2 in parallel (core functionality)
3. Run Agent 5 separately (performance profiling)

**For Quick Validation:**
1. Run Agent 3 (quick check)
2. Run Agent 1 OR Agent 2 (pick one based on priority)
3. Run Agent 5 later (if time permits)

## Monitoring Parallel Execution

### Check System Health
```bash
# Monitor Docker containers
watch -n 5 'docker-compose ps'

# Monitor API health
watch -n 5 'curl -s http://localhost:8000/api/health'

# Monitor resource usage
docker stats
```

### Check Agent Progress

**Agent 1 (Backtest Testing):**
```bash
# Check API results
curl http://localhost:8000/api/backtest/results | jq 'length'

# Check result files
ls -la backend/backtest_results/fast/ | wc -l
ls -la backend/backtest_results/report/ | wc -l
```

**Agent 2 (UI Testing):**
- Open browser: http://localhost:5173
- Check browser console for errors
- Verify UI is responsive

**Agent 5 (Performance):**
```bash
# Monitor resource usage
docker stats nautilus-backend nautilus-frontend

# Check API response times
time curl http://localhost:8000/api/health
```

## Troubleshooting Parallel Execution

### If Services Become Unresponsive
```bash
# Restart services
docker-compose restart

# Check logs
docker-compose logs --tail=100 backend
docker-compose logs --tail=100 frontend
```

### If Tests Conflict
- **Solution:** Run agents sequentially instead
- **Order:** Agent 3 → Agent 1 → Agent 2 → Agent 5

### If Resources Are Limited
- **Solution:** Run agents one at a time
- **Order:** Agent 3 → Agent 1 → Agent 2 → Agent 5

## Expected Timeline

### Sequential Execution (Safe)
- Agent 3: ~10 minutes
- Agent 1: ~30-45 minutes
- Agent 2: ~20-30 minutes
- Agent 5: ~30-60 minutes
- **Total:** ~90-145 minutes

### Parallel Execution (Recommended)
- Agent 3: ~10 minutes (must be first)
- Agents 1, 2, 5: ~45-60 minutes (run in parallel)
- **Total:** ~55-70 minutes

## Success Criteria

**All agents pass when:**
- ✅ Agent 3: Docker setup verified, services healthy
- ✅ Agent 1: All backtests execute, calculations correct, CLI-API aligned
- ✅ Agent 2: All UI components work, CLI-frontend aligned
- ✅ Agent 5: Performance profiled, optimizations identified

## Quick Start Commands

```bash
# 1. Start system
docker-compose up -d

# 2. Wait and verify
sleep 10
curl http://localhost:8000/api/health && echo "✓ Backend ready"
curl http://localhost:5173 && echo "✓ Frontend ready"

# 3. Run Agent 3 (foundation)
# Follow AGENT_3_DOCKER_INFRASTRUCTURE.md

# 4. Once Agent 3 passes, run Agents 1, 2, 5 in parallel
# Open 3 terminals and follow respective prompts
```

## Notes

- **Agent 4 (FUSE)** is skipped - implementation complete but requires GCS bucket
- **Agent 5** can run anytime after baseline, but parallel is fine
- **Agents 1 and 2** are independent - safe to run in parallel
- **Monitor resources** if running all 3 in parallel on limited hardware

