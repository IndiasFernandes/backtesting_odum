# DeFi Venues - Decentralized Finance (On-Chain Protocols)

> **Related Documentation**:
> - [`00_PROJECT_OVERVIEW.md`](./00_PROJECT_OVERVIEW.md) - System architecture and common concepts
> - [`01_CEFI_VENUES.md`](./01_CEFI_VENUES.md) - CeFi venues
> - [`03_TRADFI_VENUES.md`](./03_TRADFI_VENUES.md) - TradFi venues
> - [`04_SPORTS_BETTING_VENUES.md`](./04_SPORTS_BETTING_VENUES.md) - Sports betting venues

---

## Table of Contents

1. [Overview](#overview)
2. [DEX Protocols (Trading)](#dex-protocols-trading)
3. [Lending Protocols](#lending-protocols)
4. [Staking Protocols](#staking-protocols)
5. [Atomic Transaction Middleware](#atomic-transaction-middleware)
6. [Decentralized Exchanges (Specialized Chains)](#decentralized-exchanges-specialized-chains)
7. [Execution Flow Examples](#execution-flow-examples)
8. [Smart Execution for DeFi](#smart-execution-for-defi)

---

## Overview

Decentralized Finance (DeFi) protocols enable trading, lending, staking, and other financial operations through smart contracts without intermediaries. The execution system routes orders to DeFi venues via on-chain contract calls.

### Implementation Priorities

Based on protocol capabilities and business requirements:

| Priority | Category | Operations | Status | Notes |
|----------|----------|------------|--------|-------|
| **HIGH** | DEX Swaps | Swap (Uniswap, Curve, Balancer) | ⏳ Planned | Primary DeFi integration target. On-chain trade data available. Full backtesting support. |
| **N/A** | CeFi Trading | Buy/Sell (Binance, OKX, Bybit, Deribit) | ✅ Implemented | Already implemented via CeFi venues. Not DeFi. |
| **MEDIUM** | Lending | Borrow/Lend (AAVE, Morpho) | ⏳ Planned | Execution supported. No backtesting. Complex position management. |
| **MEDIUM** | Staking | Stake/Unstake (Lido, EtherFi) | ⏳ Planned | Execution supported. No backtesting. Not core trading functionality. |

**Focus**: Implement DEX swap operations (Uniswap, Curve, Balancer) as the primary DeFi integration with full backtesting support. Lending and staking operations are planned for execution but will not support backtesting.

### Supported Venues

| Category | Venue | Venue Code | Supported Instruments | Status |
|---------|-------|------------|----------------------|--------|
| **DEX** | Uniswap V2/V3/V4 | `UNISWAPV2-ETH`, `UNISWAPV3-ETH`, `UNISWAPV4-ETH` | SPOT_PAIR, POOL | ⏳ Planned |
| **DEX** | Curve | `CURVE-ETH` | SPOT_PAIR, POOL | ⏳ Planned |
| **DEX** | Balancer | `BALANCER-ETH` | POOL | ⏳ Planned |
| **DEX** | CowSwap | `COWSWAP-ETH` | SPOT_PAIR | ⏳ Planned |
| **Lending** | AAVE V3 | `AAVE_V3_ETH` | A_TOKEN, DEBT_TOKEN | ⏳ Planned |
| **Lending** | Morpho | `MORPHO-ETHEREUM` | SUPPLY_TOKEN, DEBT_TOKEN | ⏳ Planned |
| **Staking** | EtherFi | `ETHERFI` | LST | ⏳ Planned |
| **Staking** | Lido | `LIDO` | LST | ⏳ Planned |
| **Middleware** | Instadapp | `INSTADAPP` | Atomic operations | ⏳ Planned |
| **DEX (Chain)** | Hyperliquid | `HYPERLIQUID` | PERPETUAL, SPOT_PAIR | ⏳ Planned |
| **DEX (Chain)** | Aster | `ASTER` | PERPETUAL, SPOT_PAIR | ⏳ Planned |
| **Wallet** | Wallet | `WALLET` | SPOT_ASSET | ⏳ Planned |

### Common Characteristics

- **Chain**: Ethereum mainnet (most protocols), specialized chains (Hyperliquid, Aster)
- **Execution**: On-chain contract calls via Web3
- **Gas Costs**: Variable, must be estimated before execution
- **Slippage**: Must be configured for swaps
- **MEV Protection**: Private mempool recommended for large trades
- **Atomic Transactions**: Supported via Instadapp middleware

---

## DEX Protocols (Trading)

### Uniswap V2/V3/V4

**Venue Codes**: `UNISWAPV2-ETH`, `UNISWAPV3-ETH`, `UNISWAPV4-ETH`

**Supported Instrument Types**:
- `SPOT_PAIR` (trading routes)
- `POOL` (liquidity pools)

**Instrument ID Format**:
```
UNISWAPV3-ETH:SPOT_PAIR:ETH-USDT@ETHEREUM
UNISWAPV3-ETH:POOL:ETH-USDT:3000@ETHEREUM
UNISWAPV3-ETH:POOL:ETH-USDT:500@ETHEREUM
```

**Execution Attributes**:
- **Chain**: Ethereum mainnet (`@ETHEREUM`)
- **Fee Tiers**:
  - V2: 3000 bps (0.3%) implied
  - V3: 100, 500, 3000, 10000 bps (0.01%, 0.05%, 0.3%, 1%)
- **Pool Address**: Stored in `pool_address` attribute
- **Factory Address**: V3 = `0x1F98431c8aD98523631AE4a59f267346ea31F984`
- **Router**: V3 = `0xE592427A0AEce92De3Edee1F18E0157C05861564`

**Execution Requirements**:
- Contract addresses in instrument attributes (`base_asset_contract_address`, `quote_asset_contract_address`, `pool_address`)
- Gas estimation required
- Slippage tolerance configuration
- MEV protection (private mempool recommended)
- Token approval before swap (ERC-20 `approve()`)

**Execution Methods**:
- **V2**: `UniswapV2Router02.swapExactTokensForTokens()`
- **V3**: `SwapRouter.exactInputSingle()` or `exactInput()` for multi-hop
- **V4**: Universal Router with command-based execution

**Data Availability**:
- ✅ On-chain transaction logs (Swap events)
- ✅ Pool reserves for liquidity analysis
- ✅ Historical trade data via The Graph subgraphs
- ✅ Real-time price feeds via oracles

**Atomic Transaction Support**:
- Uniswap Router supports atomic multi-hop swaps
- Can be integrated into flash loan sequences via Instadapp
- All swaps within transaction succeed or fail together

**MVP Instruments**:
- `UNISWAPV3-ETH:SPOT_PAIR:ETH-USDT@ETHEREUM`
- `UNISWAPV3-ETH:SPOT_PAIR:ETH-WSTETH@ETHEREUM`

---

### Curve

**Venue Code**: `CURVE-ETH`

**Supported Instrument Types**:
- `SPOT_PAIR`
- `POOL`

**Instrument ID Format**:
```
CURVE-ETH:SPOT_PAIR:ETH-USDT@ETHEREUM
CURVE-ETH:POOL:ETH-USDT@ETHEREUM
CURVE-ETH:SPOT_PAIR:ETH-WEETH@ETHEREUM
```

**Execution Attributes**:
- **Chain**: Ethereum mainnet
- **Registry Contract**: `0x90E00ACe148ca3b23Ac1bC8C240C2a7Dd9c2d9f5`
- **Pool Types**: Stable pools, crypto pools, metapools
- **Specialization**: Optimized for stablecoin and similar-asset swaps
- **Low Slippage**: Designed for correlated assets

**Execution Methods**:
- `CurvePool.exchange()` for direct swaps
- `CurveRouter.exchange()` for multi-hop routing

**Data Availability**:
- ✅ On-chain Swap events
- ✅ Pool balances and reserves
- ✅ Historical data via Curve subgraphs

**MVP Instruments**:
- `CURVE-ETH:SPOT_PAIR:ETH-USDT@ETHEREUM`
- `CURVE-ETH:SPOT_PAIR:ETH-WEETH@ETHEREUM`

---

### Balancer

**Venue Code**: `BALANCER-ETH`

**Supported Instrument Types**:
- `POOL`

**Instrument ID Format**:
```
BALANCER-ETH:POOL:ETH-USDC@ETHEREUM
```

**Execution Attributes**:
- **Chain**: Ethereum mainnet
- **Vault Contract**: `0xBA12222222228d8Ba445958a75a0704d566BF2C8`
- **Pool Types**: Weighted pools, stable pools, composable pools
- **Flash Loans**: Provides flash loans for atomic transactions (via Instadapp)

**Execution Methods**:
- `Vault.swap()` with SOR-optimized paths
- GraphQL API for route discovery (`https://api-v3.balancer.fi/graphql`)

**Data Availability**:
- ✅ Balancer GraphQL API for route discovery
- ✅ On-chain swap events
- ✅ Pool TVL and liquidity data
- ✅ Smart Order Router (SOR) for optimal path finding

**Advantages**:
- Smart Order Router finds optimal paths automatically
- Supports weighted pools, stable pools, composable pools
- Price impact calculation available via API

---

### CowSwap

**Venue Code**: `COWSWAP-ETH`

**Supported Instrument Types**:
- `SPOT_PAIR` (via CoW Protocol)

**Instrument ID Format**:
```
COWSWAP-ETH:SPOT_PAIR:ETH-USDT@ETHEREUM
```

**Execution Attributes**:
- **Chain**: Ethereum mainnet
- **Protocol**: CoW Protocol (Coincidence of Wants)
- **Solver Network**: Off-chain solvers find optimal routes
- **MEV Protection**: Orders submitted off-chain, settled on-chain atomically
- **Gas Optimization**: Solvers optimize gas costs
- **Use Cases**: 
  - Large swaps with MEV protection
  - Complex multi-hop routes
  - **Note**: Cannot be used inside atomic flash loan transactions (off-chain solver submits tx)

**Execution Requirements**:
- Order submission via CoW Protocol API
- Solver network finds optimal execution path
- On-chain settlement via CoW Protocol contract

**Limitation**: CowSwap cannot be used inside atomic flash loan transactions because:
- CowSwap uses off-chain solvers that submit transactions
- Flash loan transactions must complete within single block
- Cannot bundle external solver transaction into atomic sequence

**Alternative**: Use Uniswap, Curve, or 1inch for swaps within atomic transactions

---

## Lending Protocols

> **Important**: Lending operations (borrow, lend, transfer) **cannot be executed via NautilusTrader**. NautilusTrader is designed for trading operations (buy/sell/swap) and does not support DeFi protocol interactions like lending, borrowing, staking, or transfers.
>
> **Status**: These operations are **execution-only** (via smart contracts) and will **not support backtesting**. They require direct smart contract calls and complex position management that NautilusTrader does not handle.
>
> **Focus for backtesting**: DEX swap operations (Uniswap, Curve, Balancer) are the primary DeFi integration with full backtesting support via NautilusTrader.

### AAVE V3

**Venue Code**: `AAVE_V3_ETH`

**Status**: ⏳ **Planned** - Execution supported, no backtesting

**Supported Instrument Types**:
- `A_TOKEN` (supply positions)
- `DEBT_TOKEN` (borrow positions)

**Instrument ID Format**:
```
AAVE_V3_ETH:A_TOKEN:AUSDT@ETHEREUM
AAVE_V3_ETH:A_TOKEN:AWETH@ETHEREUM
AAVE_V3_ETH:DEBT_TOKEN:DEBTWETH@ETHEREUM
```

**Execution Attributes**:
- **Chain**: Ethereum mainnet
- **Pool Contract**: `0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2`
- **Operations**: Supply, withdraw, borrow, repay
- **Interest Rate Model**: Variable rates, updated on-chain
- **Collateral**: Assets supplied can be used as collateral for borrowing
- **Health Factor**: Monitored to prevent liquidation

**Execution Methods**:
- Supply: `supply(asset, amount, onBehalfOf, referralCode)`
- Withdraw: `withdraw(asset, amount, to)`
- Borrow: `borrow(asset, amount, interestRateMode, referralCode, onBehalfOf)`
- Repay: `repay(asset, amount, rateMode, onBehalfOf)`

**Backtesting Support**: ❌ Not supported via NautilusTrader
- **Cannot be done via NautilusTrader**: NautilusTrader does not support DeFi protocol operations (borrow, lend, supply, withdraw)
- Complex position management (collateral ratios, health factors)
- Interest rate tracking required
- Historical data availability constraints
- Requires direct smart contract interactions, not trading operations

**Execution Support**: ✅ Planned (via smart contracts, not NautilusTrader)
- Real-time execution via direct smart contract calls
- Integration with Unified OMS and Position Tracker
- Position tracking and health factor monitoring
- Uses Web3/OnChain middleware, not NautilusTrader adapters

---

### Morpho

**Venue Code**: `MORPHO-ETHEREUM`

**Status**: ⏳ **Planned** - Execution supported, no backtesting

**Supported Instrument Types**:
- `SUPPLY_TOKEN`
- `DEBT_TOKEN`

**Instrument ID Format**:
```
MORPHO-ETHEREUM:SUPPLY_TOKEN:SUPPLYUSDC@ETHEREUM
MORPHO-ETHEREUM:DEBT_TOKEN:DEBTUSDC@ETHEREUM
```

**Execution Attributes**:
- **Chain**: Ethereum mainnet
- **API**: `https://api.morpho.org/graphql`
- **Operations**: Supply, withdraw, borrow, repay
- **Flash Loans**: Morpho provides flash loans for atomic transactions (via Instadapp)
- **Fee**: 0 bps when liquid (best flash loan provider)

**Execution Methods**:
- Supply: `supply(marketParams, assets, shares, onBehalf, data)`
- Borrow: `borrow(marketParams, assets, shares, onBehalf, receiver)`
- Repay: `repay(marketParams, assets, shares, onBehalf, data)`
- Withdraw: `withdraw(marketParams, assets, shares, onBehalf, receiver)`

**Backtesting Support**: ❌ Not supported
- Complex position management similar to AAVE
- Flash loans may be useful for atomic operations

**Execution Support**: ✅ Planned
- Real-time execution via smart contracts
- Flash loan support for atomic operations
- Integration with Unified OMS and Position Tracker

---

## Staking Protocols

> **Important**: Staking operations (stake, unstake) **cannot be executed via NautilusTrader**. NautilusTrader is designed for trading operations (buy/sell/swap) and does not support DeFi staking protocols.
>
> **Status**: These operations are **execution-only** (via smart contracts) and will **not support backtesting**. They require direct smart contract calls and yield tracking that NautilusTrader does not handle.
>
> **Focus for backtesting**: DEX swap operations (Uniswap, Curve, Balancer) are the primary DeFi integration with full backtesting support via NautilusTrader.

### EtherFi

**Venue Code**: `ETHERFI`

**Status**: ⏳ **Planned** - Execution supported, no backtesting

**Supported Instrument Types**:
- `LST` (Liquid Staking Token)

**Instrument ID Format**:
```
ETHERFI:LST:WEETH@ETHEREUM
```

**Execution Attributes**:
- **Chain**: Ethereum mainnet
- **Contract Address**: `0xcd5fe23c85820f7b72d0926fc9b05b43e359b7ee`
- **Operations**: Stake ETH → receive weETH, unstake weETH → receive ETH
- **Exchange Rate**: Dynamic (weETH/ETH ratio)
- **Yield**: Earns staking rewards while maintaining liquidity

**Execution Methods**:
- Stake: `deposit()` with ETH → receive weETH
- Unstake: `withdraw()` with weETH → receive ETH

**Backtesting Support**: ❌ Not supported via NautilusTrader
- **Cannot be done via NautilusTrader**: NautilusTrader does not support staking operations (stake, unstake)
- Not trading operations - staking is a protocol interaction, not a trade
- Yield tracking complexity
- Historical data availability constraints
- Requires direct smart contract interactions, not trading operations

**Execution Support**: ✅ Planned (via smart contracts, not NautilusTrader)
- Real-time execution via direct smart contract calls
- Integration with Unified OMS and Position Tracker
- Position tracking for weETH balances
- Uses Web3/OnChain middleware, not NautilusTrader adapters

---

### Lido

**Venue Code**: `LIDO`

**Status**: ⏳ **Planned** - Execution supported, no backtesting

**Supported Instrument Types**:
- `LST` (Liquid Staking Token)

**Instrument ID Format**:
```
LIDO:LST:STETH@ETHEREUM
LIDO:LST:WSTETH@ETHEREUM
```

**Execution Attributes**:
- **Chain**: Ethereum mainnet
- **stETH Contract**: `0xae7ab96520de3a18e5e111b5eaab095312d7fe84`
- **wstETH Contract**: `0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0`
- **Operations**: 
  - Stake ETH → receive stETH
  - Wrap stETH → receive wstETH (ERC-20 compatible)
- **Exchange Rate**: Dynamic (stETH/ETH ratio increases over time)

**Execution Methods**:
- Stake: `submit()` with ETH → receive stETH
- Unstake: `requestWithdrawals()` → receive ETH after delay (1-5 days)
- Wrap: `wrap()` with stETH → receive wstETH
- Unwrap: `unwrap()` with wstETH → receive stETH

**Backtesting Support**: ❌ Not supported via NautilusTrader
- **Cannot be done via NautilusTrader**: NautilusTrader does not support staking operations (stake, unstake)
- Not trading operations - staking is a protocol interaction, not a trade
- Long withdrawal periods (1-5 days for unstaking)
- Yield tracking complexity
- Historical data availability constraints
- Requires direct smart contract interactions, not trading operations

**Execution Support**: ✅ Planned (via smart contracts, not NautilusTrader)
- Real-time execution via direct smart contract calls
- Integration with Unified OMS and Position Tracker
- Position tracking for stETH/wstETH balances
- Uses Web3/OnChain middleware, not NautilusTrader adapters

---

## Atomic Transaction Middleware

### Instadapp

**Venue Code**: `INSTADAPP`

**Supported Instrument Types**:
- **Middleware**: Not a direct venue, provides atomic transaction orchestration

**Execution Attributes**:
- **Chain**: Ethereum mainnet
- **Purpose**: Atomic transaction middleware for complex multi-step operations
- **Flash Loan Aggregation**: Routes flash loans to best provider (Morpho, Balancer, AAVE)
- **Operations**: 
  - Atomic leveraged staking (flash borrow → stake → supply → borrow → repay)
  - Atomic unwinding (flash borrow → repay → withdraw → unstake → swap → repay)
- **Gas Optimization**: Reduces gas costs vs sequential transactions
- **MEV Protection**: Atomic transactions reduce MEV risk

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

**Execution Flow**:
1. Execution-service receives order with `atomic_group_id`
2. Parse all operations in atomic group
3. Call Instadapp middleware with operation sequence
4. Instadapp orchestrates all operations in single transaction
5. All operations succeed or fail together (atomic guarantee)
6. Return execution result

**Supported Atomic Operations**:
- **Entry Operations**:
  - Leveraged staking (flash borrow → stake → supply → borrow → repay)
  - Leveraged lending (flash borrow → supply → borrow → repay)
- **Exit Operations**:
  - Partial unwind (flash borrow → repay → withdraw → swap → repay)
  - Full unwind (repay → withdraw → unstake → swap)
- **Rebalancing Operations**:
  - LTV adjustment (flash borrow → repay → withdraw → swap → repay)
  - Protocol migration (flash borrow → repay old → supply new → borrow → repay)

---

## Decentralized Exchanges (Specialized Chains)

### Hyperliquid

**Venue Code**: `HYPERLIQUID`

**Supported Instrument Types**:
- `PERPETUAL` (perpetual futures)
- `SPOT_PAIR` (spot trading)

**Instrument ID Format**:
```
HYPERLIQUID:PERPETUAL:BTC-USDC@HYPERLIQUID
HYPERLIQUID:SPOT_PAIR:BTC-USDC@HYPERLIQUID
```

**Execution Attributes**:
- **Chain**: Hyperliquid chain (HyperEVM)
- **API**: `https://api.hyperliquid.xyz`
- **Data Provider**: `hyperliquid_api` (REST API + S3 archive)
- **Quote Currency**: USDC (all perpetuals and spot pairs)
- **Leverage**: Dynamic (1-20x based on open interest)
- **Order Types**: Market, Limit, Stop Loss
- **Fee Structure**: Maker/taker fees based on volume

**MVP Instruments**:
- BTC, ETH, SOL, AVAX, ARB, OP, MATIC, LINK, UNI, AAVE perpetuals

**Execution Requirements**:
- Hyperliquid REST API for order placement
- WebSocket for real-time updates
- S3 archive for historical tick data

**Note**: Chain suffix `@HYPERLIQUID` is required to distinguish from Ethereum-based protocols

---

### Aster

**Venue Code**: `ASTER`

**Supported Instrument Types**:
- `PERPETUAL` (perpetual futures)
- `SPOT_PAIR` (spot trading)

**Instrument ID Format**:
```
ASTER:PERPETUAL:BTC-USDT@ASTER
ASTER:SPOT_PAIR:BTC-USDT@ASTER
```

**Execution Attributes**:
- **Chain**: Aster chain (Polkadot)
- **API**: `https://fapi.asterdex.com`
- **Data Provider**: `aster_api` (REST API)
- **Quote Currency**: USDT (perpetuals), USDT/USDC (spot)
- **Leverage**: Up to 20x
- **Order Types**: Market, Limit, Stop Loss

**MVP Instruments**:
- BTC, ETH, SOL perpetuals

**Execution Requirements**:
- Aster REST API for order placement
- **Note**: Aster not yet supported by CCXT (use direct API)

**Note**: Chain suffix `@ASTER` is required to distinguish from Ethereum-based protocols

---

### Wallet

**Venue Code**: `WALLET`

**Supported Instrument Types**:
- `SPOT_ASSET` (on-chain wallet positions)

**Instrument ID Format**:
```
WALLET:SPOT_ASSET:ETH
WALLET:SPOT_ASSET:USDT
WALLET:SPOT_ASSET:EIGEN
WALLET:SPOT_ASSET:ETHFI
```

**Execution Attributes**:
- **Chain**: Ethereum mainnet (and other chains)
- **Operations**: Balance queries, transfers
- **No Trading**: Wallet is for position tracking, not execution

**Purpose**: Track on-chain wallet balances as positions. Used for position tracking, not for order execution.

---

## Execution Flow Examples

### Example 1: DeFi DEX Swap

**Input**: Order instruction
```json
{
  "operation_id": "swap_001",
  "operation": "swap",
  "instrument_key": "UNISWAPV3-ETH:SPOT_PAIR:ETH-USDT@ETHEREUM",
  "side": "BUY",
  "amount": 1.0,
  "order_type": "MARKET",
  "max_slippage": 0.005,
  "expected_deltas": {
    "WALLET:SPOT_ASSET:ETH": 1.0,
    "WALLET:SPOT_ASSET:USDT": -3000.0
  }
}
```

**Execution Flow**:
1. Parse instrument ID → venue=`UNISWAPV3-ETH`, type=`SPOT_PAIR`, symbol=`ETH-USDT`
2. Lookup instrument definition → get:
   - `base_asset_contract_address` = `0xC02aaA39b223FE8D0A0e5c4F27eAD9083c756Cc2` (WETH)
   - `quote_asset_contract_address` = `0xdAC17F958D2ee523a2206206994597C13D831ec7` (USDT)
   - `pool_address` = `0x...` (or compute from factory + tokens + fee)
3. Route to Uniswap V3 Router contract
4. Estimate gas and slippage
5. Execute swap via router contract: `exactInputSingle()` or `exactInput()`
6. Wait for transaction confirmation
7. Return execution result

**Output**: Execution response
```json
{
  "execution_id": "exec_002",
  "status": "success",
  "venue": "UNISWAPV3-ETH",
  "instrument_id": "UNISWAPV3-ETH:SPOT_PAIR:ETH-USDT@ETHEREUM",
  "transaction_hash": "0x...",
  "gas_used": 150000,
  "gas_price_gwei": 30,
  "position_deltas": {
    "WALLET:SPOT_ASSET:ETH": 1.0,
    "WALLET:SPOT_ASSET:USDT": -3000.0
  }
}
```

### Example 2: DeFi Supply Operation

**Input**: Order instruction
```json
{
  "operation_id": "supply_001",
  "operation": "supply",
  "instrument_key": "AAVE_V3_ETH:A_TOKEN:AUSDT@ETHEREUM",
  "side": "SUPPLY",
  "amount": 10000.0,
  "source_token": "USDT",
  "expected_deltas": {
    "AAVE_V3_ETH:A_TOKEN:AUSDT@ETHEREUM": 10000.0,
    "WALLET:SPOT_ASSET:USDT": -10000.0
  }
}
```

**Execution Flow**:
1. Parse instrument ID → venue=`AAVE_V3_ETH`, type=`A_TOKEN`
2. Lookup AAVE Pool contract address
3. Approve USDT spending (if not already approved)
4. Execute supply via Pool contract: `supply(USDT, 10000.0, onBehalfOf, referralCode)`
5. Wait for transaction confirmation
6. Return execution result with aUSDT position delta

---

## Smart Execution for DeFi

### DeFi Spot Smart Order Routing

**Objective**: Route spot trades across multiple DEX pools to achieve best execution

**What Smart Routing Does**:
- **Pool Discovery**: Queries instruments-service for all available pools for a trading pair (Uniswap V2/V3/V4, Curve, Balancer)
- **Liquidity Analysis**: Assesses pool liquidity depth and current reserves
- **Fee Comparison**: Compares fee tiers across pools (Uniswap: 0.01%, 0.05%, 0.3%, 1%; Curve: variable)
- **Slippage Simulation**: Simulates execution across pools to estimate price impact
- **Optimal Route Selection**: Selects best pool(s) based on:
  - Total execution cost (price + fees + gas)
  - Available liquidity vs order size
  - Price impact estimation
- **Split Execution**: Splits large orders across multiple pools if beneficial
- **Execution**: Routes order to selected pool(s) via appropriate router contracts

**Supported Venues**: Uniswap V2/V3/V4, Curve, Balancer, CowSwap (for non-atomic orders)

**Input**: Order with `SPOT_PAIR` instrument ID, no specific venue specified, `smart_execution_enabled = True`

**Output**: Execution across optimal pool(s) with actual fill prices and gas costs

### Execution Flow with Smart Routing

```
Order Received (SPOT_PAIR, smart_execution_enabled = True)
  ↓
Query All DEX Pools for Pair
  ↓
Analyze Pool Liquidity (Uniswap V2/V3/V4, Curve, Balancer)
  ↓
Simulate Execution Across Pools
  ↓
Calculate Total Cost (Price + Fees + Gas)
  ↓
Select Optimal Pool(s) OR Split Across Pools
  ↓
Execute Swap(s) via Router Contracts
  ↓
Return Execution Results
```

### Gas Estimation

**Requirements**:
- Estimate gas before executing transaction
- Account for gas price volatility
- Set gas limit with buffer (typically 1.2x estimated)
- Monitor gas prices for optimal timing

**Gas Optimization**:
- Batch operations when possible
- Use atomic transactions to reduce total gas
- Select pools with lower gas costs when similar execution cost

### Slippage Protection

**Configuration**:
- Set slippage tolerance in order (`max_slippage`)
- Account for pool liquidity and price impact
- Use oracle prices for validation
- Monitor slippage during execution

**Slippage Calculation**:
- Price impact = (execution_price - oracle_price) / oracle_price
- Total slippage = price_impact + fees
- Reject execution if slippage exceeds tolerance

---

## Related Documentation

- **Project Overview**: [`00_PROJECT_OVERVIEW.md`](./00_PROJECT_OVERVIEW.md)
- **CeFi Venues**: [`01_CEFI_VENUES.md`](./01_CEFI_VENUES.md)
- **TradFi Venues**: [`03_TRADFI_VENUES.md`](./03_TRADFI_VENUES.md)
- **Sports Betting Venues**: [`04_SPORTS_BETTING_VENUES.md`](./04_SPORTS_BETTING_VENUES.md)





