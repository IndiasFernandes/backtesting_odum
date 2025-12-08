"""Trade-driven backtest strategy implementation."""
from typing import Optional

from nautilus_trader.model.data import TradeTick
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.objects import Quantity, Price
from nautilus_trader.trading.strategy import Strategy, StrategyConfig


class TempBacktestStrategyConfig(StrategyConfig):
    """Configuration for TempBacktestStrategy."""
    instrument_id: str
    submission_mode: str = "per_trade_tick"


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
        
        # Submit limit order at the EXACT trade price to execute exactly as the Parquet trade
        # This ensures the order fills at the exact price from the trade data
        order = self.order_factory.limit(
            instrument_id=tick.instrument_id,
            order_side=side,
            quantity=quantity,
            price=tick.price,  # Use exact trade price from Parquet data
            time_in_force=TimeInForce.IOC,  # Immediate or Cancel - ensures immediate execution at trade price
        )
        
        self.submit_order(order)
        self._order_count += 1
        
        # Use INFO level so we can see order submissions in logs
        self.log.info(
            f"Submitted order #{self._order_count}: {side.name} {quantity} @ {tick.price} "
            f"(from trade tick {tick.trade_id}, aggressor={aggressor_side})"
        )
    
    def on_stop(self) -> None:
        """Called when strategy stops."""
        self.log.info(f"TempBacktestStrategy stopped. Total orders: {self._order_count}")

