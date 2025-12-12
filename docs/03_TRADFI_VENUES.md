# TradFi Venues - Traditional Finance

> **Related Documentation**:
> - [`00_PROJECT_OVERVIEW.md`](./00_PROJECT_OVERVIEW.md) - System architecture and common concepts
> - [`01_CEFI_VENUES.md`](./01_CEFI_VENUES.md) - CeFi venues
> - [`02_DEFI_VENUES.md`](./02_DEFI_VENUES.md) - DeFi venues
> - [`04_SPORTS_BETTING_VENUES.md`](./04_SPORTS_BETTING_VENUES.md) - Sports betting venues

---

## Table of Contents

1. [Overview](#overview)
2. [CME (Chicago Mercantile Exchange)](#cme-chicago-mercantile-exchange)
3. [CBOE (Cboe Global Markets)](#cboe-cboe-global-markets)
4. [NASDAQ / NYSE](#nasdaq--nyse)
5. [Execution Flow Examples](#execution-flow-examples)
6. [Smart Execution for TradFi](#smart-execution-for-tradfi)

---

## Overview

Traditional Finance (TradFi) venues provide access to regulated financial markets including equities, futures, options, and other traditional instruments. The execution system routes orders to TradFi venues through broker APIs, primarily Interactive Brokers.

### Supported Venues

| Venue | Venue Code | Supported Instruments | Execution Provider | Data Provider | Status |
|-------|------------|----------------------|-------------------|---------------|--------|
| **CME** | `CME` | FUTURE, OPTION | Interactive Brokers | Databento (GLBX.MDP3) | ⏳ Planned |
| **CBOE** | `CBOE` | INDEX | N/A (data only) | Barchart | ⏳ Planned |
| **NASDAQ** | `NASDAQ` | EQUITY | Interactive Brokers (planned) | Databento (DBEQ.BASIC) | ⏳ Planned |
| **NYSE** | `NYSE` | EQUITY | Interactive Brokers (planned) | Databento (DBEQ.BASIC) | ⏳ Planned |

### Common Characteristics

- **Execution Provider**: Interactive Brokers (TWS/IB Gateway API)
- **Data Providers**: Databento (GLBX.MDP3 for CME), Barchart (VIX), Databento (DBEQ.BASIC for equities)
- **Trading Hours**: Varies by instrument (CME: 23 hours/day, 5 days/week)
- **Contract Sizes**: Varies by instrument type
- **Regulation**: Regulated markets with specific trading rules

---

## CME (Chicago Mercantile Exchange)

### Venue Information

**Venue Code**: `CME`

**Execution Venue**: **Interactive Brokers** (IB)  
**Data Provider**: Databento (`GLBX.MDP3`)

**Supported Instrument Types**:
- `FUTURE`
- `OPTION`

### Instrument ID Format

```
CME:FUTURE:SP500-USD-241225@LIN
CME:FUTURE:CRUDE-USD-241225@LIN
CME:OPTION:SP500-USD-241225-4500-CALL@LIN
```

### Execution Attributes

- **Execution API**: Interactive Brokers TWS/IB Gateway API
- **Data API**: Databento (`GLBX.MDP3`)
- **Trading Hours**: Sunday 5:00 PM CT to Friday 4:00 PM CT (23 hours/day, 5 days/week)
- **Maintenance Break**: Daily 4:00-5:00 PM CT (1 hour)
- **Contract Sizes**: Varies by instrument (see MVP instruments below)
- **Order Types**: Market (`MKT`), Limit (`LMT`), Stop (`STP`)

### MVP Futures Instruments (42 total)

#### Equity Index Futures (5)

- **ES** (E-mini S&P 500): `CME:FUTURE:SP500-USD-{expiry}@LIN`
  - Contract size: $50 × index points
  - Tick size: 0.25 index points = $12.50
  
- **NQ** (E-mini NASDAQ-100): `CME:FUTURE:NASDAQ100-USD-{expiry}@LIN`
  - Contract size: $20 × index points
  - Tick size: 0.25 index points = $5.00
  
- **RTY** (E-mini Russell 2000): `CME:FUTURE:RUSSELL2000-USD-{expiry}@LIN`
  - Contract size: $50 × index points
  - Tick size: 0.10 index points = $5.00
  
- **YM** (E-mini Dow Jones): `CME:FUTURE:DOW-USD-{expiry}@LIN`
  - Contract size: $5 × index points
  - Tick size: 1 index point = $5.00
  
- **NKD** (Nikkei 225 Dollar): `CME:FUTURE:NIKKEI225-USD-{expiry}@LIN`
  - Contract size: $5 × index points
  - Tick size: 5 index points = $25.00

#### Sector Futures (8)

- **XAF** (Energy): `CME:FUTURE:ENERGY_SECTOR-USD-{expiry}@LIN`
- **XAK** (Technology): `CME:FUTURE:TECH_SECTOR-USD-{expiry}@LIN`
- **XAY** (Consumer Discretionary): `CME:FUTURE:CONSUMER_DISC_SECTOR-USD-{expiry}@LIN`
- **XAP** (Consumer Staples): `CME:FUTURE:CONSUMER_STAPLES_SECTOR-USD-{expiry}@LIN`
- **XAV** (Health Care): `CME:FUTURE:HEALTHCARE_SECTOR-USD-{expiry}@LIN`
- **XAI** (Industrials): `CME:FUTURE:INDUSTRIALS_SECTOR-USD-{expiry}@LIN`
- **XAB** (Materials): `CME:FUTURE:MATERIALS_SECTOR-USD-{expiry}@LIN`
- **XAU** (Utilities): `CME:FUTURE:UTILITIES_SECTOR-USD-{expiry}@LIN`

#### Treasury Futures (4)

- **ZT** (2-Year T-Note): `CME:FUTURE:TREASURY_2Y-USD-{expiry}@LIN`
  - Contract size: $200,000 face value
  - Tick size: 1/32 point = $15.625
  
- **ZF** (5-Year T-Note): `CME:FUTURE:TREASURY_5Y-USD-{expiry}@LIN`
  - Contract size: $100,000 face value
  - Tick size: 1/32 point = $15.625
  
- **ZN** (10-Year T-Note): `CME:FUTURE:TREASURY_10Y-USD-{expiry}@LIN`
  - Contract size: $100,000 face value
  - Tick size: 1/32 point = $15.625
  
- **ZB** (30-Year T-Bond): `CME:FUTURE:TREASURY_30Y-USD-{expiry}@LIN`
  - Contract size: $100,000 face value
  - Tick size: 1/32 point = $31.25

#### Crypto Futures (2)

- **BTC**: `CME:FUTURE:BTC-USD-{expiry}@LIN`
  - Contract size: 5 BTC
  - Tick size: $5.00
  
- **ETH**: `CME:FUTURE:ETH-USD-{expiry}@LIN`
  - Contract size: 50 ETH
  - Tick size: $0.25

#### Energy Commodities (4)

- **CL** (WTI Crude Oil): `CME:FUTURE:CRUDE-USD-{expiry}@LIN`
  - Contract size: 1,000 barrels
  - Tick size: $0.01 per barrel = $10.00
  
- **NG** (Natural Gas): `CME:FUTURE:NATGAS-USD-{expiry}@LIN`
  - Contract size: 10,000 MMBtu
  - Tick size: $0.001 per MMBtu = $10.00
  
- **HO** (Heating Oil): `CME:FUTURE:HEATING_OIL-USD-{expiry}@LIN`
  - Contract size: 1,000 U.S. gallons (42,000 gallons)
  - Tick size: $0.0001 per gallon = $4.20
  
- **RB** (RBOB Gasoline): `CME:FUTURE:GASOLINE-USD-{expiry}@LIN`
  - Contract size: 1,000 U.S. gallons (42,000 gallons)
  - Tick size: $0.0001 per gallon = $4.20

#### Metals (3)

- **GC** (Gold): `CME:FUTURE:GOLD-USD-{expiry}@LIN`
  - Contract size: 100 troy ounces
  - Tick size: $0.10 per troy ounce = $10.00
  
- **SI** (Silver): `CME:FUTURE:SILVER-USD-{expiry}@LIN`
  - Contract size: 5,000 troy ounces
  - Tick size: $0.005 per troy ounce = $25.00
  
- **HG** (Copper): `CME:FUTURE:COPPER-USD-{expiry}@LIN`
  - Contract size: 25,000 pounds
  - Tick size: $0.0005 per pound = $12.50

#### Agricultural Commodities (6)

- **CT** (Cotton): `CME:FUTURE:COTTON-USD-{expiry}@LIN`
  - Contract size: 50,000 pounds
  - Tick size: $0.01 per pound = $5.00
  
- **ZS** (Soybeans): `CME:FUTURE:SOYBEANS-USD-{expiry}@LIN`
  - Contract size: 5,000 bushels
  - Tick size: $0.25 per bushel = $12.50
  
- **ZC** (Corn): `CME:FUTURE:CORN-USD-{expiry}@LIN`
  - Contract size: 5,000 bushels
  - Tick size: $0.25 per bushel = $12.50
  
- **ZW** (Wheat): `CME:FUTURE:WHEAT-USD-{expiry}@LIN`
  - Contract size: 5,000 bushels
  - Tick size: $0.25 per bushel = $12.50
  
- **ZL** (Soybean Oil): `CME:FUTURE:SOYBEAN_OIL-USD-{expiry}@LIN`
  - Contract size: 60,000 pounds
  - Tick size: $0.0001 per pound = $6.00
  
- **ZM** (Soybean Meal): `CME:FUTURE:SOYBEAN_MEAL-USD-{expiry}@LIN`
  - Contract size: 100 short tons (200,000 pounds)
  - Tick size: $0.10 per short ton = $10.00

#### FX Futures (10)

- **6E** (Euro): `CME:FUTURE:EUR-USD-{expiry}@LIN`
  - Contract size: €125,000
  - Tick size: $0.0001 per euro = $12.50
  
- **6B** (British Pound): `CME:FUTURE:GBP-USD-{expiry}@LIN`
  - Contract size: £62,500
  - Tick size: $0.0001 per pound = $6.25
  
- **6J** (Japanese Yen): `CME:FUTURE:JPY-USD-{expiry}@LIN`
  - Contract size: ¥12,500,000
  - Tick size: $0.000001 per yen = $12.50
  
- **6A** (Australian Dollar): `CME:FUTURE:AUD-USD-{expiry}@LIN`
  - Contract size: AUD 100,000
  - Tick size: $0.0001 per AUD = $10.00
  
- **6C** (Canadian Dollar): `CME:FUTURE:CAD-USD-{expiry}@LIN`
  - Contract size: CAD 100,000
  - Tick size: $0.0001 per CAD = $10.00
  
- **6N** (New Zealand Dollar): `CME:FUTURE:NZD-USD-{expiry}@LIN`
  - Contract size: NZD 100,000
  - Tick size: $0.0001 per NZD = $10.00
  
- **6S** (Swiss Franc): `CME:FUTURE:CHF-USD-{expiry}@LIN`
  - Contract size: CHF 125,000
  - Tick size: $0.0001 per CHF = $12.50
  
- **6M** (Mexican Peso): `CME:FUTURE:MXN-USD-{expiry}@LIN`
  - Contract size: MXN 500,000
  - Tick size: $0.000025 per MXN = $12.50
  
- **6Z** (South African Rand): `CME:FUTURE:ZAR-USD-{expiry}@LIN`
  - Contract size: ZAR 500,000
  - Tick size: $0.000025 per ZAR = $12.50
  
- **6L** (Brazilian Real): `CME:FUTURE:BRL-USD-{expiry}@LIN`
  - Contract size: BRL 100,000
  - Tick size: $0.0001 per BRL = $10.00

### CME Options

**Instrument ID Format**:
```
CME:OPTION:SP500-USD-241225-4500-CALL@LIN
CME:OPTION:SP500-USD-241225-4500-PUT@LIN
```

**Option Types**:
- **ES.OPT** (Standard Monthly/Quarterly): `CME:OPTION:SP500-USD-{expiry}-{strike}-{CALL|PUT}@LIN`
- **EW1-5.OPT** (Weekly Friday): `CME:OPTION:SP500-USD-{expiry}-{strike}-{CALL|PUT}@LIN`

**Contract Specifications**:
- Underlying: E-mini S&P 500 futures (ES)
- Contract size: 1 ES futures contract
- Tick size: 0.25 index points = $12.50
- Strike intervals: 25 index points

### IB Symbol Mapping

- Instrument ID `CME:FUTURE:SP500-USD-241225@LIN` → IB symbol `ES` + expiry `20241225`
- Instrument ID `CME:OPTION:SP500-USD-241225-4500-CALL@LIN` → IB symbol `ES` + expiry + strike + type

**Note**: Expiry format `YYMMDD` in instrument ID must be converted to IB format (YYYYMMDD or contract month code).

### Execution Flow

1. Parse instrument ID → venue=`CME`, type=`FUTURE`/`OPTION`, symbol=`SP500-USD-241225`
2. Lookup instrument definition → get:
   - `exchange_raw_symbol` = `ES` (E-mini S&P 500)
   - `contract_size` = 50 (index points × $50)
   - `expiry` = `2024-12-25T08:00:00Z`
3. Convert expiry format: `241225` → IB contract month code or `20241225`
4. Route to Interactive Brokers API
5. Map order type: `LIMIT` → IB `LMT`, `MARKET` → IB `MKT`
6. Execute futures order via IB TWS/IB Gateway
7. Return execution result

---

## CBOE (Cboe Global Markets)

### Venue Information

**Venue Code**: `CBOE`

**Supported Instrument Types**:
- `INDEX` (VIX only)

### Instrument ID Format

```
CBOE:INDEX:VIX-USD
```

### Execution Attributes

- **Data Provider**: Barchart (15-minute OHLCV data)
- **Trading Hours**: 9:30 AM - 4:15 PM ET (weekdays only)
- **Note**: VIX is an index, not a tradable futures/options contract (used for data only)

### Purpose

VIX (Volatility Index) is used for:
- Volatility feature generation for ML models
- Market sentiment analysis
- Risk management indicators

**Note**: VIX itself is not directly tradable. VIX futures and options are traded on CBOE Futures Exchange (CFE), which would use different instrument IDs.

---

## NASDAQ / NYSE

### Venue Information

**Venue Codes**: `NASDAQ`, `NYSE`

**Supported Instrument Types**:
- `EQUITY` (planned)

### Instrument ID Format

```
NASDAQ:EQUITY:AAPL
NYSE:EQUITY:SPY
```

### Execution Attributes

- **Data Provider**: Databento (`DBEQ.BASIC`)
- **Execution**: Planned via Interactive Brokers
- **Status**: ⏳ Planned (not yet implemented)

### Planned Implementation

- Equity trading via Interactive Brokers
- Market data from Databento
- Support for common equities and ETFs

---

## Execution Flow Examples

### Example 1: TradFi Futures via IB

**Input**: Order instruction
```json
{
  "operation_id": "trade_003",
  "operation": "trade",
  "instrument_key": "CME:FUTURE:SP500-USD-241225@LIN",
  "side": "BUY",
  "amount": 1,
  "order_type": "LIMIT",
  "price": 4500.0,
  "expected_deltas": {
    "CME:FUTURE:SP500-USD-241225@LIN": 1
  }
}
```

**Execution Flow**:
1. Parse instrument ID → venue=`CME`, type=`FUTURE`, symbol=`SP500-USD-241225`
2. Lookup instrument definition → get:
   - `exchange_raw_symbol` = `ES` (E-mini S&P 500)
   - `contract_size` = 50 (index points × $50)
   - `expiry` = `2024-12-25T08:00:00Z`
3. Convert expiry format: `241225` → IB contract month code or `20241225`
4. Route to Interactive Brokers API
5. Map order type: `LIMIT` → IB `LMT`
6. Execute futures order via IB TWS/IB Gateway
7. Return execution result

**Output**: Execution response
```json
{
  "execution_id": "exec_003",
  "status": "success",
  "venue": "CME",
  "execution_venue": "INTERACTIVE_BROKERS",
  "instrument_id": "CME:FUTURE:SP500-USD-241225@LIN",
  "ib_order_id": 12345,
  "fills": [
    {
      "price": 4500.0,
      "quantity": 1,
      "timestamp": "2025-01-15T10:30:00Z"
    }
  ],
  "position_deltas": {
    "CME:FUTURE:SP500-USD-241225@LIN": 1
  }
}
```

---

## Smart Execution for TradFi

### TradFi Smart Algo Execution

**Objective**: Optimize execution for CME futures via Interactive Brokers

**Algorithm Types**:

#### TWAP (Time-Weighted Average Price)

- Execute orders evenly over specified time window
- Reduces market impact over time
- Suitable for large orders that need to be spread out

#### VWAP (Volume-Weighted Average Price)

- Execute orders proportional to historical volume profile
- Matches market volume patterns
- Reduces market impact by trading when volume is high

#### Implementation Shortfall

- Minimize difference between decision price and execution price
- Balances urgency vs market impact
- Optimizes execution cost

#### Participation Rate

- Control order size relative to market volume (e.g., 10% participation)
- Limits market impact
- Maintains execution speed while controlling price impact

**Supported Venues**: CME futures via Interactive Brokers (S&P 500, commodities, FX, treasuries)

**Input**: Order with `FUTURE` instrument ID, algo parameters (TWAP/VWAP window, participation rate)

**Output**: Executed order meeting algo objectives (TWAP/VWAP target, implementation shortfall minimization)

### Execution Flow with Smart Algo

```
Order Received (FUTURE, smart_execution_enabled = True)
  ↓
Parse Algo Parameters (TWAP/VWAP/Implementation Shortfall)
  ↓
Query Historical Volume Profile (for VWAP)
  ↓
Calculate Execution Schedule
  ↓
Execute Orders Over Time Window
  ↓
Monitor Fill Progress
  ↓
Adjust Execution Rate Based on Market Conditions
  ↓
Complete Execution
  ↓
Return Execution Results
```

### Tick Data Analysis for TradFi

**Data Source**: Databento (GLBX.MDP3 tick data for CME futures)

**Capabilities**:
- **Real-Time Tick Processing**: Consume tick data streams from Databento
- **Order Book Reconstruction**: Build order book snapshots from tick data
- **Liquidity Analysis**: Assess available liquidity at different price levels
- **Optimal Fill Timing**: Identify time windows with:
  - Higher liquidity
  - Lower volatility
  - Better price levels
- **Market Microstructure**: Analyze bid-ask spreads, order flow, and trade patterns

### Slippage Optimization for TradFi

**Pre-Trade Simulation**:
- Simulate execution based on historical volume patterns
- Calculate expected slippage based on:
  - Order size vs available liquidity
  - Historical slippage patterns
  - Current market conditions
- Estimate market impact for different execution strategies
- Select optimal execution algorithm and parameters

---

## Order Type Mapping

### TradFi Order Types

| System Order Type | Interactive Brokers | Description |
|-------------------|---------------------|-------------|
| `MARKET` | `MKT` | Execute immediately at best available price |
| `LIMIT` | `LMT` | Execute only at specified price or better |
| `STOP` | `STP` | Triggered when price reaches stop price |

### Order Type Details

**Market Orders (`MKT`)**:
- Execute immediately at best available price
- No price guarantee
- Higher slippage risk for large orders

**Limit Orders (`LMT`)**:
- Execute only at specified price or better
- Price guarantee
- May not fill if price moves away

**Stop Orders (`STP`)**:
- Triggered when price reaches stop price
- Executes as market order after trigger
- Used for stop-loss protection

---

## Backtesting for TradFi

### Data Sources

- **Databento**: GLBX.MDP3 tick data for CME futures
- **Data Types**: Trades, order book snapshots, market data
- **Access**: SDK access (when ready, we'll get the latest repo to work off)
- **Headers**: Tick data sample headers haven't changed, so previous code should work

### Execution Simulation

- **Order Book Reconstruction**: Build order book from tick data
- **Slippage Modeling**: Model slippage based on order size and liquidity
- **Fill Price Calculation**: Calculate fill prices using order book depth
- **Realistic Latency**: Model execution timing and latency
- **Algo Execution Simulation**: Simulate TWAP/VWAP/Implementation Shortfall algorithms

### Backtesting Flow

```
Pre-generated Orders (from Strategy Service)
  ↓
Read Orders from GCS
  ↓
Query Tick Data (Databento GLBX.MDP3)
  ↓
Reconstruct Order Book
  ↓
Simulate Execution (with Algo if specified)
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
- **CeFi Venues**: [`01_CEFI_VENUES.md`](./01_CEFI_VENUES.md)
- **DeFi Venues**: [`02_DEFI_VENUES.md`](./02_DEFI_VENUES.md)
- **Sports Betting Venues**: [`04_SPORTS_BETTING_VENUES.md`](./04_SPORTS_BETTING_VENUES.md)





