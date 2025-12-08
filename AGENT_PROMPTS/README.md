# Agent Prompts

This directory contains focused prompts for each of the 5 agents defined for testing and completing the backtesting system.

## Agent Overview

### ✅ Agent 1: Backtest Testing Agent
**File**: `AGENT_1_BACKTEST_TESTING.md`  
**Focus**: Test backtest execution, verify trades, validate calculations  
**Can run in parallel**: Yes

### ✅ Agent 2: UI Testing Agent
**File**: `AGENT_2_UI_TESTING.md`  
**Focus**: Test all UI components, buttons, functionalities  
**Can run in parallel**: Yes

### ✅ Agent 3: Docker & Infrastructure Agent
**File**: `AGENT_3_DOCKER_INFRASTRUCTURE.md`  
**Focus**: Ensure Docker setup works easily, containers are production-ready  
**Can run in parallel**: Yes

### ⏭️ Agent 4: FUSE Integration Agent
**File**: `AGENT_4_FUSE_INTEGRATION.md`  
**Focus**: GCS FUSE integration (SKIP - not tested)  
**Status**: Implementation complete, testing requires GCS bucket access

### ✅ Agent 5: Performance & Optimization Agent
**File**: `AGENT_5_PERFORMANCE_OPTIMIZATION.md`  
**Focus**: Profile performance, identify bottlenecks, implement optimizations  
**Can run in parallel**: Yes (after baseline measurements)

## Quick Start

1. **Start the system:**
   ```bash
   docker-compose up -d
   ```

2. **Verify services are running:**
   ```bash
   docker-compose ps
   curl http://localhost:8000/api/health
   curl http://localhost:5173
   ```

3. **Execution order:**
   - **First:** Agent 3 (Docker Infrastructure) - ~10 min
   - **Then in parallel:** Agents 1, 2, and 5 - ~45-60 min
   
   See `EXECUTION_GUIDE.md` for detailed parallel execution instructions.

## Data Location

Data files are provided in:
- `data_downloads/raw_tick_data/by_date/day-YYYY-MM-DD/` (contains Parquet files)
- `data_downloads/configs/*.json` (contains JSON configuration files)

**Note**: These are mounted at `/app/data_downloads` in the Docker container. The API scans this location to discover datasets and configs.

## Agent Execution Order

**Phase 1 (Foundation - Run First):**
- Agent 3: Docker Infrastructure (~10 min) - **Must complete first**

**Phase 2 (Parallel - Run Simultaneously):**
- Agent 1: Backtest Testing (~30-45 min)
- Agent 2: UI Testing (~20-30 min)
- Agent 5: Performance Optimization (~30-60 min)

**Phase 3 (Future):**
- Agent 4: FUSE Integration (skip - requires GCS bucket)

**See `EXECUTION_GUIDE.md` for detailed execution strategy and parallel running instructions.**

## Notes

- All agents can run in parallel except Agent 5 (should run after baseline)
- Agent 4 is skipped (FUSE testing requires GCS bucket)
- Each prompt includes specific test commands and success criteria
- Deliverables are clearly defined for each agent

