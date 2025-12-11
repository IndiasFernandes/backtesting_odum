"""Trade-driven backtest strategy implementation."""
from typing import List, Dict, Any, Optional

from nautilus_trader.model.data import TradeTick
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.objects import Quantity, Price
from nautilus_trader.model.identifiers import ExecAlgorithmId
from nautilus_trader.trading.strategy import Strategy, StrategyConfig
from nautilus_trader.model.events import OrderFilled, OrderDenied, OrderRejected


class TempBacktestStrategyConfig(StrategyConfig):
    """Configuration for TempBacktestStrategy."""
    instrument_id: str
    submission_mode: str = "per_trade_tick"
    use_exec_algorithm: bool = False
    exec_algorithm: Optional[Dict[str, Any]] = None


class TempBacktestStrategy(Strategy):
    """
    Trade-driven strategy that creates one order per trade tick.
    
    Uses submission_mode="per_trade_tick" to ensure deterministic order generation.
    """
    
    def __init__(self, config: TempBacktestStrategyConfig):
        """
        Initialize strategy.
        
        Args:
            config: Strategy configuration
        """
        super().__init__(config)
        self._order_count = 0
        self._instrument_id = InstrumentId.from_str(config.instrument_id)
        # Store fill and rejection events for timeline building
        self._fill_events: List[Dict[str, Any]] = []
        self._rejection_events: List[Dict[str, Any]] = []
        # Execution algorithm configuration
        self._use_exec_algo = getattr(config, 'use_exec_algorithm', False)
        self._exec_algo_config = getattr(config, 'exec_algorithm', None)
    
    def on_start(self) -> None:
        """Called when strategy starts."""
        self.log.info(f"TempBacktestStrategy started for {self._instrument_id}")
        
        # Subscribe to trade ticks for the instrument
        # This is required for the strategy to receive trade tick events
        self.subscribe_trade_ticks(self._instrument_id)
        self.log.info(f"Subscribed to trade ticks for {self._instrument_id}")
    
    def on_trade_tick(self, tick: TradeTick) -> None:
        """
        Handle trade tick - create one order per trade.
        
        This is a trade-driven strategy: for each trade tick received,
        we create exactly one order matching the trade characteristics.
        
        Args:
            tick: Trade tick data containing price, size, and aggressor side
        """
        if tick.instrument_id != self._instrument_id:
            return
        
        # Determine order side from trade aggressor side
        # AggressorSide.BUYER means the buyer was aggressive -> we create a BUY order
        # AggressorSide.SELLER means the seller was aggressive -> we create a SELL order
        aggressor_side = tick.aggressor_side
        if aggressor_side is None:
            # Fallback: default to BUY
            side = OrderSide.BUY
            self.log.warning(f"Trade tick {tick.trade_id} has no aggressor_side, defaulting to BUY")
        else:
            # Map aggressor side to order side
            # BUYER -> BUY order, SELLER -> SELL order
            from nautilus_trader.model.enums import AggressorSide
            if aggressor_side == AggressorSide.BUYER:
                side = OrderSide.BUY
            elif aggressor_side == AggressorSide.SELLER:
                side = OrderSide.SELL
            else:
                # Fallback
                side = OrderSide.BUY
                self.log.warning(f"Unknown aggressor_side {aggressor_side}, defaulting to BUY")
        
        # Use trade size for quantity (one order per trade row)
        quantity = tick.size
        
        # Check if execution algorithm should be used
        exec_algo_type = None
        if self._exec_algo_config:
            if isinstance(self._exec_algo_config, dict):
                exec_algo_type = self._exec_algo_config.get("type", "").upper()
            else:
                exec_algo_type = str(self._exec_algo_config).upper()
        
        # Handle NORMAL mode (market orders, no execution algorithm)
        if exec_algo_type == "NORMAL":
            # NORMAL execution: use market orders without any execution algorithm
            order = self.order_factory.market(
                instrument_id=tick.instrument_id,
                order_side=side,
                quantity=quantity,
                time_in_force=TimeInForce.FOK,  # Fill or Kill
            )
            
            self.log.info(
                f"Submitted order #{self._order_count} (NORMAL mode - market order): "
                f"{side.name} {quantity} @ {tick.price}"
            )
        elif self._use_exec_algo and self._exec_algo_config and exec_algo_type not in ("NORMAL", None):
            # Execution algorithm mode
            exec_algo_params = self._exec_algo_config.get("params", {}) if isinstance(self._exec_algo_config, dict) else {}
            
            # Create order with execution algorithm
            exec_algo_id = ExecAlgorithmId(exec_algo_type)
            
            # For execution algorithms, we typically use market orders or limit orders
            # The algorithm will handle splitting into child orders
            if exec_algo_type == "ICEBERG":
                # Iceberg can work with limit orders
                order = self.order_factory.limit(
                    instrument_id=tick.instrument_id,
                    order_side=side,
                    quantity=quantity,
                    price=tick.price,
                    time_in_force=TimeInForce.GTC,  # Good till cancelled for iceberg
                    exec_algorithm_id=exec_algo_id,
                    exec_algorithm_params=exec_algo_params,
                )
            else:
                # TWAP and VWAP work with market orders
                order = self.order_factory.market(
                    instrument_id=tick.instrument_id,
                    order_side=side,
                    quantity=quantity,
                    time_in_force=TimeInForce.FOK,  # Fill or Kill
                    exec_algorithm_id=exec_algo_id,
                    exec_algorithm_params=exec_algo_params,
                )
            
            self.log.info(
                f"Submitted order #{self._order_count} with {exec_algo_type} execution algorithm: "
                f"{side.name} {quantity} @ {tick.price}"
            )
        else:
            # Default behavior: Submit limit order at the EXACT trade price
            # This ensures the order fills at the exact price from the trade data
            order = self.order_factory.limit(
                instrument_id=tick.instrument_id,
                order_side=side,
                quantity=quantity,
                price=tick.price,  # Use exact trade price from Parquet data
                time_in_force=TimeInForce.IOC,  # Immediate or Cancel - ensures immediate execution at trade price
            )
            
            self.log.info(
                f"Submitted order #{self._order_count}: {side.name} {quantity} @ {tick.price} "
                f"(from trade tick {tick.trade_id}, aggressor={aggressor_side})"
            )
        
        self.submit_order(order)
        self._order_count += 1
    
    def on_order_filled(self, event: OrderFilled) -> None:
        """
        Handle order fill event - capture fill details for timeline.
        
        Args:
            event: OrderFilled event containing fill details
        """
        try:
            fill_data = {
                "order_id": str(event.client_order_id),
                "price": float(event.last_px.as_decimal()) if event.last_px else 0.0,
                "quantity": float(event.last_qty.as_decimal()) if event.last_qty else 0.0,
                "ts_event": event.ts_event,
                "ts_init": event.ts_init,
                "side": event.order_side.name.lower() if hasattr(event.order_side, 'name') else str(event.order_side),
            }
            self._fill_events.append(fill_data)
            self.log.debug(
                f"Order filled: {event.client_order_id} - {fill_data['quantity']} @ {fill_data['price']}"
            )
        except Exception as e:
            self.log.warning(f"Error capturing fill event: {e}")
    
    def on_order_denied(self, event: OrderDenied) -> None:
        """
        Handle order denial event - capture rejection details for timeline.
        
        Args:
            event: OrderDenied event containing denial details
        """
        try:
            rejection_data = {
                "order_id": str(event.client_order_id),
                "reason": str(event.reason) if hasattr(event, 'reason') else "Unknown",
                "ts_event": event.ts_event,
                "ts_init": event.ts_init,
            }
            self._rejection_events.append(rejection_data)
            self.log.debug(
                f"Order denied: {event.client_order_id} - Reason: {rejection_data['reason']}"
            )
        except Exception as e:
            self.log.warning(f"Error capturing denial event: {e}")
    
    def on_order_rejected(self, event: OrderRejected) -> None:
        """
        Handle order rejection event - capture rejection details for timeline.
        
        Args:
            event: OrderRejected event containing rejection details
        """
        try:
            rejection_data = {
                "order_id": str(event.client_order_id),
                "reason": str(event.reason) if hasattr(event, 'reason') else "Unknown",
                "ts_event": event.ts_event,
                "ts_init": event.ts_init,
            }
            self._rejection_events.append(rejection_data)
            self.log.debug(
                f"Order rejected: {event.client_order_id} - Reason: {rejection_data['reason']}"
            )
        except Exception as e:
            self.log.warning(f"Error capturing rejection event: {e}")
    
    def get_fill_events(self) -> List[Dict[str, Any]]:
        """Get all captured fill events."""
        return self._fill_events.copy()
    
    def get_rejection_events(self) -> List[Dict[str, Any]]:
        """Get all captured rejection events."""
        return self._rejection_events.copy()
    
    def on_stop(self) -> None:
        """Called when strategy stops."""
        self.log.info(
            f"TempBacktestStrategy stopped. Total orders: {self._order_count}, "
            f"Fills: {len(self._fill_events)}, Rejections: {len(self._rejection_events)}"
        )

