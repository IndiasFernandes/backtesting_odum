# Execution Algorithms Guide: TWAP, VWAP, and More

## Overview

Execution algorithms (exec algos) in NautilusTrader allow you to split large orders into smaller pieces over time to minimize market impact and achieve better execution prices. This guide covers how to test and deploy execution algorithms in both **backtesting** and **live trading** scenarios.

## What Are Execution Algorithms?

Execution algorithms break down large orders into smaller "child" orders that are executed over time according to specific rules:

- **TWAP (Time-Weighted Average Price)**: Executes orders evenly over a time horizon
- **VWAP (Volume-Weighted Average Price)**: Executes orders proportionally to market volume
- **Iceberg**: Hides order size by showing only a small portion
- **Custom Algorithms**: Build your own execution logic

## Key Concepts

### Primary vs. Spawned Orders

- **Primary Order**: The original large order submitted to the execution algorithm
- **Spawned Orders**: Smaller child orders created by the algorithm to fill the primary order

### Execution Algorithm Flow

1. Strategy submits a **primary order** with `exec_algorithm_id` and `exec_algorithm_params`
2. Execution algorithm receives the order via `on_order()` method
3. Algorithm spawns multiple smaller orders over time
4. Algorithm tracks fills and manages remaining quantity
5. When primary order is fully filled, algorithm completes

## Backtesting with Execution Algorithms

### Step 1: Add Execution Algorithm to BacktestEngine

```python
from nautilus_trader.examples.algorithms.twap import TWAPExecAlgorithm
from nautilus_trader.backtest.node import BacktestNode
from nautilus_trader.backtest.config import BacktestEngineConfig

# Create backtest engine
engine_config = BacktestEngineConfig()
engine = BacktestEngine(config=engine_config)

# Add TWAP execution algorithm
twap_algo = TWAPExecAlgorithm()
engine.add_exec_algorithm(twap_algo)
```

### Step 2: Configure Strategy to Use Execution Algorithm

#### Option A: Use Built-in EMACrossTWAP Strategy

```python
from decimal import Decimal
from nautilus_trader.model.data import BarType
from nautilus_trader.examples.strategies.ema_cross_twap import (
    EMACrossTWAP, 
    EMACrossTWAPConfig
)

# Configure strategy with TWAP parameters
strategy_config = EMACrossTWAPConfig(
    instrument_id=InstrumentId.from_str("BTC-USDT.BINANCE"),
    bar_type=BarType.from_str("BTC-USDT.BINANCE-250-TICK-LAST-INTERNAL"),
    trade_size=Decimal("0.10"),
    fast_ema_period=10,
    slow_ema_period=20,
    twap_horizon_secs=10.0,    # Total execution time (seconds)
    twap_interval_secs=2.5,    # Time between child orders (seconds)
)

strategy = EMACrossTWAP(config=strategy_config)
engine.add_strategy(strategy)
```

#### Option B: Modify Your Strategy to Submit Orders with Exec Algorithm

```python
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model import ExecAlgorithmId
from nautilus_trader.model.orders import MarketOrder

class MyStrategy(Strategy):
    def on_trade_tick(self, tick: TradeTick) -> None:
        # Submit order with TWAP execution algorithm
        order = self.order_factory.market(
            instrument_id=self.instrument_id,
            order_side=OrderSide.BUY,
            quantity=self.instrument.make_qty(Decimal("1.0")),
            time_in_force=TimeInForce.FOK,
            exec_algorithm_id=ExecAlgorithmId("TWAP"),
            exec_algorithm_params={
                "horizon_secs": 20,      # Execute over 20 seconds
                "interval_secs": 2.5,     # Place order every 2.5 seconds
            },
        )
        self.submit_order(order)
```

### Step 3: Run Backtest

```python
from nautilus_trader.backtest.node import BacktestNode
from nautilus_trader.backtest.config import BacktestRunConfig

# Configure backtest run
run_config = BacktestRunConfig(
    engine_id="backtest-engine-001",
    data_configs=[...],  # Your data configs
    venue_configs=[...],  # Your venue configs
    strategies=[strategy],
    exec_algorithms=[twap_algo],
)

# Run backtest
node = BacktestNode(configs=[run_config])
node.run()
```

## Integrating Execution Algorithms into Current System

### Update BacktestEngine to Support Execution Algorithms

Add execution algorithm support to `backend/backtest_engine.py`:

```python
from nautilus_trader.examples.algorithms.twap import TWAPExecAlgorithm
from nautilus_trader.model import ExecAlgorithmId

class BacktestEngine:
    def _add_execution_algorithms(self, config: Dict[str, Any]) -> List:
        """
        Add execution algorithms based on config.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            List of execution algorithms
        """
        exec_algorithms = []
        
        # Check if execution algorithms are configured
        exec_config = config.get("execution", {})
        algorithms = exec_config.get("algorithms", [])
        
        for algo_config in algorithms:
            algo_type = algo_config.get("type", "").upper()
            
            if algo_type == "TWAP":
                # Create TWAP algorithm
                twap_algo = TWAPExecAlgorithm()
                exec_algorithms.append(twap_algo)
            elif algo_type == "VWAP":
                # Create VWAP algorithm (if available)
                # vwap_algo = VWAPExecAlgorithm()
                # exec_algorithms.append(vwap_algo)
                pass
            # Add more algorithm types as needed
        
        return exec_algorithms
    
    def run(self, ...):
        # ... existing code ...
        
        # Add execution algorithms
        exec_algorithms = self._add_execution_algorithms(config)
        
        # Create BacktestRunConfig with exec algorithms
        run_config = BacktestRunConfig(
            engine_id=engine_id,
            data_configs=data_configs,
            venue_configs=venue_configs,
            strategies=[strategy],
            exec_algorithms=exec_algorithms,  # Add this
        )
        
        # ... rest of run method ...
```

### Update JSON Configuration Schema

Add execution algorithm configuration to your JSON configs:

```json
{
  "instrument": { ... },
  "venue": { ... },
  "strategy": {
    "name": "TempBacktestStrategy",
    "submission_mode": "per_trade_tick",
    "use_exec_algorithm": true,
    "exec_algorithm": {
      "type": "TWAP",
      "params": {
        "horizon_secs": 20,
        "interval_secs": 2.5
      }
    }
  },
  "execution": {
    "algorithms": [
      {
        "type": "TWAP",
        "id": "TWAP",
        "enabled": true
      }
    ]
  }
}
```

### Update Strategy to Use Execution Algorithms

Modify `backend/strategy.py`:

```python
from nautilus_trader.model import ExecAlgorithmId

class TempBacktestStrategy(Strategy):
    def __init__(self, config: TempBacktestStrategyConfig):
        super().__init__(config)
        # ... existing code ...
        
        # Check if execution algorithm should be used
        self.use_exec_algo = getattr(config, 'use_exec_algorithm', False)
        self.exec_algo_config = getattr(config, 'exec_algorithm', {})
    
    def on_trade_tick(self, tick: TradeTick) -> None:
        # ... existing order creation logic ...
        
        if self.use_exec_algo:
            # Add execution algorithm parameters
            exec_algo_id = ExecAlgorithmId(self.exec_algo_config.get("type", "TWAP"))
            exec_algo_params = self.exec_algo_config.get("params", {})
            
            order = self.order_factory.market(
                instrument_id=tick.instrument_id,
                order_side=side,
                quantity=quantity,
                time_in_force=TimeInForce.FOK,
                exec_algorithm_id=exec_algo_id,
                exec_algorithm_params=exec_algo_params,
            )
        else:
            # Original order creation without exec algo
            order = self.order_factory.limit(
                instrument_id=tick.instrument_id,
                order_side=side,
                quantity=quantity,
                price=tick.price
            )
        
        self.submit_order(order)
```

## Live Trading with Execution Algorithms

### Step 1: Set Up Live Trading Environment

```python
from nautilus_trader.live.node import LiveNode
from nautilus_trader.live.config import LiveEngineConfig
from nautilus_trader.adapters.binance import BinanceDataClient, BinanceExecutionClient

# Create live engine config
engine_config = LiveEngineConfig()

# Create data and execution clients
data_client = BinanceDataClient(
    loop=asyncio.get_event_loop(),
    client=binance_client,
    msgbus=msgbus,
    cache=cache,
    clock=clock,
)

exec_client = BinanceExecutionClient(
    loop=asyncio.get_event_loop(),
    client=binance_client,
    msgbus=msgbus,
    cache=cache,
    clock=clock,
)

# Create live node
live_node = LiveNode(config=engine_config)
live_node.add_data_client(data_client)
live_node.add_exec_client(exec_client)
```

### Step 2: Add Execution Algorithms to Live Node

```python
from nautilus_trader.examples.algorithms.twap import TWAPExecAlgorithm

# Create execution algorithm
twap_algo = TWAPExecAlgorithm()

# Add to live node
live_node.add_exec_algorithm(twap_algo)
```

### Step 3: Deploy Strategy with Execution Algorithm

```python
# Use the same strategy code from backtesting
strategy = EMACrossTWAP(config=strategy_config)

# Add strategy to live node
live_node.add_strategy(strategy)

# Start live trading
live_node.run()
```

## Available Execution Algorithms

### TWAP (Time-Weighted Average Price)

**Purpose**: Execute orders evenly over a time horizon

**Parameters**:
- `horizon_secs`: Total execution time in seconds
- `interval_secs`: Time between child orders in seconds

**Example**:
```python
exec_algorithm_params = {
    "horizon_secs": 60,      # Execute over 1 minute
    "interval_secs": 5,     # Place order every 5 seconds
}
```

**Use Cases**:
- Large orders that need to be executed over time
- Minimizing market impact
- Achieving average execution price

### VWAP (Volume-Weighted Average Price)

**Purpose**: Execute orders proportionally to market volume

**Note**: VWAP may not be available as a built-in algorithm. You may need to implement it yourself.

**Use Cases**:
- Matching market volume profile
- Reducing impact during high-volume periods

### Custom Execution Algorithms

You can create your own execution algorithms by inheriting from `ExecAlgorithm`:

```python
from nautilus_trader.execution.algorithm import ExecAlgorithm
from nautilus_trader.model.orders.base import Order
from nautilus_trader.model.objects import Quantity
from decimal import Decimal
from datetime import timedelta

class MyCustomExecAlgorithm(ExecAlgorithm):
    def on_order(self, order: Order) -> None:
        """
        Handle incoming primary order.
        
        Args:
            order: The primary order to execute
        """
        # Validate exec_algorithm_params
        params = order.exec_algorithm_params or {}
        horizon_secs = params.get("horizon_secs", 10)
        interval_secs = params.get("interval_secs", 1)
        
        # Calculate number of child orders
        num_orders = max(1, int(horizon_secs / interval_secs))
        child_qty_decimal = order.quantity.as_decimal() / Decimal(str(num_orders))
        child_qty_decimal = round(child_qty_decimal, 16)  # Match precision
        child_qty = Quantity.from_str(str(child_qty_decimal))
        
        # Spawn child orders with time delays
        for i in range(num_orders):
            delay_secs = i * interval_secs
            
            if delay_secs > 0:
                # Schedule delayed spawn using clock
                spawn_time = self.clock.utc_now() + timedelta(seconds=delay_secs)
                spawn_qty_capture = child_qty  # Capture in closure
                alert_name = f"custom_spawn_{order.client_order_id}_{i}"
                self.clock.set_time_alert(
                    name=alert_name,
                    alert_time=spawn_time,
                    callback=lambda event, qty=spawn_qty_capture: self._spawn_child(order, qty)
                )
            else:
                # Spawn immediately
                self._spawn_child(order, child_qty)
    
    def _spawn_child(self, order: Order, quantity: Quantity) -> None:
        """Helper to spawn child order."""
        self.spawn_market(
            primary=order,  # Note: parameter is "primary", not "primary_order"
            quantity=quantity,
        )
```

## Testing Execution Algorithms

### Backtesting Test Workflow

1. **Create test config with exec algorithm**:
```json
{
  "execution": {
    "algorithms": [{"type": "TWAP", "id": "TWAP"}]
  },
  "strategy": {
    "use_exec_algorithm": true,
    "exec_algorithm": {
      "type": "TWAP",
      "params": {"horizon_secs": 20, "interval_secs": 2.5}
    }
  }
}
```

2. **Run backtest**:
```bash
python backend/run_backtest.py \
  --instrument BTC-USDT \
  --config configs/twap_test_config.json \
  --start 2023-05-25T02:00:00Z \
  --end 2023-05-25T02:05:00Z \
  --data_source gcs
```

3. **Analyze results**:
- Check order timeline to see spawned orders
- Verify execution price vs. market price
- Compare performance metrics (slippage, fill rate, etc.)

### Comparing Algorithms

Run multiple backtests with different algorithms:

```bash
# TWAP backtest
python backend/run_backtest.py --config configs/twap_config.json ...

# Market order backtest (no exec algo)
python backend/run_backtest.py --config configs/market_config.json ...

# Compare results
python scripts/compare_exec_algorithms.py \
  --results results/twap/ \
  --results results/market/
```

## Best Practices

### 1. Start with Backtesting

Always test execution algorithms thoroughly in backtesting before deploying live.

### 2. Parameter Tuning

- **TWAP horizon_secs**: Match to your order size and market conditions
- **TWAP interval_secs**: Balance between market impact and execution speed
- Test different parameter combinations

### 3. Monitor Performance

Track these metrics:
- **Execution Price**: Average fill price vs. market price
- **Slippage**: Difference between expected and actual execution price
- **Fill Rate**: Percentage of order filled
- **Market Impact**: Price movement caused by your orders

### 4. Risk Management

- Set maximum order size limits
- Monitor remaining quantity
- Implement circuit breakers for extreme market conditions

### 5. Live Trading Considerations

- Start with small order sizes
- Monitor execution in real-time
- Have manual override capability
- Log all executions for analysis

## Example: Complete TWAP Integration

### 1. Update Config Loader

```python
# backend/config_loader.py
def load_config(self, config_path: Path) -> Dict[str, Any]:
    config = json.loads(config_path.read_text())
    
    # Add default execution config if not present
    if "execution" not in config:
        config["execution"] = {
            "algorithms": []
        }
    
    return config
```

### 2. Update BacktestEngine

```python
# backend/backtest_engine.py
def run(self, ...):
    # ... existing setup ...
    
    # Add execution algorithms
    exec_algorithms = []
    exec_config = config.get("execution", {})
    for algo_config in exec_config.get("algorithms", []):
        if algo_config.get("type") == "TWAP":
            exec_algorithms.append(TWAPExecAlgorithm())
    
    # Create run config with exec algorithms
    run_config = BacktestRunConfig(
        # ... existing config ...
        exec_algorithms=exec_algorithms,
    )
    
    # ... rest of run method ...
```

### 3. Update Strategy Config

```python
# backend/strategy.py
class TempBacktestStrategyConfig(StrategyConfig):
    instrument_id: str
    submission_mode: str = "per_trade_tick"
    use_exec_algorithm: bool = False
    exec_algorithm_type: Optional[str] = None
    exec_algorithm_params: Optional[Dict[str, Any]] = None
```

### 4. Test with CLI

```bash
# Run backtest with TWAP
python backend/run_backtest.py \
  --instrument BTC-USDT \
  --config configs/twap_config.json \
  --start 2023-05-25T02:00:00Z \
  --end 2023-05-25T02:05:00Z \
  --data_source gcs
```

## Resources

- **NautilusTrader Execution Concepts**: https://nautilustrader.io/docs/latest/concepts/execution
- **NautilusTrader Backtesting Guide**: https://nautilustrader.io/docs/latest/getting_started/backtest_low_level
- **TWAP Example**: `nautilus_trader/examples/algorithms/twap.py`
- **EMACrossTWAP Strategy**: `nautilus_trader/examples/strategies/ema_cross_twap.py`

## Next Steps

1. ✅ Add execution algorithm support to `BacktestEngine`
2. ✅ Update JSON config schema to include execution config
3. ✅ Modify strategy to use execution algorithms
4. ✅ Test with backtesting
5. ✅ Deploy to live trading (after thorough testing)

## Summary

Execution algorithms like TWAP allow you to:
- **Backtest**: Test order execution strategies on historical data
- **Live Trade**: Deploy the same algorithms to live markets
- **Optimize**: Minimize market impact and improve execution prices
- **Customize**: Build your own execution logic

The same code works in both backtesting and live trading, ensuring consistency between testing and production.

