# Live Execution Mechanism - Executive Summary

## Overview

This document provides a high-level summary of the live execution mechanism architecture. For detailed implementation plans, see `LIVE_EXECUTION_ARCHITECTURE.md`.

---

## Key Objectives

1. **Consistency with Backtest**: Use same execution algorithms, order types, and routing logic
2. **Multi-Venue Support**: Both NautilusTrader-integrated (CeFi) and external SDK adapters (TradFi, future DeFi/Sports)
3. **Unified Tracking**: Single source of truth for orders and positions across all venues
4. **Production-Ready**: Fault tolerance, monitoring, and real-time synchronization
5. **Spec Alignment**: Integrates with unified-cloud-services, uses same GCS buckets and output schemas as backtest infrastructure

---

## Architecture Highlights

### Core Components

```
Strategy Service
    ↓ (protobuf Order)
Live Execution Orchestrator
    ├── Pre-Trade Risk Engine
    ├── Unified OMS
    ├── Smart Router
    └── Unified Position Tracker
         ↓
    ┌────┴────┐
    │         │
NautilusTrader  External Adapters
TradingNode     (Deribit, IB, etc.)
```

### 1. Live Execution Orchestrator
- Main entry point for order execution
- Coordinates risk checks, OMS, routing, and execution
- Handles error recovery and graceful degradation
- Integrates with strategy-service for signal-driven execution

### 2. TradingNode Integration
- Integrates NautilusTrader `TradingNode` for CeFi venues
- Supports Binance (Spot/Futures), Bybit, OKX
- Event-driven updates (order events, position updates)

### 3. External SDK Adapter Framework
- Abstract interface for venues not in NautilusTrader
- Reference implementation: Deribit adapter
- Easy to extend for future venues (IB, DeFi, Sports)

### 4. Unified OMS
- Tracks all orders across all venues
- Syncs with NautilusTrader Cache (real-time)
- Syncs with external adapters (polling/webhooks)
- PostgreSQL persistence

### 5. Unified Position Tracker
- Aggregates positions from all venues
- Unified queries by canonical ID, strategy, venue
- Exposure calculations (total notional value)

### 6. Smart Order Router
- Routes orders to optimal venue
- Considers execution cost, fees, liquidity, latency
- Supports both NautilusTrader and external venues

### 7. Pre-Trade Risk Engine
- Velocity checks (orders per second/minute)
- Position limits (per-instrument, per-strategy, global)
- Exposure limits (total notional value)
- Order size validation

### 8. Unified Cloud Services Integration
- Uses `unified-cloud-services` for GCS data access
- Byte-range streaming for efficient tick data loading
- Signal-driven execution (only fetch data for signal intervals)
- Uploads results to `execution-store-cefi-central-element-323112` bucket

### 9. Signal-Driven Execution
- Loads sparse signals from strategy-service (~29 signals/day)
- Streams only 5-minute windows of tick data for each signal
- 94% I/O reduction compared to full file downloads
- 85% faster execution time

---

## Key Design Decisions

### 1. Consistency with Backtest
- **Decision**: Reuse same execution algorithms (TWAP, VWAP, Iceberg)
- **Rationale**: Ensures backtest results are predictive of live performance
- **Impact**: Strategies can be tested in backtest and deployed live with confidence

### 2. Unified Abstraction
- **Decision**: Single interface for NautilusTrader and external venues
- **Rationale**: Simplifies strategy code and enables venue-agnostic routing
- **Impact**: Strategies don't need to know which venue executes their orders

### 3. State Synchronization
- **Decision**: Real-time sync for NautilusTrader, periodic polling for external
- **Rationale**: NautilusTrader provides event-driven updates; external APIs may not
- **Impact**: Consistent state across all venues with minimal latency

### 4. Deployment Separation
- **Decision**: Deploy live execution separately from backtest, but share core mechanisms
- **Rationale**: Different scaling requirements and operational concerns
- **Impact**: Independent deployment and scaling, shared codebase for consistency

---

## Implementation Phases

### Phase 1: Core Infrastructure (Weeks 1-2)
- Module structure
- Database schema
- Configuration framework

### Phase 2: TradingNode Integration (Weeks 3-4)
- TradingNode wrapper
- Event subscriptions
- Order submission
- Position sync

### Phase 3: External Adapter Framework (Weeks 5-6)
- Base adapter interface
- Deribit adapter (reference)
- Adapter registry

### Phase 4: Unified OMS & Position Tracker (Weeks 7-8)
- Unified OMS implementation
- Unified Position Tracker
- State synchronization

### Phase 5: Risk Engine & Router Integration (Weeks 9-10)
- Pre-Trade Risk Engine
- Enhanced Smart Router
- Execution Orchestrator

### Phase 6: Testing & Validation (Weeks 11-12)
- Unit tests
- Integration tests
- Paper trading
- Production readiness

---

## Venue Support Matrix

| Venue Type | Venues | Integration Method | Status |
|------------|--------|-------------------|--------|
| **CeFi** | Binance Spot/Futures, Bybit, OKX | NautilusTrader TradingNode | ✅ Phase 2 |
| **TradFi** | Interactive Brokers | External SDK Adapter | ⏳ Phase 3 |
| **CeFi (External)** | Deribit | External SDK Adapter | ⏳ Phase 3 |
| **DeFi** | Uniswap, AAVE, etc. | External SDK Adapter | 🔮 Future |
| **Sports** | Betfair, etc. | External SDK Adapter | 🔮 Future |

---

## Configuration Example

```json
{
    "trading_node": {
        "data_clients": [
            {
                "name": "BINANCE_SPOT",
                "api_key": "${BINANCE_SPOT_API_KEY}",
                "api_secret": "${BINANCE_SPOT_API_SECRET}"
            }
        ],
        "exec_clients": [
            // Same as data_clients
        ]
    },
    "external_adapters": {
        "DERIBIT": {
            "api_key": "${DERIBIT_API_KEY}",
            "api_secret": "${DERIBIT_API_SECRET}"
        }
    },
    "risk_engine": {
        "enabled": true,
        "max_orders_per_second": 10,
        "max_position_per_instrument": {
            "BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN": "1.0"
        }
    },
    "router": {
        "smart_execution_enabled": true
    },
    "gcs": {
        "instruments_bucket": "instruments-store-cefi-central-element-323112",
        "market_data_bucket": "market-data-tick-cefi-central-element-323112",
        "execution_bucket": "execution-store-cefi-central-element-323112"
    }
}
```

## Output Schemas (Aligned with Spec)

All execution results follow the same schema as backtest infrastructure:

- **summary.json**: High-level results (PNL, metrics, execution stats)
- **orders.parquet**: All order records with status tracking
- **fills.parquet**: All execution fills with fees
- **positions.parquet**: Position timeline with P&L
- **equity_curve.parquet**: Portfolio value over time

Results uploaded to: `gs://execution-store-cefi-central-element-323112/backtest_results/{run_id}/`

---

## External System Integration

### Strategy Service Protocol
- **Protocol**: Protobuf Order messages over gRPC or REST API
- **Message Format**: `Order` protobuf message (operation_id, instrument_key, side, amount, price, etc.)
- **Response Format**: `ExecutionResult` protobuf message (status, venue, fills, etc.)

### Venue API Management
- **NautilusTrader Venues**: Managed by TradingNode (automatic reconnection, event-driven)
- **External Venues**: Managed by adapters (custom reconnection, polling/webhooks)
- **Unified Interface**: All venues exposed through same interface

---

## Monitoring & Observability

### Metrics
- Order submission rate
- Order fill rate
- Latency (submission → fill)
- Venue selection distribution
- Risk rejections
- Position exposure

### Logging
- All order submissions
- All fills
- Risk check results
- Routing decisions
- State synchronization events

### Alerts
- High rejection rate
- Venue connectivity issues
- Position limit breaches
- Unusual latency

---

## Next Steps

1. **Review Architecture**: Review `LIVE_EXECUTION_ARCHITECTURE.md` for detailed design
2. **Set Up Infrastructure**: Create module structure, database schema, configuration framework
3. **Begin Phase 1**: Start with core infrastructure setup
4. **Iterate**: Follow phased implementation plan, test incrementally

---

## Key Files

- `LIVE_EXECUTION_ARCHITECTURE.md`: Detailed architecture and implementation plan
- `LIVE_EXECUTION_SUMMARY.md`: Executive summary (this document)
- `FRONTEND_SERVICE_DETECTION.md`: Frontend service detection and status page implementation plan
- `backend/live_execution/`: Live execution module (to be created)
- `backend/backtest_engine.py`: Reference implementation (backtest)
- `backend/ucs_data_loader.py`: Unified Cloud Services integration
- `.secrets/COMPLETE_USER_GUIDE.html`: User guide with execution orchestrator pattern

## Service Detection & UI

The frontend will automatically detect which services are running and show/hide pages accordingly:

- **Backtest Only**: Shows backtest pages when `odum-backend` (port 8000) is running
- **Live Only**: Shows live execution pages when `odum-live-backend` (port 8001) is running
- **Both**: Shows all pages when both services are running
- **Status Page**: Always available at `/status`, shows all service health and GCS bucket connectivity

See `FRONTEND_SERVICE_DETECTION.md` for detailed implementation plan.

## Migration from Current System

**Current Setup** (December 2025):
- `odum-backend` (port 8000) - Backtest ✅
- `odum-frontend` (port 5173) - UI ✅
- `data_downloads` - Data volume ✅ (fallback only, not primary)

**Current Data Flow** (UCS as Primary):
- ✅ **Data Source**: GCS via `unified-cloud-services` (UCS)
  - `backend/ucs_data_loader.py` uses UCS for all data loading
  - `UNIFIED_CLOUD_SERVICES_USE_DIRECT_GCS=true` (direct GCS API)
- ✅ **Data Destination**: GCS via `unified-cloud-services` (UCS)
  - `backend/results.py` uses UCS `upload_to_gcs()` for all results
  - Results written to `gs://execution-store-cefi-central-element-323112/`
  - Local `data_downloads/` is fallback only (FUSE mount or dev convenience)

**Migration Strategy** (Zero Downtime, Backward Compatible):

1. **Add Profiles**: Update `docker-compose.yml` to add profiles to existing services
   - Existing `docker-compose up -d` continues to work
   - New `docker-compose --profile backtest up -d` also works

2. **Add Live Services**: Create `docker-compose.profiles.yml` with live execution services
   - PostgreSQL, Redis, Live Backend added as new services
   - Existing backtest services unaffected

3. **Update Frontend**: Add service detection and conditional routing
   - Existing pages continue to work
   - New pages added conditionally

**Key Points**:
- ✅ No breaking changes to existing functionality
- ✅ No data migration required
- ✅ Easy rollback if needed
- ✅ Gradual rollout possible

See `FRONTEND_SERVICE_DETECTION.md` Section 8 for step-by-step migration guide.

## GCS Buckets (from Spec)

| Data | Bucket | Access Method |
|------|--------|---------------|
| Instrument Definitions | `gs://instruments-store-cefi-central-element-323112/` | UCS `download_from_gcs()` |
| Market Tick Data | `gs://market-data-tick-cefi-central-element-323112/` | UCS `download_from_gcs_streaming()` |
| Execution Results | `gs://execution-store-cefi-central-element-323112/` | UCS `upload_to_gcs()` |

**⚠️ Important**: `unified-cloud-services` (UCS) is the **PRIMARY** interface for all data operations:
- ✅ **Data Source**: GCS via UCS (not local `data_downloads/`)
- ✅ **Data Destination**: GCS via UCS (not local filesystem)
- ✅ Local volumes are fallback/development convenience only
- ✅ `UNIFIED_CLOUD_SERVICES_USE_DIRECT_GCS=true` ensures direct GCS API access

---

## Questions & Considerations

1. **Deployment Environment**: Where will live execution service be deployed? (Cloud, on-premise, hybrid)
2. **API Protocol**: Prefer gRPC or REST API for strategy service integration?
3. **Database**: PostgreSQL confirmed? Any specific requirements?
4. **Monitoring**: Preferred monitoring stack? (Prometheus, Datadog, etc.)
5. **External Venues**: Priority order for external adapter development? (Deribit first, then IB?)

---

## Conclusion

This architecture provides a robust, extensible foundation for live execution that mirrors the backtest design while supporting multiple venue types. The phased implementation plan enables incremental development and early validation of key components.

