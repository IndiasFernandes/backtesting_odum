"""
Execution algorithms for order management.

Implements TWAP, VWAP, and other execution patterns.
"""
from typing import Optional, List, Dict
from decimal import Decimal
from datetime import timedelta, datetime
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.objects import Quantity, Price
from nautilus_trader.execution.algorithms import ExecAlgorithm, ExecAlgorithmConfig
from nautilus_trader.model.events import OrderFilled


class TWAPExecAlgorithmConfig(ExecAlgorithmConfig):
    """Configuration for TWAP execution algorithm."""
    duration_seconds: int  # Total execution time in seconds
    interval_seconds: int  # Time between child orders in seconds


class TWAPExecAlgorithm(ExecAlgorithm):
    """
    Time-Weighted Average Price execution algorithm.
    
    Splits large order into smaller orders executed evenly over time.
    
    Example:
        Total quantity: 10 BTC
        Duration: 60 minutes
        Interval: 5 minutes
        -> 12 child orders of ~0.83 BTC each, executed every 5 minutes
    """
    
    def __init__(self, config: TWAPExecAlgorithmConfig):
        super().__init__(config)
        self.config = config
        self.child_orders: List = []
        self.start_time: Optional[datetime] = None
        self.total_quantity: Optional[Quantity] = None
        self.remaining_quantity: Optional[Quantity] = None
        self.instrument_id: Optional[InstrumentId] = None
        self.order_side: Optional[OrderSide] = None
        self.limit_price: Optional[Price] = None
    
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
        self.instrument_id = instrument_id
        self.order_side = side
        self.total_quantity = quantity
        self.remaining_quantity = quantity
        self.limit_price = price
        self.start_time = self.clock.utc_now()
        
        # Calculate number of child orders
        num_orders = max(1, self.config.duration_seconds // self.config.interval_seconds)
        child_size = quantity / Decimal(str(num_orders))
        
        self.log.info(
            f"TWAP: Splitting {quantity} into {num_orders} orders of ~{child_size} "
            f"over {self.config.duration_seconds}s"
        )
        
        # Schedule child orders
        for i in range(num_orders):
            order_time = self.start_time + timedelta(seconds=i * self.config.interval_seconds)
            
            # Last order gets remainder
            if i == num_orders - 1:
                order_quantity = self.remaining_quantity
            else:
                order_quantity = child_size
            
            # Create child order
            if price:
                child_order = self.order_factory.limit(
                    instrument_id=instrument_id,
                    order_side=side,
                    quantity=order_quantity,
                    price=price,
                    time_in_force=TimeInForce.GTC,  # Good till cancelled
                )
            else:
                child_order = self.order_factory.market(
                    instrument_id=instrument_id,
                    order_side=side,
                    quantity=order_quantity,
                )
            
            # Schedule for execution
            self.clock.schedule(
                callback=lambda o=child_order: self._submit_child_order(o),
                when=order_time
            )
    
    def _submit_child_order(self, order):
        """Submit scheduled child order."""
        if self.remaining_quantity <= 0:
            self.log.warning("TWAP: Remaining quantity is zero, skipping order")
            return
        
        self.submit_order(order)
        self.child_orders.append(order)
        self.log.info(f"TWAP: Submitted child order {order.client_order_id}")
    
    def on_order_filled(self, event: OrderFilled):
        """Track filled orders."""
        if event.last_qty:
            filled_qty = event.last_qty.as_decimal()
            if self.remaining_quantity:
                self.remaining_quantity -= filled_qty
                self.log.info(
                    f"TWAP: Order filled, remaining: {self.remaining_quantity}"
                )


class VWAPExecAlgorithmConfig(ExecAlgorithmConfig):
    """Configuration for VWAP execution algorithm."""
    duration_seconds: int  # Total execution time
    volume_profile: Dict[int, float]  # Volume distribution by hour (0-23)


class VWAPExecAlgorithm(ExecAlgorithm):
    """
    Volume-Weighted Average Price execution algorithm.
    
    Executes orders proportionally to historical volume distribution.
    """
    
    def __init__(self, config: VWAPExecAlgorithmConfig):
        super().__init__(config)
        self.config = config
        self.child_orders: List = []
        self.total_quantity: Optional[Quantity] = None
        self.instrument_id: Optional[InstrumentId] = None
        self.order_side: Optional[OrderSide] = None
    
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
        self.instrument_id = instrument_id
        self.order_side = side
        self.total_quantity = quantity
        
        # Get volume profile for current time window
        current_hour = self.clock.utc_now().hour
        volume_distribution = self._get_volume_distribution(current_hour)
        
        if not volume_distribution:
            # Fallback to TWAP if no volume profile
            self.log.warning("VWAP: No volume profile, using uniform distribution")
            volume_distribution = self._get_uniform_distribution()
        
        # Normalize distribution
        total_pct = sum(volume_distribution.values())
        if total_pct == 0:
            volume_distribution = self._get_uniform_distribution()
            total_pct = sum(volume_distribution.values())
        
        # Execute proportionally to volume distribution
        start_time = self.clock.utc_now()
        interval_seconds = self.config.duration_seconds // len(volume_distribution)
        
        for i, (time_slot, volume_pct) in enumerate(sorted(volume_distribution.items())):
            normalized_pct = volume_pct / total_pct if total_pct > 0 else 1.0 / len(volume_distribution)
            child_quantity = quantity * Decimal(str(normalized_pct))
            
            if child_quantity <= 0:
                continue
            
            order_time = start_time + timedelta(seconds=i * interval_seconds)
            
            if price:
                child_order = self.order_factory.limit(
                    instrument_id=instrument_id,
                    order_side=side,
                    quantity=child_quantity,
                    price=price,
                    time_in_force=TimeInForce.GTC,
                )
            else:
                child_order = self.order_factory.market(
                    instrument_id=instrument_id,
                    order_side=side,
                    quantity=child_quantity,
                )
            
            # Schedule for execution at time slot
            self.clock.schedule(
                callback=lambda o=child_order: self.submit_order(o),
                when=order_time
            )
    
    def _get_volume_distribution(self, hour: int) -> Dict[int, float]:
        """Get volume distribution for hour."""
        # Use configured volume profile or default
        return self.config.volume_profile.get(hour, {})
    
    def _get_uniform_distribution(self) -> Dict[int, float]:
        """Get uniform volume distribution (fallback)."""
        num_slots = 12  # 12 time slots
        return {i: 1.0 / num_slots for i in range(num_slots)}


class AggressiveBuyPattern:
    """
    Aggressive buy order pattern.
    
    Executes immediately using market orders for fastest fill.
    """
    
    def __init__(self, order_factory):
        self.order_factory = order_factory
    
    def execute(
        self,
        instrument_id: InstrumentId,
        quantity: Quantity
    ):
        """Execute aggressive buy order."""
        order = self.order_factory.market(
            instrument_id=instrument_id,
            order_side=OrderSide.BUY,
            quantity=quantity,
        )
        return order


class PassiveBuyPattern:
    """
    Passive buy order pattern.
    
    Places limit orders at bid price, waits for fill.
    """
    
    def __init__(self, order_factory, cache):
        self.order_factory = order_factory
        self.cache = cache
    
    def execute(
        self,
        instrument_id: InstrumentId,
        quantity: Quantity
    ):
        """Execute passive buy order at bid."""
        # Get current bid from order book
        book = self.cache.order_book(instrument_id)
        if book and book.best_bid_price():
            bid_price = book.best_bid_price()
        else:
            # Fallback: use last trade price
            last_trade = self.cache.trade_tick(instrument_id)
            if last_trade:
                bid_price = last_trade.price * Decimal("0.999")  # 0.1% below last trade
            else:
                raise ValueError(f"No price data available for {instrument_id}")
        
        order = self.order_factory.limit(
            instrument_id=instrument_id,
            order_side=OrderSide.BUY,
            quantity=quantity,
            price=bid_price,
            time_in_force=TimeInForce.GTC,
        )
        return order


class IcebergBuyPattern:
    """
    Iceberg buy order pattern.
    
    Shows small visible size, hides large size.
    """
    
    def __init__(self, order_factory, visible_pct: float = 0.1):
        self.order_factory = order_factory
        self.visible_pct = visible_pct  # Percentage of order to show
    
    def execute(
        self,
        instrument_id: InstrumentId,
        total_quantity: Quantity
    ):
        """Execute iceberg buy order."""
        visible_size = total_quantity * Decimal(str(self.visible_pct))
        hidden_size = total_quantity - visible_size
        
        # Submit visible order
        visible_order = self.order_factory.limit(
            instrument_id=instrument_id,
            order_side=OrderSide.BUY,
            quantity=visible_size,
            price=None,  # Will be set by strategy based on market
        )
        
        return {
            "visible_order": visible_order,
            "hidden_size": hidden_size,
            "total_quantity": total_quantity,
        }

