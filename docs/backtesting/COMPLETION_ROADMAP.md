# Backtesting System - Completion Roadmap

> **Source of Truth (SSOT)** for what's needed to complete the backtesting system for CeFi and TradFi.

## Current Status

### ✅ Completed (CeFi)
- [x] Backtest engine with NautilusTrader BacktestNode
- [x] External JSON configuration
- [x] Automatic data conversion (Parquet → NautilusTrader catalog)
- [x] Execution algorithms (TWAP, VWAP, Iceberg)
- [x] Smart router (basic venue selection)
- [x] Unified Cloud Services (UCS) integration for GCS
- [x] Fast and Report output modes
- [x] Docker Compose deployment
- [x] Frontend UI (React/Vite)
- [x] CeFi venues: Binance Spot/Futures, Bybit, OKX

### ⏳ In Progress
- [ ] Deribit venue support 
- [ ] TradFi venue support (Interactive Brokers)
- [ ] Enhanced TradFi data format support
- [ ] TradFi-specific execution algorithms
- [ ] Multi-venue backtesting (CeFi + TradFi simultaneously)

### 🔮 Future
- [ ] DeFi venue support
- [ ] Sports betting venue support
- [ ] Cross-venue arbitrage strategies

---

## Completion Requirements

### 1. Deribit Venue Support (CeFi)

#### 1.1 Deribit Integration
**Status**: In Progress

**Overview**: Deribit is a cryptocurrency derivatives exchange specializing in options and futures. It's not directly supported by NautilusTrader, so requires an external adapter implementation.

**Requirements**:
- [ ] Deribit API client setup (REST + WebSocket)
- [ ] Deribit instrument provider (options, futures, perpetuals)
- [ ] Deribit data client for historical data
- [ ] Deribit execution client for backtesting
- [ ] Deribit-specific order types (limit, market, stop-loss)
- [ ] Deribit authentication (HMAC-SHA256)

**Implementation Steps**:
1. Set up Deribit API credentials (testnet: test.deribit.com)
2. Create Deribit adapter following external adapter pattern (similar to live execution)
3. Implement Deribit REST API client for market data
4. Implement Deribit WebSocket client for real-time data
5. Add Deribit data format converters (similar to CeFi converters)
6. Test with Deribit testnet
7. Add Deribit-specific configuration options

**API Documentation**:
- Deribit API: https://docs.deribit.com/
- Python Client: https://github.com/deribit/deribit-api-clients
- Test Environment: https://test.deribit.com/

**Key Features**:
- Options trading (BTC, ETH options)
- Futures trading (perpetual futures)
- High leverage support
- Advanced order types

**Data Sources**:
- Deribit public API (market data)
- Deribit private API (account data, historical trades)
- GCS storage: `gs://market-data-tick-cefi-central-element-323112/` (Deribit data)

**Implementation Notes**:
- Deribit uses HMAC-SHA256 authentication
- Rate limit: 100 requests/minute for authenticated requests
- WebSocket for real-time data, REST for historical data
- Similar to other CeFi venues but requires external adapter (not in NautilusTrader)

---

### 2. TradFi Venue Support

#### 1.1 Interactive Brokers Integration
**Status**: Not started

**Requirements**:
- [ ] IB TWS/Gateway connection setup
- [ ] IB instrument provider integration
- [ ] IB data client for historical data
- [ ] IB execution client for backtesting
- [ ] IB-specific order types (STP, TRAIL, etc.)
- [ ] IB account types (Cash, Margin, IRA)

**Implementation Steps**:
1. Install IB TWS/Gateway locally
2. Create IB adapter following NautilusTrader IB integration patterns
3. Add IB data format converters (similar to CeFi converters)
4. Test with IB demo account
5. Add IB-specific configuration options

**Reference**:
- NautilusTrader IB integration: https://nautilustrader.io/docs/latest/integrations/ib
- IB API documentation: https://interactivebrokers.github.io/tws-api/

#### 1.2 TradFi Data Format Support
**Status**: Not started

**Requirements**:
- [ ] TradFi instrument definitions (stocks, options, futures)
- [ ] TradFi market data format (NYSE, NASDAQ, CME, etc.)
- [ ] TradFi-specific data converters
- [ ] TradFi catalog structure

**Data Sources**:
- IB historical data API
- External data providers (if needed)

**Implementation Steps**:
1. Define TradFi instrument schemas
2. Create TradFi data converters (`backend/data_converter.py` extension)
3. Add TradFi catalog paths
4. Test data loading and conversion

#### 1.3 TradFi Execution Algorithms
**Status**: Not started

**Requirements**:
- [ ] TradFi-specific TWAP (market hours aware)
- [ ] TradFi-specific VWAP (volume-weighted for stocks)
- [ ] Limit order handling (NYSE, NASDAQ rules)
- [ ] Market-on-open/close orders
- [ ] Stop-loss and take-profit orders

**Implementation Steps**:
1. Extend existing execution algorithms for TradFi
2. Add market hours awareness
3. Add exchange-specific rules
4. Test with TradFi instruments

---

### 3. Enhanced Multi-Venue Support

#### 2.1 Cross-Venue Backtesting
**Status**: Not started

**Requirements**:
- [ ] Support multiple venues in single backtest
- [ ] Cross-venue position aggregation
- [ ] Cross-venue risk management
- [ ] Cross-venue execution routing

**Implementation Steps**:
1. Extend `BacktestRunConfig` to support multiple venues
2. Add multi-venue position tracker
3. Add cross-venue risk engine
4. Test with CeFi + TradFi simultaneously

#### 2.2 Unified Position Tracking
**Status**: Partial (CeFi only)

**Requirements**:
- [ ] Aggregate positions across CeFi venues
- [ ] Aggregate positions across TradFi venues
- [ ] Cross-venue exposure calculations
- [ ] Unified P&L reporting

---

### 4. Data Infrastructure

#### 3.1 TradFi Data Pipeline
**Status**: Not started

**Requirements**:
- [ ] TradFi data ingestion from IB
- [ ] TradFi data storage in GCS
- [ ] TradFi data catalog structure
- [ ] TradFi data validation

**GCS Buckets**:
- `gs://instruments-store-tradfi-central-element-323112/` (TradFi instruments)
- `gs://market-data-tick-tradfi-central-element-323112/` (TradFi market data)

#### 3.2 Data Quality & Validation
**Status**: Partial

**Requirements**:
- [ ] Data completeness checks
- [ ] Data consistency validation
- [ ] Missing data handling
- [ ] Data quality metrics

---

### 5. Testing & Validation

#### 4.1 TradFi Test Suite
**Status**: Not started

**Requirements**:
- [ ] TradFi backtest unit tests
- [ ] TradFi integration tests
- [ ] TradFi data validation tests
- [ ] TradFi execution algorithm tests

#### 4.2 Performance Testing
**Status**: Partial

**Requirements**:
- [ ] Multi-venue performance benchmarks
- [ ] Large-scale backtest performance
- [ ] Memory usage optimization
- [ ] Parallel execution testing

---

### 6. Documentation

#### 5.1 TradFi Documentation
**Status**: Not started

**Requirements**:
- [ ] TradFi setup guide
- [ ] TradFi configuration examples
- [ ] TradFi execution algorithms guide
- [ ] TradFi troubleshooting guide

#### 5.2 API Documentation
**Status**: Partial

**Requirements**:
- [ ] Complete API reference
- [ ] Multi-venue API examples
- [ ] Error handling guide

---

## Implementation Priority

### Phase 1: Deribit Integration (Weeks 1-2)
1. Deribit API client setup
2. Deribit adapter implementation
3. Deribit data format support
4. Basic Deribit backtesting

### Phase 2: TradFi Foundation (Weeks 3-6)
1. IB TWS/Gateway setup
2. IB adapter implementation
3. TradFi data format support
4. Basic TradFi backtesting

### Phase 3: TradFi Enhancement (Weeks 7-10)
1. TradFi execution algorithms
2. TradFi-specific order types
3. TradFi data pipeline
4. TradFi testing suite

### Phase 4: Multi-Venue (Weeks 11-14)
1. Cross-venue backtesting
2. Unified position tracking
3. Cross-venue risk management
4. Multi-venue testing

### Phase 5: Production Readiness (Weeks 15-18)
1. Performance optimization
2. Documentation completion
3. Production deployment
4. Monitoring and alerting

---

## Success Criteria

### CeFi Completion
- ✅ Core CeFi venues supported (Binance, Bybit, OKX)
- ⏳ Deribit integration in progress
- ✅ All CeFi execution algorithms working
- ✅ GCS integration complete
- ✅ Production deployment ready

### TradFi Completion
- [ ] IB integration complete
- [ ] TradFi data pipeline operational
- [ ] TradFi execution algorithms working
- [ ] TradFi backtesting validated

### Multi-Venue Completion
- [ ] Cross-venue backtesting operational
- [ ] Unified position tracking working
- [ ] Cross-venue risk management validated
- [ ] Multi-venue performance acceptable

---

## Dependencies

### External
- Deribit API credentials (testnet available)
- Deribit API access (REST + WebSocket)
- Interactive Brokers TWS/Gateway
- IB API access
- TradFi market data access
- GCS buckets for CeFi/TradFi data

### Internal
- External adapter framework (for Deribit)
- NautilusTrader IB integration
- Unified Cloud Services (UCS)
- Backtest engine extensions
- Data converter extensions

---

## Notes

- **Deribit**: External adapter required (not in NautilusTrader), similar to live execution external adapter pattern
- **Deribit API**: Well-documented REST + WebSocket API, Python client available
- **Deribit Testnet**: Available for testing without real funds
- **TradFi**: Integration follows same patterns as CeFi
- Reuse existing execution algorithms where possible
- Extend data converters for Deribit/TradFi formats
- Maintain consistency with CeFi architecture
- Use UCS for all GCS operations (CeFi/TradFi data)

---

*Last updated: December 2025*
*Status: Planning phase*

