# OMS & Smart Routing Quick Reference

## Quick Answer

**YES, you can implement everything:**
- ✅ **OMS**: Already supported (NETTING/HEDGING in config)
- ✅ **Smart Router**: Created (`backend/smart_router.py`)
- ✅ **Execution Patterns**: Created (`backend/execution_algorithms.py`)
- ✅ **Buy Patterns**: Aggressive, Passive, Iceberg, TWAP, VWAP

---

## What Was Created

### 1. Smart Order Router (`backend/smart_router.py`)
- Routes orders to best venue based on fees, latency, fill rates
- Splits large orders across multiple venues
- Tracks venue performance

### 2. Execution Algorithms (`backend/execution_algorithms.py`)
- **TWAP**: Time-weighted execution
- **VWAP**: Volume-weighted execution
- **Buy Patterns**: Aggressive, Passive, Iceberg

### 3. Documentation (`OMS_SMART_ROUTING_GUIDE.md`)
- Complete implementation guide
- Code examples
- Best practices

---

## Quick Usage Examples

### Example 1: Multi-Venue Config

```json
{
  "strategy": {
    "name": "MultiVenueStrategy",
    "use_smart_routing": true,
    "venues": [
      {
        "name": "BINANCE-FUTURES",
        "maker_fee": 0.0002,
        "taker_fee": 0.0004,
        "latency_ms": 50
      },
      {
        "name": "DERIBIT",
        "maker_fee": 0.0001,
        "taker_fee": 0.0003,
        "latency_ms": 80
      }
    ]
  }
}
```

### Example 2: TWAP Execution

```json
{
  "strategy": {
    "name": "TWAPStrategy",
    "execution_algorithm": {
      "type": "TWAP",
      "duration_seconds": 3600,
      "interval_seconds": 60
    }
  }
}
```

### Example 3: Aggressive Buy Pattern

```python
from backend.execution_algorithms import AggressiveBuyPattern

pattern = AggressiveBuyPattern(order_factory)
order = pattern.execute(instrument_id, quantity)
submit_order(order)
```

---

## OMS Types (Already Supported)

### NETTING (Default)
```json
{
  "venue": {
    "oms_type": "NETTING"  // Single net position
  }
}
```

### HEDGING
```json
{
  "venue": {
    "oms_type": "HEDGING"  // Separate long/short positions
  }
}
```

---

## Smart Router Usage

```python
from backend.smart_router import SmartOrderRouter

# Initialize router
venues = [
    {"name": "BINANCE-FUTURES", "maker_fee": 0.0002, "taker_fee": 0.0004},
    {"name": "DERIBIT", "maker_fee": 0.0001, "taker_fee": 0.0003},
]
router = SmartOrderRouter(venues)

# Select best venue
venue = router.select_venue(
    instrument_id=instrument_id,
    side=OrderSide.BUY,
    quantity=Quantity.from_str("1.0"),
    price=Price.from_str("50000.0")
)

# Route large order across venues
allocations = router.route_order(
    instrument_id=instrument_id,
    side=OrderSide.BUY,
    total_quantity=Quantity.from_str("10.0"),
    max_venues=3
)
```

---

## Execution Algorithms Usage

### TWAP
```python
from backend.execution_algorithms import TWAPExecAlgorithm, TWAPExecAlgorithmConfig

config = TWAPExecAlgorithmConfig(
    duration_seconds=3600,  # 1 hour
    interval_seconds=60     # 1 minute intervals
)
algorithm = TWAPExecAlgorithm(config)

algorithm.execute(
    instrument_id=instrument_id,
    side=OrderSide.BUY,
    quantity=Quantity.from_str("10.0"),
    price=Price.from_str("50000.0")
)
```

### VWAP
```python
from backend.execution_algorithms import VWAPExecAlgorithm, VWAPExecAlgorithmConfig

volume_profile = {
    0: 0.05,   # 5% of volume at midnight
    9: 0.15,   # 15% at 9 AM
    15: 0.20,  # 20% at 3 PM
    # ... etc
}

config = VWAPExecAlgorithmConfig(
    duration_seconds=3600,
    volume_profile=volume_profile
)
algorithm = VWAPExecAlgorithm(config)
```

---

## Buy Patterns

### Aggressive (Market Order)
```python
from backend.execution_algorithms import AggressiveBuyPattern

pattern = AggressiveBuyPattern(order_factory)
order = pattern.execute(instrument_id, quantity)
submit_order(order)
```

### Passive (Limit at Bid)
```python
from backend.execution_algorithms import PassiveBuyPattern

pattern = PassiveBuyPattern(order_factory, cache)
order = pattern.execute(instrument_id, quantity)
submit_order(order)
```

### Iceberg (Hidden Size)
```python
from backend.execution_algorithms import IcebergBuyPattern

pattern = IcebergBuyPattern(order_factory, visible_pct=0.1)
result = pattern.execute(instrument_id, total_quantity)
submit_order(result["visible_order"])
# When visible order fills, submit next chunk
```

---

## Integration Steps

### Step 1: Add to Strategy Config

```python
# backend/strategy.py
class SmartRoutingStrategyConfig(StrategyConfig):
    instrument_id: str
    use_smart_routing: bool = False
    venues: List[Dict] = []
    execution_algorithm: Optional[Dict] = None
```

### Step 2: Use in Strategy

```python
class MultiVenueStrategy(Strategy):
    def __init__(self, config):
        super().__init__(config)
        if config.use_smart_routing:
            from backend.smart_router import SmartOrderRouter
            self.router = SmartOrderRouter(config.venues)
    
    def on_trade_tick(self, tick):
        if self.should_trade(tick):
            # Use router to select venue
            venue = self.router.select_venue(...)
            # Submit order
```

---

## Summary

### ✅ OMS
- NETTING: Single net position
- HEDGING: Separate long/short

### ✅ Smart Router
- Venue selection
- Order splitting
- Performance tracking

### ✅ Execution Algorithms
- TWAP: Time-weighted
- VWAP: Volume-weighted
- Buy patterns: Aggressive, Passive, Iceberg

### ✅ Integration
- Works with your existing config system
- Extends your current strategy
- Ready to use!

---

## Files Created

1. `backend/smart_router.py` - Smart order router
2. `backend/execution_algorithms.py` - Execution algorithms
3. `OMS_SMART_ROUTING_GUIDE.md` - Complete guide
4. `OMS_QUICK_REFERENCE.md` - This file

---

## Next Steps

1. ✅ Review implementation files
2. ✅ Test smart router with sample configs
3. ✅ Integrate with your strategy
4. ✅ Backtest with multi-venue configs
5. ✅ Monitor and optimize routing performance

Everything is ready to use! 🚀

