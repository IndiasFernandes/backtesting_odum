# File Organization Strategy: Live vs Backtest Separation

> Clear separation of live and backtest code while maintaining shared components

## Overview

Even though live and backtest run as **separate services**, the codebase maintains clear separation at the file level. This ensures:
- ✅ Clear boundaries between live and backtest code
- ✅ Easy to understand what code belongs where
- ✅ Shared components clearly identified
- ✅ Easy to maintain and extend
- ✅ No confusion about which code runs where

**Related Documents**:
- `ROADMAP.md` - Complete implementation roadmap
- `IMPLEMENTATION_GUIDE.md` - Detailed implementation instructions
- `DEVELOPMENT_PROMPT.md` - Quick reference prompt

---

## Directory Structure

### Current Structure (December 2025)

**Note**: Currently, backtest code is in `backend/core/engine.py`. The structure below shows the **current state** and the **target state** after reorganization.

```
backend/
├── core/                    # CURRENT: Core components (mixed)
│   ├── __init__.py
│   ├── engine.py           # CURRENT: BacktestEngine (backtest-specific)
│   └── node_builder.py     # Shared node configuration builder
│
├── backtest_engine.py       # CURRENT: Legacy redirect (imports from core.engine)
│
├── backtest/                # TARGET: Backtest-specific components (to be created)
│   ├── __init__.py         # NEW
│   └── engine.py           # TARGET: Move BacktestEngine here
│
├── live/                    # TARGET: Live-specific components (to be created)
│   ├── __init__.py         # NEW
│   ├── engine.py           # NEW: LiveEngine / LiveExecutionOrchestrator
│   ├── trading_node.py     # NEW: TradingNode wrapper
│   ├── orchestrator.py     # NEW: Execution Orchestrator
│   ├── oms.py              # NEW: Unified OMS
│   ├── positions.py        # NEW: Position Tracker
│   ├── risk.py             # NEW: Risk Engine
│   ├── router.py           # NEW: Smart Router (live-specific)
│   └── adapters/           # NEW: External SDK adapters
│       ├── __init__.py
│       ├── base.py
│       ├── deribit.py
│       └── registry.py
│
├── execution/               # CURRENT: Shared execution components
│   ├── __init__.py
│   ├── algorithms.py       # TWAP, VWAP, Iceberg (shared)
│   └── router.py           # Base router logic (shared)
│
├── strategies/              # CURRENT: Shared strategy components
│   ├── __init__.py
│   ├── base.py             # Base strategy classes
│   └── evaluator.py        # Strategy evaluator
│
├── data/                    # CURRENT: Shared data management
│   ├── __init__.py
│   ├── catalog.py          # Catalog manager
│   ├── config_builder.py   # Data config builder
│   ├── converter.py        # Data converter
│   ├── loader.py           # UCS data loader
│   └── validator.py        # Data validator
│
├── instruments/            # CURRENT: Shared instrument management
│   ├── __init__.py
│   ├── factory.py          # Instrument factory
│   ├── registry.py         # Instrument registry
│   ├── utils.py           # Instrument utilities
│   └── custom_instruments.py
│
├── config/                  # CURRENT: Shared configuration
│   ├── __init__.py
│   └── loader.py           # Config loader
│
├── results/                 # CURRENT: Shared result processing
│   ├── __init__.py
│   ├── serializer.py       # Result serializer
│   ├── extractor.py         # Result extractor
│   ├── timeline.py         # Timeline builder
│   └── position_manager.py # Position manager
│
├── api/                     # CURRENT: API endpoints
│   ├── __init__.py
│   ├── server.py           # CURRENT: Backtest API (port 8000)
│   ├── algorithm_manager.py # Algorithm management API
│   ├── data_checker.py     # Data availability checker
│   └── live_server.py      # TARGET: Live API (port 8001) - NEW
│
├── utils/                   # CURRENT: Shared utilities
│   ├── __init__.py
│   ├── paths.py
│   ├── validation.py
│   └── log_capture.py
│
├── catalog_manager.py       # CURRENT: Catalog manager (backtest-specific)
├── run_backtest.py          # CURRENT: CLI entrypoint
└── results.py               # CURRENT: Legacy results module
```

### Current vs Target Structure

| Component | Current Location | Target Location | Status |
|-----------|-----------------|-----------------|--------|
| BacktestEngine | `backend/core/engine.py` | `backend/backtest/engine.py` | ⏳ To migrate |
| Backtest API | `backend/api/server.py` | `backend/api/server.py` | ✅ Current |
| Live API | ❌ Not exists | `backend/api/live_server.py` | ⏳ To create |
| Live Components | ❌ Not exists | `backend/live/*` | ⏳ To create |
| Shared Components | ✅ `backend/execution/`, `backend/data/`, etc. | ✅ Same | ✅ Current |

---

## Separation Principles

### 1. Clear Directory Boundaries

**Backtest-Specific** (`backend/backtest/`):
- ✅ All code that **only** runs in backtest service
- ✅ Uses `BacktestNode`
- ✅ Historical data replay
- ✅ Simulated execution

**Live-Specific** (`backend/live/`):
- ✅ All code that **only** runs in live service
- ✅ Uses `TradingNode`
- ✅ Real-time market data
- ✅ Live order execution
- ✅ External adapters

**Shared** (`backend/execution/`, `backend/data/`, etc.):
- ✅ Code used by **both** backtest and live
- ✅ Execution algorithms (TWAP, VWAP, Iceberg)
- ✅ Data loading/conversion
- ✅ Instrument management
- ✅ Configuration loading
- ✅ Result processing

---

## Component Mapping

### Backtest Components

| Component | Current Location | Target Location | Purpose | Shared? |
|-----------|-----------------|-----------------|---------|---------|
| BacktestEngine | `backend/core/engine.py` | `backend/backtest/engine.py` | Main backtest orchestrator | ❌ No |
| BacktestNode Config | `backend/core/node_builder.py` | `backend/core/node_builder.py` | Node configuration | ✅ Yes |
| Backtest Strategy | `backend/strategies/base.py` | `backend/strategies/base.py` | Trade-driven strategy | ✅ Yes |
| Backtest API | `backend/api/server.py` | `backend/api/server.py` | FastAPI endpoints (port 8000) | ❌ No |
| Catalog Manager | `backend/catalog_manager.py` | `backend/data/catalog.py` (or keep) | Catalog management | ⚠️ Backtest-specific |
| Data Loading | `backend/data/loader.py` | `backend/data/loader.py` | UCS data loader | ✅ Yes |
| Result Upload | `backend/results/serializer.py` | `backend/results/serializer.py` | GCS upload | ✅ Yes |
| CLI Entrypoint | `backend/run_backtest.py` | `backend/run_backtest.py` | CLI runner | ❌ No |

### Live Components

| Component | Location | Purpose | Shared? |
|-----------|----------|---------|---------|
| LiveExecutionOrchestrator | `backend/live/orchestrator.py` | Main live orchestrator | ❌ No |
| LiveEngine | `backend/live/engine.py` | Live engine wrapper | ❌ No |
| TradingNode Wrapper | `backend/live/trading_node.py` | TradingNode integration | ❌ No |
| Unified OMS | `backend/live/oms.py` | Order management | ❌ No |
| Position Tracker | `backend/live/positions.py` | Position aggregation | ❌ No |
| Risk Engine | `backend/live/risk.py` | Pre-trade risk checks | ❌ No |
| Smart Router (Live) | `backend/live/router.py` | Live-specific routing | ❌ No |
| External Adapters | `backend/live/adapters/` | Deribit, IB adapters | ❌ No |
| Live API | `backend/api/live_server.py` | FastAPI endpoints (port 8001) | ❌ No |

### Shared Components

| Component | Location | Used By | Notes |
|-----------|----------|---------|-------|
| Execution Algorithms | `backend/execution/algorithms.py` | Both | TWAP, VWAP, Iceberg |
| Base Router Logic | `backend/execution/router.py` | Both | Base routing logic |
| Instrument Factory | `backend/instruments/factory.py` | Both | Instrument creation |
| Config Loader | `backend/config/loader.py` | Both | JSON config loading |
| UCS Data Loader | `backend/data/loader.py` | Both | GCS data access |
| Result Serializer | `backend/results/serializer.py` | Both | Result formatting |
| Node Builder | `backend/core/node_builder.py` | Both | Node configuration |

---

## Import Patterns

### Backtest Service Imports

**Current Imports** (as of December 2025):
```python
# backend/api/server.py (Backtest API)
from backend.core.engine import BacktestEngine  # CURRENT: core.engine
from backend.data.catalog import CatalogManager
from backend.config.loader import ConfigLoader
from backend.execution.algorithms import TWAPExecAlgorithm  # Shared
from backend.results.serializer import ResultSerializer     # Shared
```

**Target Imports** (after reorganization):
```python
# backend/api/server.py (Backtest API)
from backend.backtest.engine import BacktestEngine  # TARGET: backtest.engine
from backend.data.catalog import CatalogManager
from backend.config.loader import ConfigLoader
from backend.execution.algorithms import TWAPExecAlgorithm  # Shared
from backend.results.serializer import ResultSerializer     # Shared
```

### Live Service Imports

```python
# backend/api/live_server.py (Live API)
from backend.live.orchestrator import LiveExecutionOrchestrator
from backend.live.trading_node import LiveTradingNode
from backend.live.oms import UnifiedOrderManager
from backend.live.positions import UnifiedPositionTracker
from backend.live.risk import PreTradeRiskEngine
from backend.execution.algorithms import TWAPExecAlgorithm  # Shared
from backend.instruments.factory import InstrumentFactory    # Shared
```

### Shared Component Imports

```python
# backend/execution/algorithms.py (Used by both)
# No imports from backtest/ or live/ directories
# Only imports from shared modules (instruments, config, etc.)
```

---

## Migration Strategy

### Current State (December 2025)

```
backend/
├── core/
│   ├── engine.py           # CURRENT: BacktestEngine
│   └── node_builder.py     # Shared node builder
├── backtest_engine.py       # Legacy redirect (imports core.engine)
├── catalog_manager.py       # Backtest-specific catalog manager
├── run_backtest.py          # CLI entrypoint
├── results.py               # Legacy results module
├── execution/
│   ├── algorithms.py       # Shared algorithms
│   └── router.py           # Shared router logic
├── data/
│   ├── catalog.py          # Catalog manager
│   ├── loader.py          # UCS data loader
│   ├── converter.py       # Data converter
│   └── validator.py       # Data validator
├── instruments/
│   ├── factory.py          # Instrument factory
│   └── utils.py           # Instrument utilities
├── config/
│   └── loader.py          # Config loader
├── results/
│   ├── serializer.py      # Result serializer
│   └── extractor.py       # Result extractor
├── strategies/
│   └── base.py            # Strategy base classes
├── api/
│   └── server.py          # CURRENT: Backtest API (port 8000)
└── utils/                 # Shared utilities
```

### Target State (After Reorganization)

```
backend/
├── backtest/               # NEW: Backtest-specific
│   ├── __init__.py
│   └── engine.py           # Move from core/engine.py
│
├── live/                   # NEW: Live-specific
│   ├── __init__.py
│   ├── engine.py           # NEW: LiveEngine
│   ├── orchestrator.py     # NEW: LiveExecutionOrchestrator
│   ├── trading_node.py    # NEW: TradingNode wrapper
│   ├── oms.py             # NEW: UnifiedOrderManager
│   ├── positions.py       # NEW: UnifiedPositionTracker
│   ├── risk.py            # NEW: PreTradeRiskEngine
│   ├── router.py          # NEW: Live-specific router
│   └── adapters/          # NEW: External adapters
│
├── core/                   # Keep: Shared core
│   ├── __init__.py
│   └── node_builder.py    # Shared node builder
│
├── execution/              # Keep: Shared execution
│   ├── algorithms.py       # Shared algorithms
│   └── router.py          # Base router logic
│
├── data/                   # Keep: Shared data
│   ├── catalog.py
│   ├── loader.py
│   └── ...
│
├── api/                    # Keep: API endpoints
│   ├── server.py          # Backtest API (port 8000)
│   └── live_server.py     # NEW: Live API (port 8001)
│
└── ... (other shared modules unchanged)
```

### Migration Steps

**Phase 1: Create Directory Structure** (Before Live Development)
```bash
# Create backtest directory (for future organization)
mkdir -p backend/backtest
touch backend/backtest/__init__.py

# Create live directory structure
mkdir -p backend/live
mkdir -p backend/live/adapters
touch backend/live/__init__.py
touch backend/live/adapters/__init__.py
```

**Phase 2: Move Backtest Code** (Optional - can be done later)
```bash
# Option A: Move BacktestEngine to backtest/ (recommended for clarity)
mv backend/core/engine.py backend/backtest/engine.py

# Option B: Keep in core/ but rename to clarify it's backtest-specific
# (Less disruptive, but less clear separation)

# Update imports in api/server.py
# FROM: from backend.core.engine import BacktestEngine
# TO:   from backend.backtest.engine import BacktestEngine
```

**Phase 3: Create Live Code** (During Live Development)
```bash
# Create live components as they're developed
touch backend/live/engine.py
touch backend/live/orchestrator.py
touch backend/live/trading_node.py
touch backend/live/oms.py
touch backend/live/positions.py
touch backend/live/risk.py
touch backend/live/router.py
touch backend/live/adapters/base.py
touch backend/live/adapters/deribit.py
touch backend/live/adapters/registry.py
```

**Phase 4: Create Live API** (During Live Development)
```bash
# Create live API server
touch backend/api/live_server.py
# Import from backend.live.*
```

**Phase 5: Update Imports** (As components are created)
- ✅ **Current**: `backend/api/server.py` imports from `backend.core.engine`
- ⏳ **Target**: `backend/api/server.py` imports from `backend.backtest.engine` (after Phase 2)
- ⏳ **New**: `backend/api/live_server.py` imports from `backend.live.*`
- ✅ **Ensure**: Shared components (`backend/execution/`, `backend/data/`, etc.) never import from `backend.backtest.*` or `backend.live.*`

**Phase 6: Update Docker Services** (When both services exist)
```yaml
# Backtest service
services:
  backend:
    profiles: ["backtest", "both"]
    command: uvicorn backend.api.server:app --host 0.0.0.0 --port 8000

# Live service  
  live-backend:
    profiles: ["live", "both"]
    command: uvicorn backend.api.live_server:app --host 0.0.0.0 --port 8001
```

**Note**: Migration can be done incrementally. Backtest code can stay in `backend/core/engine.py` initially, and be moved to `backend/backtest/` later if desired.

---

## Service Boundaries

### Backtest Service (Port 8000)

**Entry Point**: `backend/api/server.py`

**Current Imports** (December 2025):
- ✅ `backend.core.engine` - BacktestEngine (CURRENT: in core/)
- ✅ `backend.execution.*` - Shared execution algorithms
- ✅ `backend.data.*` - Shared data management
- ✅ `backend.instruments.*` - Shared instrument management
- ✅ `backend.config.*` - Shared configuration
- ✅ `backend.results.*` - Shared result processing
- ❌ **Never** imports from `backend.live.*`

**Target Imports** (After reorganization):
- ✅ `backend.backtest.*` - Backtest-specific code (TARGET: move from core/)
- ✅ `backend.execution.*` - Shared execution algorithms
- ✅ `backend.data.*` - Shared data management
- ✅ `backend.instruments.*` - Shared instrument management
- ✅ `backend.config.*` - Shared configuration
- ✅ `backend.results.*` - Shared result processing
- ❌ **Never** imports from `backend.live.*`

**Docker Service**:
```yaml
services:
  backend:
    profiles: ["backtest", "both"]
    command: uvicorn backend.api.server:app --host 0.0.0.0 --port 8000
```

### Live Service (Port 8001)

**Entry Point**: `backend/api/live_server.py`

**Imports From**:
- ✅ `backend.live.*` - Live-specific code
- ✅ `backend.execution.*` - Shared execution algorithms
- ✅ `backend.instruments.*` - Shared instrument management
- ✅ `backend.config.*` - Shared configuration
- ✅ `backend.data.*` - Shared data management (for signal loading)
- ❌ **Never** imports from `backend.backtest.*`

**Docker Service**:
```yaml
services:
  live-backend:
    profiles: ["live", "both"]
    command: uvicorn backend.api.live_server:app --host 0.0.0.0 --port 8001
```

---

## Code Sharing Strategy

### Shared Modules

**Location**: `backend/execution/`, `backend/data/`, `backend/instruments/`, etc.

**Rules**:
1. ✅ **No dependencies** on `backend.backtest.*` or `backend.live.*`
2. ✅ **Pure functions/classes** that can be used by both
3. ✅ **Abstract interfaces** where needed (e.g., `ExecAlgorithm` base class)
4. ✅ **Configuration-driven** behavior (no hardcoded assumptions)

**Example - Execution Algorithms**:
```python
# backend/execution/algorithms.py
# Shared by both backtest and live

class TWAPExecAlgorithm(ExecAlgorithm):
    """Time-Weighted Average Price algorithm - shared by backtest and live."""
    
    def __init__(self, config: Dict[str, Any]):
        # No assumptions about backtest vs live
        # Works in both contexts
        pass
```

### Service-Specific Wrappers

**Pattern**: Wrap shared components with service-specific logic

**Example - Router**:
```python
# backend/execution/router.py (Shared base logic)
class BaseRouter:
    def calculate_execution_cost(self, venue: str, order: Order) -> float:
        # Shared logic for cost calculation
        pass

# backend/live/router.py (Live-specific wrapper)
from backend.execution.router import BaseRouter

class LiveSmartRouter(BaseRouter):
    def route_order(self, order: Order) -> VenueRoute:
        # Live-specific routing logic
        # Uses BaseRouter for cost calculation
        # Adds live-specific considerations (latency, real-time liquidity)
        pass
```

---

## Testing Strategy

### Unit Tests

**Structure**:
```
tests/
├── backtest/
│   ├── test_engine.py
│   └── test_orchestrator.py
├── live/
│   ├── test_engine.py
│   ├── test_orchestrator.py
│   └── test_adapters/
│       └── test_deribit.py
└── shared/
    ├── test_execution_algorithms.py
    ├── test_instruments.py
    └── test_data_loader.py
```

### Integration Tests

**Backtest Integration**:
- Test `backend/api/server.py` endpoints
- Test `backend/backtest/engine.py` with real data
- Mock shared components if needed

**Live Integration**:
- Test `backend/api/live_server.py` endpoints
- Test `backend/live/orchestrator.py` with mock venues
- Mock shared components if needed

---

## Documentation Requirements

### Code Documentation

**Each Module Should Document**:
1. **Purpose**: What this module does
2. **Service**: Which service(s) use this module (backtest, live, or both)
3. **Dependencies**: What it depends on
4. **Usage**: How to use it

**Example**:
```python
"""
Live Execution Orchestrator.

Purpose: Main entry point for live order execution, coordinates all components.

Service: Live service only (port 8001)

Dependencies:
    - backend.live.trading_node (LiveTradingNode)
    - backend.live.oms (UnifiedOrderManager)
    - backend.live.risk (PreTradeRiskEngine)
    - backend.execution.algorithms (shared)

Usage:
    orchestrator = LiveExecutionOrchestrator(...)
    await orchestrator.submit_order(order)
"""
```

### Architecture Documentation

**Update**:
- `docs/live/ARCHITECTURE.md` - Add file organization section
- `docs/backtesting/CURRENT_SYSTEM.md` - Document backtest file structure
- `README.md` - Add file organization overview

---

## Benefits of This Organization

### 1. Clear Separation ✅
- Easy to see what code belongs to which service
- No confusion about where to add new features
- Clear boundaries prevent accidental coupling

### 2. Easy Maintenance ✅
- Changes to backtest don't affect live code
- Changes to live don't affect backtest code
- Shared components clearly identified

### 3. Scalability ✅
- Easy to split into separate repositories if needed
- Easy to add new services (e.g., sandbox, paper trading)
- Clear patterns for new components

### 4. Testing ✅
- Easy to test each service independently
- Shared components tested once, used everywhere
- Clear test organization

### 5. Onboarding ✅
- New developers can quickly understand structure
- Clear where to find code for specific features
- Documentation matches file structure

---

## Anti-Patterns to Avoid

### ❌ Don't: Mix Live and Backtest Code

**Bad**:
```python
# backend/core/engine.py
class Engine:
    def run(self, mode: str):
        if mode == "backtest":
            # Backtest logic
        elif mode == "live":
            # Live logic
```

**Good**:
```python
# backend/backtest/engine.py
class BacktestEngine:
    def run(self):
        # Backtest logic only

# backend/live/engine.py
class LiveEngine:
    def run(self):
        # Live logic only
```

### ❌ Don't: Circular Dependencies

**Bad**:
```python
# backend/execution/algorithms.py
from backend.backtest.engine import BacktestEngine  # ❌ Circular!

# backend/backtest/engine.py
from backend.execution.algorithms import TWAPExecAlgorithm
```

**Good**:
```python
# backend/execution/algorithms.py
# No imports from backtest/ or live/

# backend/backtest/engine.py
from backend.execution.algorithms import TWAPExecAlgorithm  # ✅ One-way
```

### ❌ Don't: Service-Specific Logic in Shared Code

**Bad**:
```python
# backend/execution/router.py (shared)
def route_order(order: Order, is_live: bool):
    if is_live:
        # Live-specific logic
    else:
        # Backtest-specific logic
```

**Good**:
```python
# backend/execution/router.py (shared)
def calculate_execution_cost(venue: str, order: Order) -> float:
    # Shared logic only

# backend/live/router.py (live-specific)
def route_order(order: Order) -> VenueRoute:
    cost = calculate_execution_cost(order.venue, order)
    # Live-specific routing logic
```

---

## Summary

### Key Principles

1. **Clear Directory Boundaries**: `backend/backtest/` vs `backend/live/` vs shared modules
2. **No Cross-Imports**: Shared code never imports from backtest/ or live/
3. **Service-Specific Entry Points**: `backend/api/server.py` (backtest) vs `backend/api/live_server.py` (live)
4. **Shared Components**: Clearly identified and documented
5. **Consistent Patterns**: Same organization patterns throughout

### File Organization Checklist

- [ ] Create `backend/backtest/` directory
- [ ] Create `backend/live/` directory
- [ ] Move BacktestEngine to `backend/backtest/`
- [ ] Create LiveExecutionOrchestrator in `backend/live/`
- [ ] Create separate API entry points
- [ ] Update all imports
- [ ] Document file organization
- [ ] Update Docker Compose services
- [ ] Create test structure
- [ ] Update documentation

---

*Last updated: December 2025*
*Applies to: Live Execution System Architecture*

