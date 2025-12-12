# Unified Trading System - Project Overview

> **Purpose**: Complete reference for the unified trading system execution layer  
> **Audience**: Execution service implementers, strategy developers, system integrators  
> **Last Updated**: January 2025  
> **Budget**: $6,000 total (remaining) across 4 milestone groups  
> **Timeline**: 8 weeks (2 weeks per milestone group)

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Key Design Principles](#key-design-principles)
3. [Order Schema](#order-schema)
4. [Instrument Specification](#instrument-specification)
5. [Strategy Overviews](#strategy-overviews)
6. [Strategy → Execution Flow](#strategy--execution-flow)
7. [Smart Execution Capabilities](#smart-execution-capabilities)
8. [Atomic Transactions](#atomic-transactions)
9. [Project Timeline](#project-timeline)
10. [Cloud Infrastructure](#cloud-infrastructure)
11. [Backtesting Architecture](#backtesting-architecture)

---

## System Architecture

This unified trading system provides a comprehensive execution layer that routes orders across multiple venue types—centralized exchanges (CeFi), decentralized protocols (DeFi), traditional finance markets (TradFi), and sports betting platforms.

### Core Components

**Strategy Service**:
- Consumes ML predictions, features, and market data
- Maintains position state, risk, and PnL tracking
- Generates unified `Order` instructions with expected position deltas
- Assumes **perfect execution** (no slippage) for strategy backtesting

**Execution Service**:
- Receives unified `Order` instructions from strategy-service
- Routes orders based on `operation` type and `instrument_key`
- Applies smart execution algorithms if `smart_execution_enabled = True`
- Returns execution results with actual fills and position deltas

### Venue Categories

| Category | Venues | Instrument Types | Status |
|----------|--------|------------------|--------|
| **CeFi** | Binance, Bybit, OKX, Deribit | SPOT_PAIR, PERPETUAL, FUTURE, OPTION | ✅ Implemented |
| **DeFi** | Uniswap, CowSwap, AAVE, Morpho, Instadapp, Lido, EtherFi, Hyperliquid, Aster | SPOT_PAIR, POOL, A_TOKEN, DEBT_TOKEN, LST, PERPETUAL | ⏳ Planned |
| **TradFi** | CME (via IB), CBOE, NASDAQ, NYSE | FUTURE, OPTION, INDEX, EQUITY | ⏳ Planned |
| **Sports** | Betfair | MATCH_WINNER, TOTAL_GOALS_OU_2_5, BTTS | ⏳ Planned |

---

## Key Design Principles

### Canonical Instrument IDs

Stable identifiers used across all services that encode venue, instrument type, and market specifications.

**Format**: `[ASSET_CLASS:]VENUE:INSTRUMENT_TYPE:PAYLOAD[@CHAIN]`

**Examples**:
- `BINANCE-SPOT:SPOT_PAIR:BTC-USDT` (CeFi spot trading route)
- `UNISWAPV3-ETH:POOL:ETH-USDT:3000@ETHEREUM` (DeFi pool)
- `CME:FUTURE:SP500-USD-241225@LIN` (TradFi future)
- `FOOTBALL:BETFAIR:MATCH_WINNER:ENG-PREMIER_LEAGUE:20250315T1500:ARSENAL-LIVERPOOL` (Sports betting)

### Routing-Agnostic Strategy Layer

Strategies generate orders without specifying exact venues, allowing dynamic routing:
- **SPOT_PAIR**: Used for routing only (e.g., `BINANCE-SPOT:SPOT_PAIR:BTC-USDT`)
  - Never stored as a position
  - Execution service finds best venue/pool for this pair
- **SPOT_ASSET**: Represents actual holdings (e.g., `BINANCE-SPOT:SPOT_ASSET:BTC`)
  - Stored as positions after trade execution
  - Used in `expected_deltas` keys

### Execution-Dynamic Routing

Execution service selects optimal venues/pools at runtime based on:
- Expected slippage
- Trading fees
- Gas costs (for DeFi)
- Venue health and latency
- Available liquidity

### Venue-Bound Derivatives

Perpetuals and futures are non-fungible across venues:
- Instrument ID directly maps to execution venue
- No routing decision needed
- Position tracking matches execution routing

### Perfect Execution Assumption

- **Strategy Service**: Assumes perfect execution (no slippage) for backtesting
- **Execution Service**: Provides realistic execution simulation with slippage modeling

---

## Order Schema

### Order Structure

```python
Order(
    # Core identification
    operation_id: str,  # Unique operation identifier
    operation: Literal["trade", "supply", "borrow", "stake", "withdraw", "swap", "transfer", "bet"],
    
    # Instrument identification (routing vs positions)
    instrument_key: str,  # Canonical instrument ID
    # For routing: Use SPOT_PAIR (e.g., "BINANCE-SPOT:SPOT_PAIR:BTC-USDT")
    # For positions: Use SPOT_ASSET (e.g., "BINANCE-SPOT:SPOT_ASSET:BTC")
    # For derivatives: Use PERPETUAL/FUTURE/OPTION (venue-bound, non-fungible)
    
    # Venue information
    venue: Optional[str],  # Optional for SPOT_PAIR (allows smart routing), required for derivatives
    source_venue: Optional[str],  # For transfers
    target_venue: Optional[str],  # For transfers
    
    # Trading parameters
    side: Literal["BUY", "SELL", "SUPPLY", "BORROW", "STAKE", "WITHDRAW", "BACK", "LAY"],
    amount: float,  # Order amount (or stake for sports betting)
    price: Optional[float],  # Limit price (for limit orders)
    
    # Sports betting specific (when operation == "bet")
    odds: Optional[float],  # Required for sports betting (BACK/LAY odds)
    selection: Optional[str],  # Required for MATCH_WINNER (Home/Draw/Away)
    
    # Token information (for DeFi operations)
    source_token: Optional[str],  # Source token (e.g., "BTC", "USDT")
    target_token: Optional[str],  # Target token (e.g., "USDT", "aUSDT")
    
    # Smart contract parameters (for DeFi)
    contract_address: Optional[str],  # Smart contract address
    function_name: Optional[str],  # Contract function name
    function_params: Optional[Dict[str, Any]],  # Function parameters
    
    # Expected position deltas (SPOT_ASSET positions, not SPOT_PAIR)
    expected_deltas: Dict[str, float],  # instrument_key -> delta
    # Keys must be SPOT_ASSET instrument IDs (e.g., "BINANCE-SPOT:SPOT_ASSET:BTC")
    # Values are position deltas (positive = long, negative = short)
    
    # Execution preferences
    max_slippage: Optional[float],  # Max slippage tolerance (bps or decimal)
    urgency: Optional[Literal["low", "medium", "high"]],  # Execution urgency
    smart_execution_enabled: bool = False,  # Enable smart routing/algo execution
    
    # Risk management
    take_profit_price: Optional[float],  # Take profit price
    stop_loss_price: Optional[float],  # Stop loss price
    
    # Execution coordination
    atomic_group_id: Optional[str],  # Atomic group ID for multi-step operations
    sequence_in_group: Optional[int],  # Sequence within atomic group
    priority: Optional[int],  # Execution priority (higher = more urgent)
    
    # Strategy metadata
    strategy_id: Optional[str],  # Strategy identifier
    strategy_intent: Optional[str],  # Strategy intent (entry_full, exit_partial, etc.)
    
    # Additional metadata
    metadata: Optional[Dict[str, Any]]  # Additional order metadata
)
```

### Key Design Principles

1. **Routing Instruments vs Position Instruments**:
   - **SPOT_PAIR**: Used for routing only, never stored as a position
   - **SPOT_ASSET**: Represents actual holdings, stored as positions
   - **PERPETUAL/FUTURE/OPTION**: Venue-bound, non-fungible

2. **Sports Betting Orders**:
   - `operation: "bet"` for all sports betting orders
   - `side: "BACK"` or `"LAY"` (Betfair terminology)
   - `amount`: Stake amount (notional)
   - `odds`: Required - current odds at time of order
   - `selection`: Required for MATCH_WINNER (Home/Draw/Away)

3. **DeFi Operations**:
   - `operation`: "supply", "borrow", "stake", "withdraw", "swap"
   - `instrument_key`: Protocol instrument ID
   - `source_token`/`target_token`: Token codes for swaps
   - `contract_address`/`function_name`: For direct contract calls

4. **Atomic Operations**:
   - `atomic_group_id`: Groups operations that must execute together
   - `sequence_in_group`: Order of execution within atomic group
   - All operations in group succeed or fail together

---

## Instrument Specification

### Canonical Format

**Grammar (BNF-style)**:

```
<instrument-id> ::= [<asset-class> ":"] <venue> ":" <type> ":" <payload> ["@" <chain>]

<asset-class>  ::= FOOTBALL | CEFI | DEFI | COMMODITIES | EQUITY-INDEX | EQUITY | BOND | FX
                  # Optional prefix to categorize instrument by asset class

<venue>        ::= UPPER_ALNUM_DASH
<type>         ::= SPOT_ASSET | SPOT_PAIR | PERPETUAL | FUTURE | OPTION | POOL | LST | A_TOKEN | DEBT_TOKEN | EQUITY | INDEX | MATCH_WINNER | TOTAL_GOALS | BTTS
```

### Instrument Types Summary

| Type | Purpose | Example |
|------|---------|---------|
| **SPOT_ASSET** | Actual asset positions held on a venue | `BINANCE-SPOT:SPOT_ASSET:BTC` |
| **SPOT_PAIR** | Trading routes for execution routing | `BINANCE-SPOT:SPOT_PAIR:BTC-USDT` |
| **PERPETUAL** | Perpetual futures contracts (no expiry) | `BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN` |
| **FUTURE** | Dated futures contracts (with expiry) | `DERIBIT:FUTURE:BTC-USD-241225@INV` |
| **OPTION** | Options contracts (with expiry and strike) | `DERIBIT:OPTION:BTC-USD-241225-50000-CALL@INV` |
| **POOL** | DeFi DEX liquidity pools | `UNISWAPV3-ETH:POOL:ETH-USDT:3000@ETHEREUM` |
| **LST** | Liquid Staking Tokens | `ETHERFI:LST:WEETH@ETHEREUM` |
| **A_TOKEN** | AAVE lending positions (supply tokens) | `AAVE_V3_ETH:A_TOKEN:AUSDT@ETHEREUM` |
| **DEBT_TOKEN** | AAVE borrowing positions (debt tokens) | `AAVE_V3_ETH:DEBT_TOKEN:DEBTWETH@ETHEREUM` |
| **MATCH_WINNER** | Sports betting match winner market (1X2) | `FOOTBALL:BETFAIR:MATCH_WINNER:ENG-PREMIER_LEAGUE:20250315T1500:ARSENAL-LIVERPOOL` |
| **TOTAL_GOALS_OU_2_5** | Over/Under 2.5 goals market | `FOOTBALL:BETFAIR:TOTAL_GOALS_OU_2_5:ENG-PREMIER_LEAGUE:20250315T1500:ARSENAL-LIVERPOOL@2.5` |
| **BTTS** | Both Teams To Score market (YES/NO) | `FOOTBALL:BETFAIR:BTTS:ENG-PREMIER_LEAGUE:20250315T1500:ARSENAL-LIVERPOOL` |

### Instrument ID Examples

**CeFi**:
```
BINANCE-SPOT:SPOT_PAIR:BTC-USDT
BINANCE-FUTURES:PERPETUAL:ETH-USDT@LIN
DERIBIT:OPTION:BTC-USD-241225-50000-CALL@INV
```

**DeFi**:
```
UNISWAPV3-ETH:POOL:ETH-USDT:3000@ETHEREUM
AAVE_V3_ETH:A_TOKEN:AUSDT@ETHEREUM
ETHERFI:LST:WEETH@ETHEREUM
```

**TradFi**:
```
CME:FUTURE:SP500-USD-241225@LIN
CME:OPTION:SP500-USD-241225-4500-CALL@LIN
CBOE:INDEX:VIX-USD
```

**Sports Betting**:
```
FOOTBALL:BETFAIR:MATCH_WINNER:ENG-PREMIER_LEAGUE:20250315T1500:ARSENAL-LIVERPOOL
FOOTBALL:BETFAIR:TOTAL_GOALS_OU_2_5:GER-BUNDESLIGA:20250316T1430:BAYERN-MUNICH-BORUSSIA-DORTMUND@2.5
```

### Instrument Attributes Schema

**Standard Attributes**:
- `venue`: Venue code (e.g., `BINANCE-SPOT`)
- `instrument_type`: Canonical type (e.g., `SPOT_PAIR`)
- `exchange_raw_symbol`: Native exchange symbol (e.g., `BTCUSDT` for Binance)
- `ccxt_symbol`: CCXT-compatible symbol (if applicable)
- `base_asset`: Base asset code (e.g., `BTC`)
- `quote_asset`: Quote asset code (e.g., `USDT`)
- `settle_asset`: Settlement asset (for derivatives)
- `chain`: Chain identifier: `"off-chain"` for CeFi/TradFi, chain name for DeFi
- `expiry`: Optional[datetime] - Precise UTC datetime
- `strike`: Optional[str] - Strike price (as string)
- `option_type`: Optional["CALL","PUT"] - Option type
- `contract_size`: Optional[float] - Contract size
- `tick_size`: Optional[float] - Tick size
- `min_size`: Optional[float] - Minimum order size
- `inverse`: Optional[bool] - Whether instrument is inverse

**DeFi-Specific Attributes**:
- `base_asset_contract_address`: Optional[str] - ERC-20 contract address
- `quote_asset_contract_address`: Optional[str] - ERC-20 contract address
- `pool_address`: Optional[str] - Pool contract address
- `pool_fee_tier`: Optional[int] - Pool fee in basis points
- `factory_address`: Optional[str] - Factory contract address
- `chain_id`: Optional[int] - Chain ID (1 = Ethereum mainnet)

---

## Strategy Overviews

The unified trading system supports five strategy types, each targeting different market opportunities:

### Delta-One ML Strategy

**Status**: ✅ MVP Complete, going live

**Objective**: ML-based trading using delta-one features and ML predictions

**What It Does**:
- Uses delta-one features (price, volume, technical indicators) + ML model predictions
- Generates trading signals for spot pairs and perpetual futures
- Targets: Crypto CEX markets (Binance, Bybit, OKX)
- ML models predict price movements, strategy generates buy/sell orders

**Execution Integration**:
- Strategy generates `trade` orders with `SPOT_PAIR` or `PERPETUAL` instrument IDs
- Execution routes to CEX venues (Binance, Bybit, OKX)
- Supports smart execution for optimal fill timing

---

### DeFi Strategy

**Status**: ✅ Will go live (Week 5-6)

**Objective**: Yield generation through staking, lending, and basis trading using on-chain features

**What It Does**:
- Monitors on-chain lending rates (AAVE), staking yields (Lido, EtherFi), and DEX liquidity
- Generates orders for: `supply`, `borrow`, `stake`, `withdraw`, `swap` operations
- Targets: DeFi protocols (AAVE, EtherFi, Lido, Uniswap, Curve)
- Optimizes yield across lending/staking opportunities

**Execution Integration**:
- Strategy generates DeFi operation orders (`supply`, `borrow`, `stake`, etc.)
- Execution routes to OnChain middleware for protocol interactions
- Supports atomic operation groups (e.g., supply + borrow in one transaction)

**Important Note**: 
- **Swap operations** (`swap`) can be backtested via NautilusTrader using on-chain trade data
- **Lending/staking operations** (`supply`, `borrow`, `stake`, `withdraw`, `transfer`) **cannot be backtested via NautilusTrader** - they are execution-only via smart contracts
- NautilusTrader is designed for trading operations (buy/sell/swap), not DeFi protocol interactions

---

### TradFi Strategy

**Status**: ✅ Active development (Week 7-8), will go live

**Objective**: Delta-one trading with volatility-enhanced ML pricing for traditional finance markets

**What It Does**:
- Combines delta-one features + volatility features → ML predictions
- Generates trading signals for CME futures (equity indices, commodities, FX, treasuries)
- Targets: CME futures and options via Interactive Brokers
- Uses volatility features to enhance pricing accuracy

**Execution Integration**:
- Strategy generates `trade` orders with `FUTURE` or `OPTION` instrument IDs
- Execution routes to Interactive Brokers for CME execution
- Data provider: Databento (GLBX.MDP3), Execution provider: Interactive Brokers

---

### Options Strategy

**Status**: ⏳ Structure phase (data infrastructure, instrument definitions)

**Objective**: Options target position trading using volatility features and surfaces

**What It Does**:
- Uses volatility features (25 delta skew, ATM vol) + options chain data
- Generates covered call strategies and delta-alternative trades
- Targets: Crypto options (Deribit), TradFi options (CME)
- Three use cases:
  1. **Covered Call Strategy**: Generate yield via call options
  2. **ML Features**: Volatility features assist ML delta-one predictions
  3. **Delta Alternative**: Trade options instead of futures for capped downside

**Execution Integration**:
- Strategy generates `trade` orders with `OPTION` instrument IDs
- Execution routes to Deribit (crypto) or Interactive Brokers (TradFi)
- Options chain data from market-data-processing-service

---

### Sports Betting Strategy

**Status**: ⏳ Planned (post 10-week sprint)

**Objective**: Value betting using ML predictions vs market odds

**What It Does**:
- Uses sports features (team strength, form, xG, market microstructure) + ML predictions
- Compares predicted probability vs implied probability from Betfair odds
- Generates bet orders (`BACK` or `LAY`) with Kelly criterion stake sizing
- Targets: Betfair Exchange (football markets: Match Winner, Over/Under, BTTS)

**Execution Integration**:
- Strategy generates `bet` orders with `MATCH_WINNER`, `TOTAL_GOALS_OU_2_5`, or `BTTS` instrument IDs
- Execution routes to BetfairMiddlewareAdapter
- Orders include: `side` (`BACK`/`LAY`), `stake`, `odds`, `selection` (Home/Draw/Away)

---

## Strategy → Execution Flow

### Order Reception (Execution Service)

**Routing Decision Tree**:
```
IF operation == "trade" AND instrument_key is SPOT_PAIR:
    IF smart_execution_enabled == True:
        → Apply smart order routing (DeFi) or smart algo (CeFi)
        → For DeFi: Query all DEX pools, simulate slippage, select optimal pool(s)
        → For CeFi: Apply TWAP, venue selection, order splitting
    ELSE:
        → Query instruments-service for all venues with this pair
        → Simulate slippage across CEX + DEX pools
        → Select best execution venue/pool
    → Route to CEXMiddlewareAdapter OR DEXMiddlewareAdapter

ELIF operation == "trade" AND instrument_key is PERPETUAL/FUTURE/OPTION:
    IF smart_execution_enabled == True:
        → Apply smart algo execution (TWAP, VWAP, implementation shortfall)
        → For TradFi: Use algo parameters from order
        → For CeFi: Apply order splitting and optimal timing
    → Extract venue from instrument_key
    → Route directly to venue-specific middleware
    → No routing decision needed (non-fungible)

ELIF operation in ["supply", "borrow", "stake", "withdraw"]:
    → Extract venue from instrument_key
    → Route to OnChainMiddlewareAdapter
    → Execute protocol operation

ELIF operation == "swap":
    → Extract venue from instrument_key (DEX)
    → Route to DEXMiddlewareAdapter
    → Execute swap via router contract

ELIF operation == "bet":
    → Extract venue from instrument_key (BETFAIR)
    → Route to BetfairMiddlewareAdapter
    → Execute BACK/LAY order with odds, selection, stake
    → Position delta: Create SPOT_ASSET position for bet outcome

ELIF operation == "transfer":
    → Route to TransferMiddlewareAdapter
    → Handle wallet/protocol transfers
```

### Live Execution Integration Points

**1. Strategy Service → Execution Service**:
- **Batch Mode**: Strategy writes orders to GCS, execution-service reads from GCS
- **Live Mode**: Strategy-service sends orders via API/gRPC to execution-service
- Orders include `expected_deltas` for position tracking

**2. Execution Service → Venue APIs**:
- **CeFi**: Direct API calls to Binance, Bybit, OKX, Deribit
- **DeFi**: On-chain contract calls via Web3 (Uniswap Router, AAVE Pool, etc.)
- **TradFi**: Interactive Brokers TWS/IB Gateway API
- **Sports**: Betfair Exchange API

**3. Execution Results → Strategy Service**:
- Execution returns actual fills with prices, quantities, timestamps
- Position deltas update strategy-service position tracking
- Strategy-service recalculates PnL with actual execution prices

---

## Smart Execution Capabilities

Smart execution algorithms optimize order execution to minimize slippage, reduce market impact, and improve fill prices. These capabilities are integrated into the execution-service (not separate repo).

### DeFi Spot Smart Order Routing

**Objective**: Route spot trades across multiple DEX pools to achieve best execution

**What to Build**:
- **Pool Discovery**: Query instruments-service for all available pools for a given trading pair (Uniswap V2/V3/V4, Curve, Balancer)
- **Liquidity Analysis**: Assess pool liquidity depth and current reserves
- **Fee Comparison**: Compare fee tiers across pools (Uniswap: 0.01%, 0.05%, 0.3%, 1%; Curve: variable)
- **Slippage Simulation**: Simulate execution across pools to estimate price impact
- **Optimal Route Selection**: Select best pool(s) based on:
  - Total execution cost (price + fees + gas)
  - Available liquidity vs order size
  - Price impact estimation
- **Split Execution**: Split large orders across multiple pools if beneficial
- **Execution**: Route order to selected pool(s) via appropriate router contracts

**Supported Venues**: Uniswap V2/V3/V4, Curve, Balancer, CowSwap (for non-atomic orders)

---

### CeFi Smart Algo Execution

**Objective**: Optimize execution for crypto CEX venues (Binance, Bybit, OKX)

**What to Build**:
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

---

### TradFi Smart Algo Execution

**Objective**: Optimize execution for CME futures via Interactive Brokers

**What to Build**:
- **TWAP (Time-Weighted Average Price)**: Execute orders evenly over specified time window
- **VWAP (Volume-Weighted Average Price)**: Execute orders proportional to historical volume profile
- **Implementation Shortfall**: Minimize difference between decision price and execution price
- **Participation Rate**: Control order size relative to market volume (e.g., 10% participation)
- **Price Improvement**: Use limit orders with price improvement logic
- **Market Impact Modeling**: Estimate price impact based on order size and historical data

**Supported Venues**: CME futures via Interactive Brokers (S&P 500, commodities, FX, treasuries)

---

### Tick Data Analysis

**What to Build**:
- **Real-Time Tick Processing**: Consume tick data streams from Tardis (CeFi) and Databento (TradFi)
- **Order Book Reconstruction**: Build order book snapshots from tick data
- **Liquidity Analysis**: Assess available liquidity at different price levels
- **Optimal Fill Timing**: Identify time windows with:
  - Higher liquidity
  - Lower volatility
  - Better price levels
- **Market Microstructure**: Analyze bid-ask spreads, order flow, and trade patterns

**Data Sources**:
- **CeFi**: Tardis WebSocket streams (real-time) and S3 archive (historical)
- **TradFi**: Databento GLBX.MDP3 streams (real-time) and historical data

---

### Slippage Optimization

**What to Build**:
- **Pre-Trade Simulation**: Simulate execution across venues/pools before placing order
- **Slippage Estimation**: Calculate expected slippage based on:
  - Order size vs available liquidity
  - Historical slippage patterns
  - Current market conditions
- **Venue Comparison**: Compare expected slippage across venues for same instrument
- **Execution Cost Model**: Total cost = price impact + fees + gas (for DeFi)
- **Optimal Venue Selection**: Select venue/pool with lowest total execution cost

---

### TP/SL Monitoring

**What to Build**:
- **Real-Time Price Monitoring**: Monitor market prices for positions with TP/SL orders
- **Order Triggering**: Automatically place market/limit orders when TP/SL levels hit
- **Partial Fills**: Support partial TP orders (e.g., close 50% at TP1, 50% at TP2)
- **Trailing Stop Loss**: Dynamic stop loss that trails price movements
- **Order Management**: Cancel/modify TP/SL orders based on position changes

**Integration**: Works with all venue types (CeFi, DeFi, TradFi)

---

## Atomic Transactions

### Overview

Atomic transactions are critical for DeFi strategies that require multiple protocol interactions to succeed or fail together. All operations within an atomic transaction execute in a single on-chain transaction, ensuring no partial state changes.

### Atomic Transaction Guarantees

- **All-or-Nothing**: All operations succeed together or all fail together
- **No Partial State**: No intermediate state visible to other transactions
- **MEV Protection**: Reduces front-running risk (operations hidden until execution)
- **Gas Efficiency**: Single transaction vs multiple sequential transactions

### Flash Loan Pattern

**Purpose**: Create leveraged positions atomically without requiring upfront capital

**Providers**:
- **Morpho**: Flash loans via Instadapp (0 bps when liquid)
- **Balancer**: Flash loans via Instadapp (0 bps when liquid)
- **AAVE**: Direct flash loans (~5 bps fee)

**Execution Flow** (Leveraged Staking Example):
```
1. FLASH_BORROW WETH from Morpho (via Instadapp)
2. STAKE WETH → receive LST (weETH/wstETH) at EtherFi/Lido
3. SUPPLY LST to AAVE as collateral
4. BORROW WETH from AAVE (up to target_ltv)
5. FLASH_REPAY WETH to Morpho
```

**Leverage Math**:
- Equity E, Target LTV λ
- Flash amount F = (λ/(1-λ)) × E
- Supply S = E + F
- Borrow B = F (must equal flash amount to repay)

**Result**: Leveraged position created in single transaction (~0.7-1.2M gas vs 15M+ for sequential loops)

### Instadapp Middleware Integration

**Role**: Orchestrates atomic multi-step operations across protocols

**Capabilities**:
- Flash loan aggregation (routes to best provider: Morpho, Balancer, AAVE)
- Protocol connector integration (AAVE, EtherFi, Lido, Uniswap)
- Gas optimization (single transaction vs multiple)
- Atomic guarantee enforcement

**Integration Pattern**:
```python
# Execution-service calls Instadapp middleware
instadapp.execute_atomic_operation(
    operations=[
        {"type": "flash_borrow", "asset": "WETH", "amount": F},
        {"type": "stake", "protocol": "etherfi", "amount": F},
        {"type": "supply", "protocol": "aave", "asset": "weETH", "amount": S},
        {"type": "borrow", "protocol": "aave", "asset": "WETH", "amount": B},
        {"type": "flash_repay", "asset": "WETH", "amount": F}
    ]
)
```

### Atomic Unwinding Pattern

**Purpose**: Partially unwind leveraged positions while maintaining LTV

**Execution Flow** (Partial Cash-Out):
```
1. FLASH_BORROW WETH = R (repay slice)
2. AAVE REPAY WETH = R → new debt D' = D - R
3. AAVE WITHDRAW weETH worth W$ = R/λ
4. SWAP weETH → WETH (for flash repay)
5. SWAP excess weETH → USDT (cash out)
6. FLASH_REPAY WETH = R
```

**Key Constraint**: Flash loan is WETH, collateral is weETH → swap required before repayment

**Swap Venue**: Use Uniswap/Curve/1inch inside atomic transaction (NOT CowSwap - off-chain solver)

### Supported Atomic Operations

**Entry Operations**:
- Leveraged staking (flash borrow → stake → supply → borrow → repay)
- Leveraged lending (flash borrow → supply → borrow → repay)

**Exit Operations**:
- Partial unwind (flash borrow → repay → withdraw → swap → repay)
- Full unwind (repay → withdraw → unstake → swap)

**Rebalancing Operations**:
- LTV adjustment (flash borrow → repay → withdraw → swap → repay)
- Protocol migration (flash borrow → repay old → supply new → borrow → repay)

### Execution Requirements

**Gas Estimation**:
- Estimate total gas for all operations
- Account for gas price volatility
- Set gas limit with buffer (typically 1.2x estimated)

**Slippage Protection**:
- Set slippage tolerance for swaps within atomic transaction
- Account for pool liquidity and price impact
- Use oracle prices for validation

**Health Factor Checks**:
- Verify AAVE health factor after atomic operation
- Ensure LTV remains within target range
- Check liquidation thresholds

**Error Handling**:
- If any operation fails, entire transaction reverts
- No partial state changes
- Return clear error messages for debugging

### CowSwap Limitation

**Important**: CowSwap cannot be used inside atomic flash loan transactions because:
- CowSwap uses off-chain solvers that submit transactions
- Flash loan transactions must complete within single block
- Cannot bundle external solver transaction into atomic sequence

**Alternative**: Use Uniswap, Curve, or 1inch for swaps within atomic transactions

---

## Project Timeline

### Overall Timeline

**Duration**: 8 weeks total (2 weeks per milestone group)

**Budget**: $6,000 total (remaining) - $1,500 per milestone group (paid upon completion)

**Milestone Structure**: 4 milestone groups, each with backtest and live implementations (both on cloud)

### Milestone 1 (Weeks 1-2): CEFI - Centralized Finance (Crypto Exchanges)

- **Backtest**: Cloud-based backtesting for CeFi venues (Binance, Bybit, OKX, Deribit)
- **Live**: Cloud-based live execution for CeFi venues
- **Deliverables**: Move signals and real signals
- Backtesting infrastructure operational
- Basic execution routing for CeFi venues
- Smart algo execution for crypto (TWAP, venue selection, order splitting)

### Milestone 2 (Weeks 3-4): DEFI - Decentralized Finance (On-Chain Protocols)

- **Backtest**: Cloud-based backtesting for DeFi protocols
- **Live**: Cloud-based live execution for DeFi protocols
- **Deliverables**: Move signals and real signals
- DeFi protocol integration (Uniswap, CowSwap, AAVE, Morpho, Instadapp, Lido, EtherFi, Hyperliquid, Aster)
- Smart order routing for DeFi spot trades
- Atomic transaction support (Instadapp integration)

### Milestone 3 (Weeks 5-6): TRADFI - Traditional Finance (CME Futures via IB)

- **Backtest**: Cloud-based backtesting for CME futures
- **Live**: Cloud-based live execution via Interactive Brokers
- **Deliverables**: Move signals and real signals
- Interactive Brokers integration for CME futures
- Smart algo execution for TradFi (TWAP, VWAP, implementation shortfall)
- S&P 500 futures execution live

### Milestone 4 (Weeks 7-8): SPORTS - Sports Betting (Betfair Exchange)

- **Backtest**: Cloud-based backtesting for sports betting
- **Live**: Cloud-based live execution for Betfair Exchange
- **Deliverables**: Move signals and real signals
- Betfair Exchange integration
- Sports betting order execution (BACK/LAY orders)
- Match outcome position tracking

---

## Cloud Infrastructure

### Storage System

**Storage System**: Google Cloud Storage (GCS)

**Key Requirements**:
- **Day-Based Chunking**: All data must be organized by day chunks for efficient processing
- **File System Path Structure**: GCS paths look like file system paths, so if it works on local file system split into per-day data, it will work on GCS
- **Schema Design**: You need to make your own schema for what you want to write to cloud (headers, types, and groupings for different clusters of data)

### Data Clusters

1. **Orders**: Pre-generated orders from strategy service
2. **Execution Results**: Actual fills, prices, timestamps from execution service
3. **Signals**: Move signals (strategy predictions) and real signals (executed trades)
4. **Tick Data**: Historical tick data for backtesting (read-only, from Tardis/Databento)

### Tick Data Retrieval

- **CeFi**: Tardis API (historical tick data for Binance, Bybit, OKX)
- **TradFi**: Databento (GLBX.MDP3 tick data for CME futures)
- **SDK Access**: Tick data is accessed through an SDK (when ready to go, we'll get the latest repo to work off)
- **Headers**: The tick data sample hasn't changed in terms of headers, so if you already used the previous code to read in tick data, you're good

### Cloud Server Deployment

- **Setup Chat with Femi**: When it's nearing time to deploy, we should setup a chat with Femi for cloud server deployment
- **Pre-Deployment**: Focus on getting local file system implementation working first; cloud migration will be straightforward once local is working

---

## Backtesting Architecture

### Critical Timeline

Backtesting infrastructure must be operational for each milestone group (2 weeks per group):
- **Milestone 1 (CEFI)**: All CeFi venues (Binance, Bybit, OKX) with tick data
- **Milestone 2 (DEFI)**: DeFi protocols with on-chain data
- **Milestone 3 (TRADFI)**: CME futures via Interactive Brokers with tick data
- **Milestone 4 (SPORTS)**: Sports betting markets with historical odds data

### Backtesting Architecture

- **Separate from Strategy Execution**: Strategy-service pre-generates orders and writes to GCS
- **Execution-Service Backtesting**: Reads pre-generated orders from GCS and executes against tick data
- **Tick Data Sources**:
  - **CeFi**: Tardis (historical tick data for Binance, Bybit, OKX)
  - **TradFi**: Databento (GLBX.MDP3 tick data for CME futures)
- **Execution Simulation**: 
  - Order book reconstruction from tick data
  - Slippage modeling based on order size and liquidity
  - Fill price calculation using order book depth
  - Realistic latency and execution timing

### Testing Approach

- **No Testnet**: All testing uses small capital on mainnet
- **Small Capital Testing**: Use minimal amounts for live validation
- **Backtest First**: Validate execution logic via backtesting before live deployment

---

## Related Documentation

- **CeFi Venues**: [`01_CEFI_VENUES.md`](./01_CEFI_VENUES.md)
- **DeFi Venues**: [`02_DEFI_VENUES.md`](./02_DEFI_VENUES.md)
- **TradFi Venues**: [`03_TRADFI_VENUES.md`](./03_TRADFI_VENUES.md)
- **Sports Betting Venues**: [`04_SPORTS_BETTING_VENUES.md`](./04_SPORTS_BETTING_VENUES.md)





