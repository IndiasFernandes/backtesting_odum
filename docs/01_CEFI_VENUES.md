# CeFi Venues - Centralized Finance (Crypto Exchanges)

> **Related Documentation**:
> - [`00_PROJECT_OVERVIEW.md`](./00_PROJECT_OVERVIEW.md) - System architecture and common concepts
> - [`02_DEFI_VENUES.md`](./02_DEFI_VENUES.md) - DeFi venues
> - [`03_TRADFI_VENUES.md`](./03_TRADFI_VENUES.md) - TradFi venues
> - [`04_SPORTS_BETTING_VENUES.md`](./04_SPORTS_BETTING_VENUES.md) - Sports betting venues

---

## Table of Contents

1. [Overview](#overview)
2. [Binance](#binance)
3. [Bybit](#bybit)
4. [OKX](#okx)
5. [Deribit](#deribit)
6. [Execution Flow Examples](#execution-flow-examples)
7. [Smart Execution for CeFi](#smart-execution-for-cefi)

---

## Overview

Centralized exchanges (CeFi) are traditional cryptocurrency exchanges that operate as centralized platforms with order books, matching engines, and custodial wallets. The execution system routes orders to CeFi venues via direct API calls or CCXT library.

### Supported Venues

| Venue | Venue Code | Supported Instruments | Status |
|-------|------------|----------------------|--------|
| **Binance** | `BINANCE-SPOT`, `BINANCE-FUTURES` | SPOT_PAIR, PERPETUAL, FUTURE | ✅ Implemented |
| **Bybit** | `BYBIT` | SPOT_PAIR, PERPETUAL | ✅ Implemented |
| **OKX** | `OKX` | SPOT_PAIR, PERPETUAL, FUTURE | ✅ Implemented |
| **Deribit** | `DERIBIT` | PERPETUAL, FUTURE, OPTION | ✅ Implemented |

### Common Characteristics

- **Order Types**: Market, Limit, Stop Market, Stop Limit
- **Testing**: Use small capital on mainnet (no testnet)
- **Rate Limits**: Vary by exchange (120-1200 requests/minute)
- **Data Provider**: Tardis (historical tick data for backtesting)
- **Execution Provider**: Direct API calls or CCXT library

---

## Binance

### Venue Information

**Venue Code**: `BINANCE-SPOT`, `BINANCE-FUTURES`

**Supported Instrument Types**:
- `SPOT_PAIR` (BINANCE-SPOT only)
- `PERPETUAL` (BINANCE-FUTURES only)
- `FUTURE` (BINANCE-FUTURES only)

### Instrument ID Format

```
BINANCE-SPOT:SPOT_PAIR:BTC-USDT
BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN
BINANCE-FUTURES:FUTURE:BTC-USDT-241225@LIN
```

### Execution Attributes

- **Spot API**: `https://api.binance.com/api/v3/`
- **Futures API**: `https://fapi.binance.com/fapi/v1/`
- **WebSocket**: `wss://stream.binance.com:9443/ws/`
- **Rate Limit**: 1200 requests/minute
- **Testing**: Use small capital on mainnet (no testnet)
- **Order Types**: `MARKET`, `LIMIT`, `STOP_MARKET`, `STOP_LOSS_LIMIT`
- **Min Order Size**: 0.001
- **Max Order Size**: 1000
- **Price Precision**: 2 decimal places
- **Quantity Precision**: 3 decimal places

### MVP Instruments

**21 base assets**:
- SOL, BTC, ETH, AVAX, ADA, SUSHI, CAKE, XRP, DOGE, XLM, LTC, ALGO, FIL, TRX, BNB, LINK, MATIC, APT, VET, ATOM, NEAR

### Exchange Raw Symbol Mapping

- Instrument ID `BINANCE-SPOT:SPOT_PAIR:BTC-USDT` → Exchange symbol `BTCUSDT`
- Instrument ID `BINANCE-FUTURES:PERPETUAL:ETH-USDT@LIN` → Exchange symbol `ETHUSDT`

### Execution Flow

1. Parse instrument ID → venue=`BINANCE-SPOT` or `BINANCE-FUTURES`, type=`SPOT_PAIR`/`PERPETUAL`/`FUTURE`, symbol=`BTC-USDT`
2. Lookup instrument definition → get `exchange_raw_symbol` = `BTCUSDT`
3. Route to Binance Spot API: `POST https://api.binance.com/api/v3/order` (spot) or Futures API (futures)
4. Map order type: `MARKET` → Binance `MARKET`
5. Execute order with symbol `BTCUSDT`
6. Return execution result with fills

---

## Bybit

### Venue Information

**Venue Code**: `BYBIT`

**Supported Instrument Types**:
- `SPOT_PAIR`
- `PERPETUAL`

### Instrument ID Format

```
BYBIT:SPOT_PAIR:BTC-USDT
BYBIT:PERPETUAL:ETH-USDT@LIN
```

### Execution Attributes

- **Spot API**: `https://api.bybit.com/v5/`
- **Futures API**: `https://api.bybit.com/v5/`
- **WebSocket**: `wss://stream.bybit.com/v5/public/spot`
- **Rate Limit**: 120 requests/minute
- **Testing**: Use small capital on mainnet (no testnet)
- **Order Types**: `Market`, `Limit`, `Stop`, `StopLimit`
- **Min Order Size**: 0.001
- **Max Order Size**: 1000
- **Price Precision**: 2 decimal places
- **Quantity Precision**: 3 decimal places

### MVP Instruments

Same 21 base assets as Binance

### Exchange Raw Symbol Mapping

- Instrument ID `BYBIT:SPOT_PAIR:BTC-USDT` → Exchange symbol `BTCUSDT`

### Execution Flow

1. Parse instrument ID → venue=`BYBIT`, type=`SPOT_PAIR`/`PERPETUAL`, symbol=`BTC-USDT`
2. Lookup instrument definition → get `exchange_raw_symbol` = `BTCUSDT`
3. Route to Bybit API: `POST https://api.bybit.com/v5/spot/order` (spot) or `/v5/order` (futures)
4. Map order type: `MARKET` → Bybit `Market`
5. Execute order with symbol `BTCUSDT`
6. Return execution result with fills

---

## OKX

### Venue Information

**Venue Code**: `OKX`

**Supported Instrument Types**:
- `SPOT_PAIR`
- `PERPETUAL`
- `FUTURE`

### Instrument ID Format

```
OKX:SPOT_PAIR:BTC-USDT
OKX:PERPETUAL:ETH-USDT@LIN
OKX:FUTURE:BTC-USDT-241225@LIN
```

### Execution Attributes

- **Spot API**: `https://www.okx.com/api/v5/`
- **Futures API**: `https://www.okx.com/api/v5/`
- **WebSocket**: `wss://ws.okx.com:8443/ws/v5/public`
- **Rate Limit**: 10 requests per 2 seconds
- **Testing**: Use small capital on mainnet (no testnet)
- **Order Types**: `market`, `limit`, `post_only`, `fok`, `ioc`
- **Min Order Size**: 0.001
- **Max Order Size**: 1000
- **Price Precision**: 2 decimal places
- **Quantity Precision**: 3 decimal places

### MVP Instruments

Same 21 base assets as Binance

### Exchange Raw Symbol Mapping

- Instrument ID `OKX:SPOT_PAIR:BTC-USDT` → Exchange symbol `BTC-USDT`

### Execution Flow

1. Parse instrument ID → venue=`OKX`, type=`SPOT_PAIR`/`PERPETUAL`/`FUTURE`, symbol=`BTC-USDT`
2. Lookup instrument definition → get `exchange_raw_symbol` = `BTC-USDT`
3. Route to OKX API: `POST https://www.okx.com/api/v5/trade/order` (spot) or `/api/v5/trade/order` (futures)
4. Map order type: `MARKET` → OKX `market`
5. Execute order with symbol `BTC-USDT`
6. Return execution result with fills

---

## Deribit

### Venue Information

**Venue Code**: `DERIBIT`

**Supported Instrument Types**:
- `PERPETUAL`
- `FUTURE`
- `OPTION`

### Instrument ID Format

```
DERIBIT:PERPETUAL:BTC-USD@INV
DERIBIT:FUTURE:BTC-USD-241225@INV
DERIBIT:OPTION:BTC-USD-241225-50000-CALL@INV
```

### Execution Attributes

- **API**: `https://www.deribit.com/api/v2/`
- **WebSocket**: `wss://www.deribit.com/ws/api/v2`
- **Rate Limit**: Varies by endpoint
- **Order Types**: `market`, `limit`, `stop_market`, `stop_limit`
- **Margin Currency**: BTC (inverse) or USD (linear)

### Specialization

Deribit specializes in BTC/ETH derivatives with inverse contracts (BTC margin). Most contracts use inverse margin, where:
- Margin currency = base asset (BTC)
- P&L calculated in base currency
- Example: `DERIBIT:PERPETUAL:BTC-USD@INV` uses BTC as margin

### Execution Flow

1. Parse instrument ID → venue=`DERIBIT`, type=`PERPETUAL`/`FUTURE`/`OPTION`, symbol=`BTC-USD`
2. Lookup instrument definition → get `exchange_raw_symbol` and contract details
3. Route to Deribit API: `POST https://www.deribit.com/api/v2/private/buy` or `/sell`
4. Map order type: `MARKET` → Deribit `market`
5. Execute order with Deribit symbol format
6. Return execution result with fills

---

## Execution Flow Examples

### Example 1: CeFi Spot Trade

**Input**: Order instruction
```json
{
  "operation_id": "trade_001",
  "operation": "trade",
  "instrument_key": "BINANCE-SPOT:SPOT_PAIR:BTC-USDT",
  "side": "BUY",
  "amount": 0.1,
  "order_type": "MARKET",
  "expected_deltas": {
    "BINANCE-SPOT:SPOT_ASSET:BTC": 0.1,
    "BINANCE-SPOT:SPOT_ASSET:USDT": -3000.0
  }
}
```

**Execution Flow**:
1. Parse instrument ID → venue=`BINANCE-SPOT`, type=`SPOT_PAIR`, symbol=`BTC-USDT`
2. Lookup instrument definition → get `exchange_raw_symbol` = `BTCUSDT`
3. Route to Binance Spot API: `POST https://api.binance.com/api/v3/order`
4. Map order type: `MARKET` → Binance `MARKET`
5. Execute order with symbol `BTCUSDT`
6. Return execution result with fills

**Output**: Execution response
```json
{
  "execution_id": "exec_001",
  "status": "success",
  "venue": "BINANCE-SPOT",
  "instrument_id": "BINANCE-SPOT:SPOT_PAIR:BTC-USDT",
  "fills": [
    {
      "price": 30000.0,
      "quantity": 0.1,
      "timestamp": "2025-01-15T10:30:00Z"
    }
  ],
  "position_deltas": {
    "BINANCE-SPOT:SPOT_ASSET:BTC": 0.1,
    "BINANCE-SPOT:SPOT_ASSET:USDT": -3000.0
  }
}
```

### Example 2: CeFi Perpetual Futures

**Input**: Order instruction
```json
{
  "operation_id": "trade_002",
  "operation": "trade",
  "instrument_key": "BINANCE-FUTURES:PERPETUAL:ETH-USDT@LIN",
  "side": "BUY",
  "amount": 1.0,
  "order_type": "LIMIT",
  "price": 2500.0,
  "expected_deltas": {
    "BINANCE-FUTURES:PERPETUAL:ETH-USDT@LIN": 1.0
  }
}
```

**Execution Flow**:
1. Parse instrument ID → venue=`BINANCE-FUTURES`, type=`PERPETUAL`, symbol=`ETH-USDT@LIN`
2. Lookup instrument definition → get `exchange_raw_symbol` = `ETHUSDT`
3. Route to Binance Futures API: `POST https://fapi.binance.com/fapi/v1/order`
4. Map order type: `LIMIT` → Binance `LIMIT`
5. Execute limit order with symbol `ETHUSDT`, price `2500.0`
6. Return execution result with fills

---

## Smart Execution for CeFi

### CeFi Smart Algo Execution

**Objective**: Optimize execution for crypto CEX venues (Binance, Bybit, OKX)

**Capabilities**:
- **Venue Selection**: Compare execution costs across venues for same instrument
- **TWAP (Time-Weighted Average Price)**: Split orders over time windows to reduce market impact
- **Order Splitting**: Break large orders into smaller chunks based on:
  - Order book depth analysis
  - Historical volume patterns
  - Market volatility
- **Optimal Timing**: Analyze tick data to identify optimal entry points
- **Venue Health Monitoring**: Monitor venue latency, order book depth, and fill rates
- **Dynamic Routing**: Route orders to best-performing venue in real-time

**Supported Venues**: Binance, Bybit, OKX (spot and perpetual futures)

**Input**: Order with `SPOT_PAIR` or `PERPETUAL` instrument ID, `smart_execution_enabled = True`

**Output**: Executed order with improved fill prices vs naive market order

### Execution Flow with Smart Execution

```
Order Received (smart_execution_enabled = True)
  ↓
Query All Venues for Instrument
  ↓
Analyze Order Book Depth (Binance, Bybit, OKX)
  ↓
Simulate Execution Across Venues
  ↓
Calculate Expected Slippage
  ↓
Select Best Venue OR Split Across Venues
  ↓
Apply TWAP if Order Size > Threshold
  ↓
Execute Order(s) with Optimal Timing
  ↓
Return Execution Results
```

### Tick Data Analysis for CeFi

**Data Source**: Tardis (historical tick data for Binance, Bybit, OKX)

**Capabilities**:
- **Real-Time Tick Processing**: Consume tick data streams from Tardis
- **Order Book Reconstruction**: Build order book snapshots from tick data
- **Liquidity Analysis**: Assess available liquidity at different price levels
- **Optimal Fill Timing**: Identify time windows with:
  - Higher liquidity
  - Lower volatility
  - Better price levels
- **Market Microstructure**: Analyze bid-ask spreads, order flow, and trade patterns

### Slippage Optimization for CeFi

**Pre-Trade Simulation**:
- Simulate execution across venues (Binance, Bybit, OKX) before placing order
- Calculate expected slippage based on:
  - Order size vs available liquidity
  - Historical slippage patterns
  - Current market conditions
- Compare expected slippage across venues for same instrument
- Select venue with lowest total execution cost (price impact + fees)

---

## Order Type Mapping

### CeFi Order Types

| System Order Type | Binance | Bybit | OKX | Deribit |
|-------------------|---------|-------|-----|---------|
| `MARKET` | `MARKET` | `Market` | `market` | `market` |
| `LIMIT` | `LIMIT` | `Limit` | `limit` | `limit` |
| `STOP_MARKET` | `STOP_MARKET` | `Stop` | N/A | `stop_market` |
| `STOP_LOSS_LIMIT` | `STOP_LOSS_LIMIT` | `StopLimit` | N/A | `stop_limit` |

### Order Type Details

**Market Orders**:
- Execute immediately at best available price
- No price guarantee
- Higher slippage risk for large orders

**Limit Orders**:
- Execute only at specified price or better
- Price guarantee
- May not fill if price moves away

**Stop Market Orders**:
- Triggered when price reaches stop price
- Executes as market order after trigger
- Used for stop-loss protection

**Stop Limit Orders**:
- Triggered when price reaches stop price
- Executes as limit order at specified price after trigger
- More price control than stop market

---

## Backtesting for CeFi

### Data Sources

- **Tardis**: Historical tick data for Binance, Bybit, OKX
- **Data Types**: Trades, order book snapshots, liquidations
- **Access**: SDK access (when ready, we'll get the latest repo to work off)
- **Headers**: Tick data sample headers haven't changed, so previous code should work

### Execution Simulation

- **Order Book Reconstruction**: Build order book from tick data
- **Slippage Modeling**: Model slippage based on order size and liquidity
- **Fill Price Calculation**: Calculate fill prices using order book depth
- **Realistic Latency**: Model execution timing and latency
- **Venue-Specific Behavior**: Model venue-specific execution characteristics

### Backtesting Flow

```
Pre-generated Orders (from Strategy Service)
  ↓
Read Orders from GCS
  ↓
Query Tick Data (Tardis)
  ↓
Reconstruct Order Book
  ↓
Simulate Execution
  ↓
Calculate Fill Prices with Slippage
  ↓
Return Execution Results
  ↓
Update Strategy Positions
```

---

## Related Documentation

- **Project Overview**: [`00_PROJECT_OVERVIEW.md`](./00_PROJECT_OVERVIEW.md)
- **DeFi Venues**: [`02_DEFI_VENUES.md`](./02_DEFI_VENUES.md)
- **TradFi Venues**: [`03_TRADFI_VENUES.md`](./03_TRADFI_VENUES.md)
- **Sports Betting Venues**: [`04_SPORTS_BETTING_VENUES.md`](./04_SPORTS_BETTING_VENUES.md)





