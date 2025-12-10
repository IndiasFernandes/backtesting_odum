# OMS, Smart Routing & Execution Patterns Guide

## Overview

This guide shows how to implement a comprehensive Order Management System (OMS) with smart order routing and custom execution patterns (TWAP, VWAP, etc.) using NautilusTrader.

---

## Table of Contents

1. [Order Management System (OMS)](#order-management-system-oms)
2. [Smart Order Router (SOR)](#smart-order-router-sor)
3. [Execution Algorithms](#execution-algorithms)
4. [Multi-Venue Trading](#multi-venue-trading)
5. [Implementation Examples](#implementation-examples)

---

## Order Management System (OMS)

### OMS Types in NautilusTrader

NautilusTrader supports two OMS types:

#### 1. NETTING OMS
- **Single net position** per instrument
- Long and short positions offset each other
- **Use case**: Futures, perpetuals, spot trading
- **Example**: If you have +10 BTC and -5 BTC, net position = +5 BTC

```python
BacktestVenueConfig(
    name="BINANCE-FUTURES",
    oms_type="NETTING",  # ← Net positions
    account_type="MARGIN",
    starting_balances=["1000000 USDT"],
)
```

#### 2. HEDGING OMS
- **Separate long and short positions** per instrument
- Can hold both long and short simultaneously
- **Use case**: Hedging strategies, market making
- **Example**: Can have +10 BTC long and -5 BTC short simultaneously

```python
BacktestVenueConfig(
    name="DERIBIT",
    oms_type="HEDGING",  # ← Separate positions
    account_type="MARGIN",
    starting_balances=["1000000 USDT"],
)
```

### Configuring OMS in Your System

Your config already supports OMS configuration:

```json
{
  "venue": {
    "name": "BINANCE-FUTURES",
    "oms_type": "NETTING",  // ← OMS type here
    "account_type": "MARGIN",
    "base_currency": "USDT",
    "starting_balance": 1000000
  }
}
```

---

## Smart Order Router (SOR)

### What is Smart Order Routing?

Smart Order Routing automatically selects the best venue for each order based on:
- **Price**: Best bid/ask across venues
- **Liquidity**: Available volume
- **Fees**: Maker/taker fees
- **Latency**: Execution speed
- **Fill probability**: Historical fill rates

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Strategy Layer                        │
│  (Decides: What to trade, When to trade)                │
└────────────────────┬──────────────────────────────────────┘
                     │
┌────────────────────▼──────────────────────────────────────┐
│              Smart Order Router (SOR)                     │
│  (Decides: Which venue, How to split order)              │
├──────────────────────────────────────────────────────────┤
│  - Price comparison across venues                        │
│  - Liquidity analysis                                    │
│  - Fee optimization                                       │
│  - Order splitting logic                                 │
└────────────────────┬──────────────────────────────────────┘
                     │
┌────────────────────▼──────────────────────────────────────┐
│           Execution Algorithm Layer                       │
│  (Decides: TWAP, VWAP, Implementation Shortfall)        │
└────────────────────┬──────────────────────────────────────┘
                     │
┌────────────────────▼──────────────────────────────────────┐
│              Venue Execution Clients                       │
│  (Binance, Deribit, OKX, etc.)                           │
└───────────────────────────────────────────────────────────┘
```

### Implementing Smart Router

```python
from typing import List, Dict, Optional
from decimal import Decimal
from nautilus_trader.model.identifiers import InstrumentId, Venue
from nautilus_trader.model.objects import Quantity, Price
from nautilus_trader.model.enums import OrderSide


class SmartOrderRouter:
    """
    Smart Order Router that selects optimal venue for each order.
    """
    
    def __init__(self, venues: List[Dict]):
        """
        Initialize router with venue configurations.
        
        Args:
            venues: List of venue configs with fees, latency, etc.
        """
        self.venues = venues
        self.venue_stats = {}  # Track fill rates, latency, etc.
    
    def select_venue(
        self,
        instrument_id: InstrumentId,
        side: OrderSide,
        quantity: Quantity,
        price: Optional[Price] = None
    ) -> Venue:
        """
        Select best venue for order execution.
        
        Args:
            instrument_id: Instrument to trade
            side: Buy or sell
            quantity: Order quantity
            price: Optional limit price
            
        Returns:
            Best venue for this order
        """
        best_venue = None
        best_score = -float('inf')
        
        for venue_config in self.venues:
            venue_name = venue_config["name"]
            
            # Calculate venue score
            score = self._calculate_venue_score(
                venue_name=venue_name,
                instrument_id=instrument_id,
                side=side,
                quantity=quantity,
                price=price,
                venue_config=venue_config
            )
            
            if score > best_score:
                best_score = score
                best_venue = Venue(venue_name)
        
        return best_venue
    
    def _calculate_venue_score(
        self,
        venue_name: str,
        instrument_id: InstrumentId,
        side: OrderSide,
        quantity: Quantity,
        price: Optional[Price],
        venue_config: Dict
    ) -> float:
        """
        Calculate score for venue (higher = better).
        
        Scoring factors:
        - Price improvement (if limit order)
        - Fee cost
        - Liquidity
        - Historical fill rate
        - Latency
        """
        score = 0.0
        
        # 1. Fee cost (lower fees = higher score)
        maker_fee = venue_config.get("maker_fee", 0.0)
        taker_fee = venue_config.get("taker_fee", 0.0)
        avg_fee = (maker_fee + taker_fee) / 2
        score -= avg_fee * 1000  # Penalize fees
        
        # 2. Historical fill rate (if available)
        if venue_name in self.venue_stats:
            fill_rate = self.venue_stats[venue_name].get("fill_rate", 0.5)
            score += fill_rate * 100  # Reward high fill rates
        
        # 3. Liquidity (if available from order book)
        # In backtesting, we can estimate from historical data
        # In live trading, query order book depth
        
        # 4. Price improvement (for limit orders)
        if price:
            # Check if venue has better price
            # This would require order book data
            pass
        
        return score
    
    def route_order(
        self,
        instrument_id: InstrumentId,
        side: OrderSide,
        total_quantity: Quantity,
        price: Optional[Price] = None,
        max_venues: int = 3
    ) -> List[Dict]:
        """
        Route large order across multiple venues.
        
        Args:
            instrument_id: Instrument to trade
            side: Buy or sell
            total_quantity: Total order size
            price: Optional limit price
            max_venues: Maximum venues to use
            
        Returns:
            List of venue/quantity allocations
        """
        allocations = []
        remaining = total_quantity
        
        # Sort venues by score
        venue_scores = []
        for venue_config in self.venues:
            score = self._calculate_venue_score(
                venue_name=venue_config["name"],
                instrument_id=instrument_id,
                side=side,
                quantity=total_quantity,
                price=price,
                venue_config=venue_config
            )
            venue_scores.append((venue_config, score))
        
        venue_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Allocate quantity across top venues
        for i, (venue_config, score) in enumerate(venue_scores[:max_venues]):
            if remaining <= 0:
                break
            
            # Allocate percentage based on score
            if i == len(venue_scores[:max_venues]) - 1:
                # Last venue gets remainder
                allocation = remaining
            else:
                # Allocate proportional to score
                total_score = sum(s for _, s in venue_scores[:max_venues])
                allocation = total_quantity * (score / total_score) if total_score > 0 else total_quantity / max_venues
            
            allocations.append({
                "venue": Venue(venue_config["name"]),
                "quantity": min(allocation, remaining),
                "price": price,
            })
            
            remaining -= allocation
        
        return allocations
```

---

## Execution Algorithms

### Execution Algorithm Types

#### 1. TWAP (Time-Weighted Average Price)

Executes orders evenly over a time period.

```python
from nautilus_trader.execution.algorithms import ExecAlgorithm, ExecAlgorithmConfig
from datetime import timedelta
from typing import Optional


class TWAPExecAlgorithmConfig(ExecAlgorithmConfig):
    """Configuration for TWAP execution algorithm."""
    duration: timedelta  # Total execution time
    interval: timedelta  # Time between child orders


class TWAPExecAlgorithm(ExecAlgorithm):
    """
    Time-Weighted Average Price execution algorithm.
    
    Splits large order into smaller orders executed evenly over time.
    """
    
    def __init__(self, config: TWAPExecAlgorithmConfig):
        super().__init__(config)
        self.config = config
        self.child_orders = []
        self.start_time = None
        self.total_quantity = None
        self.remaining_quantity = None
    
    def execute(
        self,
        instrument_id: InstrumentId,
        side: OrderSide,
        quantity: Quantity,
        price: Optional[Price] = None
    ):
        """
        Execute order using TWAP algorithm.
        
        Args:
            instrument_id: Instrument to trade
            side: Buy or sell
            quantity: Total order quantity
            price: Optional limit price
        """
        self.total_quantity = quantity
        self.remaining_quantity = quantity
        self.start_time = self.clock.utc_now()
        
        # Calculate number of child orders
        num_orders = int(self.config.duration / self.config.interval)
        child_size = quantity / num_orders
        
        # Schedule child orders
        for i in range(num_orders):
            order_time = self.start_time + (i * self.config.interval)
            
            # Create child order
            child_order = self.order_factory.limit(
                instrument_id=instrument_id,
                order_side=side,
                quantity=child_size,
                price=price,
            )
            
            # Schedule for execution
            self.clock.schedule(
                callback=lambda: self._submit_child_order(child_order),
                when=order_time
            )
    
    def _submit_child_order(self, order):
        """Submit scheduled child order."""
        self.submit_order(order)
        self.child_orders.append(order)
```

#### 2. VWAP (Volume-Weighted Average Price)

Executes orders based on historical volume profile.

```python
class VWAPExecAlgorithm(ExecAlgorithm):
    """
    Volume-Weighted Average Price execution algorithm.
    
    Executes orders proportionally to historical volume distribution.
    """
    
    def __init__(self, config: ExecAlgorithmConfig):
        super().__init__(config)
        self.volume_profile = {}  # Historical volume by time of day
    
    def execute(
        self,
        instrument_id: InstrumentId,
        side: OrderSide,
        quantity: Quantity,
        price: Optional[Price] = None
    ):
        """
        Execute order using VWAP algorithm.
        
        Uses historical volume profile to determine execution schedule.
        """
        # Get volume profile for current time window
        current_hour = self.clock.utc_now().hour
        volume_distribution = self._get_volume_distribution(current_hour)
        
        # Execute proportionally to volume distribution
        for time_slot, volume_pct in volume_distribution.items():
            child_quantity = quantity * Decimal(str(volume_pct))
            
            child_order = self.order_factory.limit(
                instrument_id=instrument_id,
                order_side=side,
                quantity=child_quantity,
                price=price,
            )
            
            # Schedule for execution at time slot
            self.clock.schedule(
                callback=lambda: self.submit_order(child_order),
                when=time_slot
            )
    
    def _get_volume_distribution(self, hour: int) -> Dict:
        """Get volume distribution for hour."""
        # Load from historical data or use default
        return self.volume_profile.get(hour, {})
```

#### 3. Implementation Shortfall

Minimizes the difference between decision price and execution price.

```python
class ImplementationShortfallAlgorithm(ExecAlgorithm):
    """
    Implementation Shortfall execution algorithm.
    
    Balances market impact vs. opportunity cost.
    """
    
    def execute(
        self,
        instrument_id: InstrumentId,
        side: OrderSide,
        quantity: Quantity,
        decision_price: Price  # Price when decision was made
    ):
        """
        Execute order minimizing implementation shortfall.
        
        Implementation shortfall = (execution_price - decision_price) * quantity
        """
        # Calculate optimal execution schedule
        # Balance between:
        # - Market impact (larger orders = worse price)
        # - Opportunity cost (delayed execution = price moves away)
        
        # Use adaptive schedule based on:
        # - Current market volatility
        # - Order size relative to average volume
        # - Price trend
        
        pass
```

---

## Multi-Venue Trading

### Strategy with Smart Routing

```python
from nautilus_trader.trading.strategy import Strategy
from nautilus_trader.model.identifiers import InstrumentId, Venue
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.objects import Quantity, Price


class MultiVenueStrategy(Strategy):
    """
    Strategy that trades across multiple venues using smart routing.
    """
    
    def __init__(self, config):
        super().__init__(config)
        self.router = SmartOrderRouter(venues=config.venues)
        self.exec_algorithm = None  # Optional execution algorithm
    
    def on_start(self):
        """Initialize strategy."""
        # Subscribe to market data from all venues
        for venue_config in self.config.venues:
            venue = Venue(venue_config["name"])
            instrument_id = InstrumentId.from_str(
                f"{venue_config['name']}:PERPETUAL:BTC-USDT"
            )
            self.subscribe_trade_ticks(instrument_id)
    
    def on_trade_tick(self, tick):
        """Handle trade tick - decide to trade."""
        # Strategy logic decides: should we trade?
        if self.should_trade(tick):
            # Determine order parameters
            side = OrderSide.BUY  # or SELL
            quantity = Quantity.from_str("1.0")
            price = tick.price
            
            # Use smart router to select venue
            if self.config.use_smart_routing:
                venue = self.router.select_venue(
                    instrument_id=tick.instrument_id,
                    side=side,
                    quantity=quantity,
                    price=price
                )
            else:
                venue = Venue(tick.instrument_id.venue)
            
            # Create order
            order = self.order_factory.limit(
                instrument_id=tick.instrument_id,
                order_side=side,
                quantity=quantity,
                price=price,
            )
            
            # Apply execution algorithm if configured
            if self.exec_algorithm:
                self.exec_algorithm.execute(
                    instrument_id=tick.instrument_id,
                    side=side,
                    quantity=quantity,
                    price=price
                )
            else:
                # Direct execution
                self.submit_order(order)
    
    def should_trade(self, tick) -> bool:
        """Strategy logic: should we trade on this tick?"""
        # Your trading logic here
        return False
```

---

## Implementation Examples

### Example 1: Simple Multi-Venue Config

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
      },
      {
        "name": "OKX",
        "maker_fee": 0.0002,
        "taker_fee": 0.0005,
        "latency_ms": 60
      }
    ],
    "execution_algorithm": {
      "type": "TWAP",
      "duration_minutes": 60,
      "interval_seconds": 10
    }
  }
}
```

### Example 2: TWAP Execution Pattern

```python
# In your strategy config
{
  "strategy": {
    "name": "TWAPStrategy",
    "execution": {
      "algorithm": "TWAP",
      "duration": "1h",
      "interval": "10s",
      "child_order_size": "auto"  # Auto-calculate from total size
    }
  }
}
```

### Example 3: Buy Pattern with Price Improvement

```python
class BuyPatternStrategy(Strategy):
    """
    Strategy with specific buy order patterns.
    """
    
    def execute_buy_pattern(
        self,
        instrument_id: InstrumentId,
        total_quantity: Quantity,
        pattern: str = "aggressive"
    ):
        """
        Execute buy order with specific pattern.
        
        Patterns:
        - "aggressive": Market orders, immediate execution
        - "passive": Limit orders at bid, wait for fill
        - "iceberg": Large order hidden, show small size
        - "stealth": Very small orders, avoid detection
        """
        if pattern == "aggressive":
            # Market order, immediate execution
            order = self.order_factory.market(
                instrument_id=instrument_id,
                order_side=OrderSide.BUY,
                quantity=total_quantity,
            )
            self.submit_order(order)
        
        elif pattern == "passive":
            # Limit order at current bid
            book = self.cache.order_book(instrument_id)
            if book:
                bid_price = book.best_bid_price()
                order = self.order_factory.limit(
                    instrument_id=instrument_id,
                    order_side=OrderSide.BUY,
                    quantity=total_quantity,
                    price=bid_price,
                )
                self.submit_order(order)
        
        elif pattern == "iceberg":
            # Show small size, hide large size
            visible_size = total_quantity * Decimal("0.1")  # Show 10%
            hidden_size = total_quantity - visible_size
            
            # Submit visible order
            visible_order = self.order_factory.limit(
                instrument_id=instrument_id,
                order_side=OrderSide.BUY,
                quantity=visible_size,
                price=self._get_best_price(instrument_id, OrderSide.BUY),
            )
            self.submit_order(visible_order)
            
            # When visible order fills, submit next chunk
            # (This would be handled in on_order_filled)
        
        elif pattern == "stealth":
            # Very small orders to avoid detection
            num_orders = 20
            order_size = total_quantity / num_orders
            
            for i in range(num_orders):
                order = self.order_factory.limit(
                    instrument_id=instrument_id,
                    order_side=OrderSide.BUY,
                    quantity=order_size,
                    price=self._get_best_price(instrument_id, OrderSide.BUY),
                )
                # Stagger orders slightly
                delay = i * 0.1  # 100ms between orders
                self.clock.schedule(
                    callback=lambda: self.submit_order(order),
                    when=self.clock.utc_now() + timedelta(seconds=delay)
                )
```

---

## Integration with Your System

### Step 1: Extend Strategy Config

```python
# backend/strategy.py
class SmartRoutingStrategyConfig(StrategyConfig):
    instrument_id: str
    use_smart_routing: bool = False
    venues: List[Dict] = []
    execution_algorithm: Optional[Dict] = None
```

### Step 2: Create Smart Router Module

```python
# backend/smart_router.py
class SmartOrderRouter:
    # Implementation as shown above
```

### Step 3: Create Execution Algorithms

```python
# backend/execution_algorithms.py
class TWAPExecAlgorithm:
    # Implementation as shown above

class VWAPExecAlgorithm:
    # Implementation as shown above
```

### Step 4: Update Backtest Engine

```python
# backend/backtest_engine.py
def _create_strategy(self, config):
    strategy_config = config["strategy"]
    
    if strategy_config.get("use_smart_routing"):
        from backend.smart_router import SmartOrderRouter
        router = SmartOrderRouter(venues=strategy_config["venues"])
        # Pass router to strategy
```

---

## Best Practices

### 1. Venue Selection

✅ **Do:**
- Compare fees across venues
- Consider liquidity depth
- Monitor fill rates
- Track latency

❌ **Don't:**
- Always use cheapest venue (may have poor liquidity)
- Ignore execution quality
- Route without monitoring

### 2. Order Splitting

✅ **Do:**
- Split large orders to reduce market impact
- Use TWAP for time-based execution
- Use VWAP for volume-based execution
- Monitor child order fills

❌ **Don't:**
- Execute entire large order at once
- Ignore market impact
- Split too aggressively (high fees)

### 3. Execution Patterns

✅ **Do:**
- Match pattern to market conditions
- Use aggressive for urgent trades
- Use passive for non-urgent trades
- Monitor pattern performance

❌ **Don't:**
- Use same pattern for all trades
- Ignore market conditions
- Over-optimize patterns

---

## Summary

### OMS
- ✅ NETTING: Single net position (futures, perpetuals)
- ✅ HEDGING: Separate long/short positions (hedging)

### Smart Routing
- ✅ Venue selection based on fees, liquidity, latency
- ✅ Order splitting across multiple venues
- ✅ Performance tracking and optimization

### Execution Algorithms
- ✅ TWAP: Time-weighted execution
- ✅ VWAP: Volume-weighted execution
- ✅ Implementation Shortfall: Price improvement
- ✅ Custom patterns: Aggressive, passive, iceberg, stealth

### Integration
- ✅ Extend your existing strategy system
- ✅ Add router and algorithms as modules
- ✅ Configure via JSON (matches your architecture)

---

## Next Steps

1. **Implement Smart Router**: Create `backend/smart_router.py`
2. **Add Execution Algorithms**: Create `backend/execution_algorithms.py`
3. **Extend Strategy**: Update `backend/strategy.py` to support routing
4. **Test**: Backtest with multi-venue configs
5. **Monitor**: Track routing performance and optimize

Your system's config-driven architecture makes it easy to add these features! 🚀

