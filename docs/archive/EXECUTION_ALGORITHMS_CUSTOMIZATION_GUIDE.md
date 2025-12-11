# Execution Algorithms Customization Guide

## Overview

This guide explains how to edit, customize, and create execution algorithms for better order execution in your backtesting system.

## Table of Contents

1. [Understanding Execution Algorithms](#understanding-execution-algorithms)
2. [File Structure](#file-structure)
3. [Editing Existing Algorithms](#editing-existing-algorithms)
4. [Creating New Algorithms](#creating-new-algorithms)
5. [Key Customization Points](#key-customization-points)
6. [Best Practices](#best-practices)
7. [Testing Your Changes](#testing-your-changes)
8. [Advanced Techniques](#advanced-techniques)

---

## Understanding Execution Algorithms

Execution algorithms control **how** orders are executed, not **when** or **what** to trade. They:
- Split large orders into smaller pieces
- Control timing of order execution
- Minimize market impact
- Optimize execution prices

### Current Algorithms

- **NORMAL**: Direct market orders (no splitting)
- **TWAP**: Time-Weighted Average Price (even time distribution)
- **VWAP**: Volume-Weighted Average Price (volume-proportional distribution)
- **ICEBERG**: Shows only small visible portion, hides rest

---

## File Structure

### Main File: `backend/execution_algorithms.py`

```python
# Structure:
# 1. Config classes (ExecAlgorithmConfig)
# 2. Algorithm classes (ExecAlgorithm)
# 3. Helper methods
```

### Key Components

1. **Config Class**: Defines algorithm ID and parameters
2. **Algorithm Class**: Implements the execution logic
3. **on_order()**: Main entry point - receives primary orders
4. **spawn_*()**: Methods to create child orders

---

## Editing Existing Algorithms

### Example: Improving VWAP with Volume Data

**Current VWAP** (uniform distribution):
```python
# Line 166-180 in execution_algorithms.py
# For simplicity, use uniform distribution
interval_secs = horizon_secs / intervals
child_qty_decimal = order.quantity.as_decimal() / Decimal(str(intervals))
```

**Improved VWAP** (volume-weighted):
```python
def on_order(self, order: Order) -> None:
    """Enhanced VWAP with actual volume data."""
    params = order.exec_algorithm_params or {}
    horizon_secs = params.get("horizon_secs", 60)
    intervals = params.get("intervals", 10)
    
    # Get historical volume distribution
    volume_profile = self._get_volume_profile(horizon_secs, intervals)
    
    # Distribute orders proportionally to volume
    total_volume = sum(volume_profile)
    for i, volume_pct in enumerate(volume_profile):
        child_qty = order.quantity * Decimal(str(volume_pct / total_volume))
        # Schedule spawn...
    
def _get_volume_profile(self, horizon_secs: int, intervals: int) -> List[float]:
    """Query historical volume data to create volume profile."""
    # Query cache for recent volume data
    # Return list of volume percentages per interval
    pass
```

### Example: Adaptive TWAP

**Current TWAP** (fixed intervals):
```python
# Line 71-106
num_orders = max(1, int(horizon_secs / interval_secs))
```

**Adaptive TWAP** (market-condition aware):
```python
def on_order(self, order: Order) -> None:
    """Adaptive TWAP that adjusts to market conditions."""
    params = order.exec_algorithm_params or {}
    horizon_secs = params.get("horizon_secs", 60)
    base_interval_secs = params.get("interval_secs", 10)
    
    # Check market volatility
    volatility = self._get_current_volatility()
    
    # Adjust interval based on volatility
    if volatility > 0.05:  # High volatility
        interval_secs = base_interval_secs * 0.5  # Faster execution
    elif volatility < 0.01:  # Low volatility
        interval_secs = base_interval_secs * 2.0  # Slower execution
    else:
        interval_secs = base_interval_secs
    
    # Continue with adjusted interval...
    
def _get_current_volatility(self) -> float:
    """Calculate current market volatility."""
    # Query recent price data from cache
    # Calculate standard deviation of returns
    pass
```

---

## Creating New Algorithms

### Step 1: Create Config Class

```python
class MyCustomExecAlgorithmConfig(ExecAlgorithmConfig, frozen=True):
    """Configuration for MyCustomExecAlgorithm."""
    exec_algorithm_id: ExecAlgorithmId | None = ExecAlgorithmId("MY_CUSTOM")
```

### Step 2: Create Algorithm Class

```python
class MyCustomExecAlgorithm(ExecAlgorithm):
    """
    My custom execution algorithm.
    
    Parameters:
        param1: Description of param1
        param2: Description of param2
    """
    
    def __init__(self, config=None):
        """Initialize custom execution algorithm."""
        if config is None:
            config = MyCustomExecAlgorithmConfig()
        super().__init__(config)
    
    def on_order(self, order: Order) -> None:
        """
        Handle incoming primary order.
        
        Args:
            order: The primary order to execute
        """
        # Get parameters
        params = order.exec_algorithm_params or {}
        param1 = params.get("param1", "default_value")
        
        # Your custom logic here
        # Example: Split order based on custom logic
        child_qty = order.quantity / Decimal("2")
        
        # Spawn child orders
        self.spawn_market(
            primary=order,
            quantity=child_qty,
        )
```

### Step 3: Register in Backtest Engine

**File: `backend/backtest_engine.py`**

```python
# Line 42-46: Add import
from backend.execution_algorithms import (
    TWAPExecAlgorithm,
    VWAPExecAlgorithm,
    IcebergExecAlgorithm,
    MyCustomExecAlgorithm,  # Add this
)

# Line ~1500: Add to _build_exec_algorithms method
def _build_exec_algorithms(self, exec_algorithm_type: str, exec_algorithm_params: Dict[str, Any]):
    if exec_algorithm_type == "MY_CUSTOM":
        return [MyCustomExecAlgorithm()]
    # ... existing code
```

### Step 4: Add CLI Support

**File: `backend/run_backtest.py`**

```python
# Line 106: Add to choices
parser.add_argument(
    "--exec_algorithm",
    type=str,
    choices=["NORMAL", "TWAP", "VWAP", "ICEBERG", "MY_CUSTOM"],  # Add here
    ...
)
```

### Step 5: Add UI Support

**File: `frontend/src/pages/BacktestRunnerPage.tsx`**

```typescript
// Add to exec algorithm dropdown options
<option value="MY_CUSTOM">My Custom Algorithm</option>
```

---

## Key Customization Points

### 1. Order Splitting Logic

**Location**: `on_order()` method

**Options**:
- **Time-based**: Split evenly over time (TWAP)
- **Volume-based**: Split proportionally to volume (VWAP)
- **Price-based**: Split based on price levels
- **Market-impact-based**: Split to minimize impact

**Example**:
```python
# Time-based splitting
for i in range(num_intervals):
    delay_secs = i * interval_secs
    # Schedule spawn...

# Volume-based splitting
volume_profile = [0.1, 0.2, 0.3, 0.2, 0.2]  # 5 intervals
for i, volume_pct in enumerate(volume_profile):
    child_qty = order.quantity * Decimal(str(volume_pct))
    # Schedule spawn...
```

### 2. Timing Control

**Location**: `clock.set_time_alert()` calls

**Options**:
- **Fixed intervals**: Regular time spacing
- **Adaptive intervals**: Adjust based on market conditions
- **Event-driven**: Trigger on specific market events

**Example**:
```python
# Fixed timing
spawn_time = self.clock.utc_now() + timedelta(seconds=delay_secs)

# Adaptive timing (based on volatility)
if volatility > threshold:
    delay_secs = delay_secs * 0.5  # Faster in volatile markets
```

### 3. Order Type Selection

**Location**: `_spawn_*_child()` methods

**Options**:
- **Market orders**: Immediate execution (`spawn_market()`)
- **Limit orders**: Price-controlled (`spawn_limit()`)
- **Market-to-limit**: Hybrid (`spawn_market_to_limit()`)

**Example**:
```python
def _spawn_child(self, order: Order, quantity: Quantity) -> None:
    # Use limit orders in low volatility
    if self._get_volatility() < 0.01:
        self.spawn_limit(
            primary=order,
            quantity=quantity,
            price=self._calculate_limit_price(order),
        )
    else:
        # Use market orders in high volatility
        self.spawn_market(
            primary=order,
            quantity=quantity,
        )
```

### 4. Market Data Access

**Location**: Anywhere in algorithm class

**Available via**:
- `self.cache`: Access order book, trades, etc.
- `self.portfolio`: Access positions, account info
- `self.msgbus`: Subscribe to market data events

**Example**:
```python
def _get_current_spread(self) -> Decimal:
    """Get current bid-ask spread."""
    order_book = self.cache.order_book(order.instrument_id)
    if order_book:
        return order_book.spread()
    return Decimal("0")

def _get_recent_volume(self, minutes: int) -> Decimal:
    """Get recent trading volume."""
    # Query cache for recent trades
    trades = self.cache.trades(order.instrument_id)
    # Filter by time and sum volume
    return total_volume
```

---

## Best Practices

### 1. Parameter Validation

Always validate parameters:
```python
def on_order(self, order: Order) -> None:
    params = order.exec_algorithm_params or {}
    horizon_secs = params.get("horizon_secs", 60)
    
    if horizon_secs <= 0:
        self.log.error(f"Invalid horizon_secs: {horizon_secs}")
        return
```

### 2. Error Handling

Handle edge cases:
```python
def _spawn_child(self, order: Order, quantity: Quantity) -> None:
    if quantity.as_decimal() <= 0:
        self.log.warning("Skipping zero quantity spawn")
        return
    
    try:
        self.spawn_market(primary=order, quantity=quantity)
    except Exception as e:
        self.log.error(f"Failed to spawn child order: {e}")
```

### 3. Logging

Add helpful logs:
```python
self.log.info(f"Algorithm: Received order {order.client_order_id}")
self.log.debug(f"Algorithm: Splitting into {num_orders} child orders")
```

### 4. Quantity Precision

Always round quantities:
```python
child_qty_decimal = order.quantity.as_decimal() / Decimal(str(intervals))
child_qty_decimal = round(child_qty_decimal, 16)  # Match instrument precision
child_qty = Quantity.from_str(str(child_qty_decimal))
```

### 5. Clock Scheduling

Use unique alert names:
```python
alert_name = f"algo_spawn_{order.client_order_id}_{i}_{uuid.uuid4()}"
self.clock.set_time_alert(
    name=alert_name,
    alert_time=spawn_time,
    callback=lambda event, qty=spawn_qty: self._spawn_child(order, qty)
)
```

---

## Testing Your Changes

### 1. Fast Test (1 minute)

```bash
docker-compose exec backend python3 backend/run_backtest.py \
  --instrument BTCUSDT \
  --config external/data_downloads/configs/binance_futures_btcusdt_l2_trades_config.json \
  --start 2023-05-24T05:00:00Z \
  --end 2023-05-24T05:01:00Z \
  --exec_algorithm VWAP \
  --exec_algorithm_params '{"horizon_secs": 30, "intervals": 3}' \
  --fast
```

### 2. Compare Results

```python
# Compare order counts, fill rates, P&L
# VWAP should create more orders than NORMAL
# Check fill rates and execution quality
```

### 3. Validate Behavior

- Check logs for algorithm activity
- Verify order splitting is working
- Confirm timing is correct
- Validate quantity calculations

---

## Advanced Techniques

### 1. Dynamic Parameter Adjustment

```python
def on_order(self, order: Order) -> None:
    params = order.exec_algorithm_params or {}
    base_horizon = params.get("horizon_secs", 60)
    
    # Adjust based on order size
    if order.quantity.as_decimal() > 1000:
        horizon_secs = base_horizon * 2  # Larger orders take longer
    else:
        horizon_secs = base_horizon
    
    # Continue with adjusted horizon...
```

### 2. Market Condition Awareness

```python
def _should_accelerate_execution(self) -> bool:
    """Check if we should speed up execution."""
    # Check for:
    # - Approaching market close
    # - High volatility
    # - Large position risk
    return self._is_near_market_close() or self._is_high_volatility()
```

### 3. Order Book Interaction

```python
def _calculate_optimal_price(self, order: Order) -> Price:
    """Calculate optimal limit price based on order book."""
    order_book = self.cache.order_book(order.instrument_id)
    if not order_book:
        return None
    
    if order.side == OrderSide.BUY:
        # Buy at best bid or slightly above
        return order_book.best_bid_price() + Price.from_str("0.01")
    else:
        # Sell at best ask or slightly below
        return order_book.best_ask_price() - Price.from_str("0.01")
```

### 4. Position-Aware Execution

```python
def on_order(self, order: Order) -> None:
    """Adjust execution based on current position."""
    position = self.portfolio.position(order.instrument_id)
    
    if position:
        # If we have a position, execution urgency changes
        if position.is_long() and order.side == OrderSide.SELL:
            # Closing long position - can be more patient
            horizon_secs = params.get("horizon_secs", 60) * 1.5
        else:
            # Opening new position - execute faster
            horizon_secs = params.get("horizon_secs", 60) * 0.7
```

---

## Common Customization Examples

### Example 1: Aggressive VWAP

Faster execution for urgent orders:
```python
def on_order(self, order: Order) -> None:
    params = order.exec_algorithm_params or {}
    horizon_secs = params.get("horizon_secs", 60)
    intervals = params.get("intervals", 10)
    
    # Reduce horizon for faster execution
    horizon_secs = horizon_secs * 0.5
    intervals = max(3, intervals // 2)  # Minimum 3 intervals
    
    # Continue with aggressive parameters...
```

### Example 2: Smart TWAP

Adjusts intervals based on order size:
```python
def on_order(self, order: Order) -> None:
    params = order.exec_algorithm_params or {}
    base_interval = params.get("interval_secs", 10)
    
    # Larger orders need more intervals
    order_size = order.quantity.as_decimal()
    if order_size > 100:
        interval_secs = base_interval * 0.5  # More frequent
    elif order_size < 10:
        interval_secs = base_interval * 2.0  # Less frequent
    else:
        interval_secs = base_interval
```

### Example 3: Spread-Aware Execution

Waits for better spreads:
```python
def _spawn_child(self, order: Order, quantity: Quantity) -> None:
    spread = self._get_current_spread()
    spread_threshold = Decimal("0.001")  # 0.1%
    
    if spread > spread_threshold:
        # Spread too wide - wait
        self.clock.set_time_alert(
            name=f"wait_spread_{order.client_order_id}",
            alert_time=self.clock.utc_now() + timedelta(seconds=5),
            callback=lambda: self._retry_spawn(order, quantity)
        )
    else:
        # Spread acceptable - execute
        self.spawn_market(primary=order, quantity=quantity)
```

---

## Quick Reference

### Key Methods

- `on_order(order)`: Main entry point
- `spawn_market(primary, quantity)`: Create market order
- `spawn_limit(primary, quantity, price)`: Create limit order
- `self.clock.set_time_alert()`: Schedule delayed execution
- `self.cache.order_book()`: Access order book
- `self.cache.trades()`: Access trade history
- `self.portfolio.position()`: Access current position

### Key Parameters

- `horizon_secs`: Total execution time
- `interval_secs`: Time between child orders (TWAP)
- `intervals`: Number of splits (VWAP)
- `visible_pct`: Visible portion (Iceberg)

### File Locations

- **Algorithms**: `backend/execution_algorithms.py`
- **Engine**: `backend/backtest_engine.py`
- **CLI**: `backend/run_backtest.py`
- **UI**: `frontend/src/pages/BacktestRunnerPage.tsx`

---

## Next Steps

1. **Start Small**: Modify existing algorithms first
2. **Test Thoroughly**: Use fast 1-minute tests
3. **Compare Results**: Benchmark against NORMAL
4. **Iterate**: Refine based on results
5. **Document**: Add comments explaining your logic

For questions or issues, check:
- NautilusTrader docs: https://nautilustrader.io/docs
- Execution algorithms guide: `EXECUTION_ALGORITHMS_GUIDE.md`
- Code examples in `backend/execution_algorithms.py`

