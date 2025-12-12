# Phase 2: TradingNode Integration - Implementation Plan

> **Status**: In Progress  
> **Goal**: Integrate NautilusTrader TradingNode for Binance, Bybit, OKX (CeFi)  
> **Timeline**: Weeks 3-4  
> **SSOT Reference**: `docs/live/ROADMAP.md`, `docs/live/ARCHITECTURE.md`

---

## Overview

Phase 2 integrates NautilusTrader's `TradingNode` for live execution on CeFi venues (Binance, Bybit, OKX). This phase establishes the foundation for live trading while maintaining separation from the backtest system.

**Key Principles**:
- Mirror backtest design patterns but adapted for live execution
- Use NautilusTrader `TradingNode` (not `BacktestNode`)
- Subscribe to real-time events (orders, positions, account updates)
- Maintain unified schema for all venue types (CeFi, DeFi, TradFi, Sports)

---

## Tasks Breakdown

### Task 1: Create `LiveTradingNode` Wrapper Class

**File**: `backend/live/trading_node.py`

**Requirements**:
- Wrap NautilusTrader `TradingNode`
- Handle lifecycle: initialize, start, stop, reconnect
- Manage data clients and execution clients
- Error handling and logging

**Implementation Steps**:
1. Create `LiveTradingNode` class
2. Initialize `TradingNode` with config
3. Register client factories (Binance, Bybit, OKX)
4. Implement lifecycle methods
5. Add health check methods

**Dependencies**:
- `nautilus_trader` library
- Configuration from `LiveConfigLoader`
- Database connection pool (for OMS sync)

---

### Task 2: Implement `TradingNodeConfig` Builder from JSON

**File**: `backend/live/config/trading_node_config.py`

**Requirements**:
- Build NautilusTrader `TradingNodeConfig` from JSON config
- Support data clients configuration
- Support execution clients configuration
- Support portfolio/account configuration
- Environment variable substitution

**Implementation Steps**:
1. Parse JSON config sections (`trading_node.data_clients`, `trading_node.exec_clients`)
2. Create `BinanceSpotDataClient`, `BinanceFuturesDataClient` configs
3. Create `BinanceSpotExecutionClient`, `BinanceFuturesExecutionClient` configs
4. Create `BybitDataClient`, `BybitExecutionClient` configs
5. Create `OKXDataClient`, `OKXExecutionClient` configs
6. Build `TradingNodeConfig` with all clients
7. Configure portfolio/accounts

**Dependencies**:
- `LiveConfigLoader` (from Phase 1)
- NautilusTrader client config classes

---

### Task 3: Register Client Factories

**File**: `backend/live/trading_node.py` (within `LiveTradingNode`)

**Requirements**:
- Register Binance Spot/Futures client factories
- Register Bybit client factories
- Register OKX client factories
- Handle API key/secret from config

**Implementation Steps**:
1. Import NautilusTrader client factories
2. Register Binance factories (spot and futures)
3. Register Bybit factories
4. Register OKX factories
5. Configure API credentials from config

**Dependencies**:
- NautilusTrader client factory classes
- Config with API keys/secrets

---

### Task 4: Subscribe to Order Events

**File**: `backend/live/trading_node.py` (event handlers)

**Requirements**:
- Subscribe to `OrderSubmitted` events
- Subscribe to `OrderFilled` events
- Subscribe to `OrderCancelled` events
- Subscribe to `OrderRejected` events
- Update Unified OMS (via asyncpg)

**Implementation Steps**:
1. Create event handler methods
2. Subscribe to TradingNode event bus
3. Convert NautilusTrader events → UnifiedOrder updates
4. Update database via asyncpg (raw SQL)
5. Log events for debugging

**Dependencies**:
- NautilusTrader event bus
- Unified OMS (asyncpg queries)
- Database connection pool

---

### Task 5: Implement Position Sync from NautilusTrader Portfolio

**File**: `backend/live/positions.py` (position sync methods)

**Requirements**:
- Query NautilusTrader Portfolio for positions
- Convert NautilusTrader positions → UnifiedPosition format
- Update Unified Position Tracker (via asyncpg)
- Handle canonical ID mapping

**Implementation Steps**:
1. Query TradingNode portfolio
2. Iterate through positions
3. Convert InstrumentId → canonical_id
4. Aggregate positions by canonical_id
5. Update database via asyncpg
6. Handle venue breakdown (venue_positions JSONB)

**Dependencies**:
- NautilusTrader Portfolio
- Instrument converter (canonical ID mapping)
- Database connection pool

---

### Task 6: Test with Paper Trading Accounts

**File**: `docs/live/implementation/phase2/TESTING.md`

**Requirements**:
- Test TradingNode connection
- Test order submission
- Test event subscriptions
- Test position sync
- Verify database updates

**Implementation Steps**:
1. Create test config with paper trading API keys
2. Start TradingNode
3. Submit test orders
4. Verify events received
5. Verify database updates
6. Test position sync

**Dependencies**:
- Paper trading accounts (Binance, Bybit, OKX)
- Test configuration files

---

## File Structure

```
backend/live/
├── trading_node.py          # LiveTradingNode wrapper class
├── config/
│   ├── loader.py            # LiveConfigLoader (Phase 1)
│   └── trading_node_config.py  # TradingNodeConfig builder
├── positions.py             # Position sync from NautilusTrader
├── models.py                # Database models (Phase 1)
└── database.py              # Database connection pool (Phase 1)
```

---

## Integration Points

### With Phase 1 Components:
- **Database**: Use `backend/live/database.py` for asyncpg queries
- **Config**: Use `backend/live/config/loader.py` for JSON config
- **Models**: Use `backend/live/models.py` for schema reference

### With Future Phases:
- **Phase 3**: External adapters will use similar event patterns
- **Phase 4**: Unified OMS will consume TradingNode events
- **Phase 4**: Unified Position Tracker will sync from TradingNode

---

## Success Criteria

- [ ] TradingNode connects to Binance/Bybit/OKX
- [ ] Order events received and logged
- [ ] Positions synced from NautilusTrader Portfolio
- [ ] Database updated via asyncpg (raw SQL)
- [ ] Paper trading test successful
- [ ] Error handling and reconnection logic working

---

## Notes

- **Separation**: Keep `backend/live/` separate from `backend/backtest/`
- **Performance**: Use asyncpg for all database operations (not SQLAlchemy ORM)
- **Events**: Subscribe to TradingNode event bus for real-time updates
- **Testing**: Use paper trading accounts for initial testing

---

*Last updated: December 2025*

