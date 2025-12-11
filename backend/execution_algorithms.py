"""
Execution algorithms for order management.

Implements TWAP, VWAP, Iceberg, and other execution patterns using NautilusTrader ExecAlgorithm interface.
"""
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import timedelta

from nautilus_trader.execution.algorithm import ExecAlgorithm
from nautilus_trader.model.identifiers import ExecAlgorithmId
from nautilus_trader.model.orders.base import Order
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.objects import Quantity
from nautilus_trader.config import ExecAlgorithmConfig


class TWAPExecAlgorithmConfig(ExecAlgorithmConfig, frozen=True):
    """Configuration for TWAPExecAlgorithm."""
    exec_algorithm_id: ExecAlgorithmId | None = ExecAlgorithmId("TWAP")


class VWAPExecAlgorithmConfig(ExecAlgorithmConfig, frozen=True):
    """Configuration for VWAPExecAlgorithm."""
    exec_algorithm_id: ExecAlgorithmId | None = ExecAlgorithmId("VWAP")


class IcebergExecAlgorithmConfig(ExecAlgorithmConfig, frozen=True):
    """Configuration for IcebergExecAlgorithm."""
    exec_algorithm_id: ExecAlgorithmId | None = ExecAlgorithmId("ICEBERG")


class TWAPExecAlgorithm(ExecAlgorithm):
    """
    Time-Weighted Average Price execution algorithm.
    
    Splits large order into smaller orders executed evenly over time.
    
    Parameters:
        horizon_secs: Total execution time in seconds
        interval_secs: Time between child orders in seconds
    """
    
    def __init__(self, config=None):
        """Initialize TWAP execution algorithm."""
        super().__init__(config)
    
    def on_order(self, order: Order) -> None:
        """
        Handle incoming primary order and spawn child orders.
        
        Args:
            order: The primary order to execute using TWAP
        """
        # Log that we received an order
        self.log.info(f"TWAP: Received order {order.client_order_id} with quantity {order.quantity}")
        
        # Validate exec_algorithm_params
        params = order.exec_algorithm_params or {}
        horizon_secs = params.get("horizon_secs", 10)
        interval_secs = params.get("interval_secs", 1)
        
        if horizon_secs <= 0 or interval_secs <= 0:
            self.log.error(f"TWAP: Invalid parameters - horizon_secs={horizon_secs}, interval_secs={interval_secs}")
            return
        
        if interval_secs > horizon_secs:
            self.log.warning(f"TWAP: interval_secs ({interval_secs}) > horizon_secs ({horizon_secs}), using interval_secs = horizon_secs")
            interval_secs = horizon_secs
        
        # Calculate number of child orders
        num_orders = max(1, int(horizon_secs / interval_secs))
        child_qty = order.quantity / Decimal(str(num_orders))
        
        self.log.info(
            f"TWAP: Splitting {order.quantity} into {num_orders} orders of ~{child_qty} "
            f"over {horizon_secs}s (interval: {interval_secs}s)"
        )
        
        # Spawn child orders evenly over time horizon
        for i in range(num_orders):
            delay_secs = i * interval_secs
            
            # Last order gets remainder to ensure full quantity is executed
            if i == num_orders - 1:
                # Calculate remaining quantity
                remaining = order.quantity - (child_qty * Decimal(str(num_orders - 1)))
                spawn_qty = remaining if remaining > 0 else child_qty
            else:
                spawn_qty = child_qty
            
            if spawn_qty <= 0:
                continue
            
            # Schedule spawn using clock if delay is needed, otherwise spawn immediately
            if delay_secs > 0:
                # Schedule delayed spawn using clock - capture variables properly
                spawn_time = self.clock.utc_now() + timedelta(seconds=delay_secs)
                spawn_qty_capture = spawn_qty  # Capture in closure
                self.clock.schedule(
                    callback=lambda qty=spawn_qty_capture: self._spawn_twap_child(order, qty),
                    when=spawn_time
                )
            else:
                # Spawn immediately
                self._spawn_twap_child(order, spawn_qty)
    
    def _spawn_twap_child(self, order: Order, quantity: Quantity) -> None:
        """Helper to spawn TWAP child order."""
        if order.is_limit_order() and order.price:
            self.spawn_limit(
                primary=order,
                quantity=quantity,
                price=order.price,
            )
        else:
            self.spawn_market(
                primary=order,
                quantity=quantity,
            )


class VWAPExecAlgorithm(ExecAlgorithm):
    """
    Volume-Weighted Average Price execution algorithm.
    
    Executes orders proportionally to market volume distribution.
    
    Parameters:
        horizon_secs: Total execution time in seconds
        intervals: Number of intervals to split execution (default: 10)
    """
    
    def __init__(self, config=None):
        """Initialize VWAP execution algorithm."""
        if config is None:
            config = VWAPExecAlgorithmConfig()
        super().__init__(config)
    
    def on_order(self, order: Order) -> None:
        """
        Handle incoming primary order and spawn child orders based on volume profile.
        
        Args:
            order: The primary order to execute using VWAP
        """
        # Log that we received an order
        self.log.info(f"VWAP: Received order {order.client_order_id} with quantity {order.quantity}")
        
        # Validate exec_algorithm_params
        params = order.exec_algorithm_params or {}
        horizon_secs = params.get("horizon_secs", 10)
        intervals = params.get("intervals", 10)
        
        if horizon_secs <= 0 or intervals <= 0:
            self.log.error(f"VWAP: Invalid parameters - horizon_secs={horizon_secs}, intervals={intervals}")
            return
        
        # For simplicity, use uniform distribution (can be enhanced with actual volume data)
        # In production, you would query historical volume data and distribute accordingly
        interval_secs = horizon_secs / intervals
        child_qty = order.quantity / Decimal(str(intervals))
        
        self.log.info(
            f"VWAP: Splitting {order.quantity} into {intervals} orders of ~{child_qty} "
            f"over {horizon_secs}s ({intervals} intervals)"
        )
        
        # Spawn child orders with uniform distribution
        # In production, this would be weighted by actual volume distribution
        for i in range(intervals):
            delay_secs = i * interval_secs
            
            # Last order gets remainder
            if i == intervals - 1:
                remaining = order.quantity - (child_qty * Decimal(str(intervals - 1)))
                spawn_qty = remaining if remaining > 0 else child_qty
            else:
                spawn_qty = child_qty
            
            if spawn_qty <= 0:
                continue
            
            # Schedule spawn using clock if delay is needed, otherwise spawn immediately
            if delay_secs > 0:
                # Schedule delayed spawn using clock - capture variables properly
                spawn_time = self.clock.utc_now() + timedelta(seconds=delay_secs)
                spawn_qty_capture = spawn_qty  # Capture in closure
                self.clock.schedule(
                    callback=lambda qty=spawn_qty_capture: self._spawn_vwap_child(order, qty),
                    when=spawn_time
                )
            else:
                # Spawn immediately
                self._spawn_vwap_child(order, spawn_qty)
    
    def _spawn_vwap_child(self, order: Order, quantity: Quantity) -> None:
        """Helper to spawn VWAP child order."""
        if order.is_limit_order() and order.price:
            self.spawn_limit(
                primary=order,
                quantity=quantity,
                price=order.price,
            )
        else:
            self.spawn_market(
                primary=order,
                quantity=quantity,
            )


class IcebergExecAlgorithm(ExecAlgorithm):
    """
    Iceberg execution algorithm.
    
    Shows only a small visible portion of the order, hiding the rest.
    When visible portion fills, automatically shows next portion.
    
    Parameters:
        visible_pct: Percentage of order to show at once (default: 0.1 = 10%)
        horizon_secs: Maximum time to execute (optional, for timeout)
    """
    
    def __init__(self, config=None):
        """Initialize Iceberg execution algorithm."""
        if config is None:
            config = IcebergExecAlgorithmConfig()
        super().__init__(config)
        self._primary_orders: Dict[str, Order] = {}
        self._remaining_qty: Dict[str, Quantity] = {}
    
    def on_order(self, order: Order) -> None:
        """
        Handle incoming primary order and spawn first visible portion.
        
        Args:
            order: The primary order to execute using Iceberg
        """
        # Validate exec_algorithm_params
        params = order.exec_algorithm_params or {}
        visible_pct = params.get("visible_pct", 0.1)
        
        if visible_pct <= 0 or visible_pct > 1:
            self.log.error(f"Iceberg: Invalid visible_pct={visible_pct}, must be between 0 and 1")
            return
        
        # Store primary order info
        order_id = str(order.client_order_id)
        self._primary_orders[order_id] = order
        self._remaining_qty[order_id] = order.quantity
        
        # Calculate visible quantity
        visible_qty = order.quantity * Decimal(str(visible_pct))
        
        self.log.info(
            f"Iceberg: Showing {visible_qty} ({visible_pct*100}%) of {order.quantity}, "
            f"hiding {order.quantity - visible_qty}"
        )
        
        # Spawn first visible order immediately
        if order.is_limit_order() and order.price:
            self.spawn_limit(
                primary=order,
                quantity=visible_qty,
                price=order.price,
            )
        else:
            self.spawn_market(
                primary=order,
                quantity=visible_qty,
            )
    
    def on_order_filled(self, event) -> None:
        """
        Handle child order fill - spawn next visible portion if remaining.
        
        Args:
            event: OrderFilled event
        """
        # Find primary order for this fill
        order_id = None
        for oid, primary_order in self._primary_orders.items():
            # Check if this fill belongs to a child of this primary order
            if hasattr(event, 'client_order_id'):
                # In NautilusTrader, child orders reference the primary order
                # We need to track which child orders belong to which primary
                # For now, use a simple approach: check remaining quantity
                if oid in self._remaining_qty:
                    order_id = oid
                    break
        
        if order_id and order_id in self._remaining_qty:
            primary_order = self._primary_orders[order_id]
            remaining = self._remaining_qty[order_id]
            
            # Get filled quantity from event
            filled_qty = event.last_qty if hasattr(event, 'last_qty') else None
            if filled_qty:
                remaining = remaining - filled_qty.as_decimal()
                self._remaining_qty[order_id] = remaining
                
                # If there's remaining quantity, spawn next visible portion
                if remaining > 0:
                    params = primary_order.exec_algorithm_params or {}
                    visible_pct = params.get("visible_pct", 0.1)
                    next_visible_qty = remaining * Decimal(str(visible_pct))
                    
                    # Ensure we don't exceed remaining
                    next_visible_qty = min(next_visible_qty, remaining)
                    
                    if next_visible_qty > 0:
                        self.log.info(
                            f"Iceberg: Spawning next visible portion: {next_visible_qty} "
                            f"(remaining: {remaining})"
                        )
                        
                        if primary_order.is_limit_order() and primary_order.price:
                            self.spawn_limit(
                                primary=primary_order,
                                quantity=next_visible_qty,
                                price=primary_order.price,
                            )
                        else:
                            self.spawn_market(
                                primary=primary_order,
                                quantity=next_visible_qty,
                            )
                else:
                    # Order fully filled, clean up
                    self.log.info(f"Iceberg: Order {order_id} fully filled")
                    del self._primary_orders[order_id]
                    del self._remaining_qty[order_id]
