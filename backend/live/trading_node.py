"""
Live TradingNode wrapper for NautilusTrader integration.

Purpose: Wrap NautilusTrader TradingNode for live execution on CeFi venues.
Service: Live service only (port 8001)

Handles:
- TradingNode lifecycle (start, stop, reconnect)
- Client factory registration (Binance, Bybit, OKX)
- Event subscriptions (orders, positions, account updates)
- Integration with Unified OMS and Position Tracker
"""
import asyncio
import logging
from typing import Optional, Dict, Any
from nautilus_trader.live.node import TradingNode
from nautilus_trader.adapters.binance import (
    BINANCE,
    BinanceLiveDataClientFactory,
    BinanceLiveExecClientFactory,
)
from nautilus_trader.adapters.bybit import (
    BYBIT,
    BybitLiveDataClientFactory,
    BybitLiveExecClientFactory,
)
from nautilus_trader.adapters.okx import (
    OKX,
    OKXLiveDataClientFactory,
    OKXLiveExecClientFactory,
)
from nautilus_trader.model.events import OrderEvent
from nautilus_trader.model.events.order import (
    OrderSubmitted,
    OrderFilled,
    OrderCancelled,
    OrderRejected,
)

from backend.live.config.trading_node_config import TradingNodeConfigBuilder
from backend.live.config.loader import LiveConfigLoader

logger = logging.getLogger(__name__)


class LiveTradingNode:
    """
    Wrapper for NautilusTrader TradingNode for live execution.
    
    Manages TradingNode lifecycle and integrates with Unified OMS/Position Tracker.
    """
    
    def __init__(self, config_loader: LiveConfigLoader):
        """
        Initialize LiveTradingNode.
        
        Args:
            config_loader: LiveConfigLoader with loaded configuration
        """
        self.config_loader = config_loader
        self.config_builder = TradingNodeConfigBuilder(config_loader)
        self.node: Optional[TradingNode] = None
        self._running = False
        
        # Event handlers (to be set by Unified OMS)
        self._order_event_handler: Optional[callable] = None
        self._position_update_handler: Optional[callable] = None
    
    async def initialize(self):
        """Initialize TradingNode with configuration."""
        try:
            # Build TradingNodeConfig
            config = self.config_builder.build()
            
            # Create TradingNode
            self.node = TradingNode(config=config)
            
            # Register client factories
            self._register_client_factories()
            
            # Build the node
            self.node.build()
            
            logger.info("TradingNode initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize TradingNode: {e}", exc_info=True)
            raise
    
    def _register_client_factories(self):
        """Register client factories for Binance, Bybit, OKX."""
        trading_node_config = self.config_loader.get_trading_node_config()
        
        # Check which clients are configured
        data_clients = trading_node_config.get('data_clients', [])
        exec_clients = trading_node_config.get('exec_clients', [])
        
        client_names = {client.get('name', '').upper() for client in data_clients + exec_clients}
        
        # Register Binance factories
        if 'BINANCE_SPOT' in client_names or 'BINANCE_FUTURES' in client_names:
            self.node.add_data_client_factory(BINANCE, BinanceLiveDataClientFactory())
            self.node.add_exec_client_factory(BINANCE, BinanceLiveExecClientFactory())
            logger.info("Registered Binance client factories")
        
        # Register Bybit factories
        if 'BYBIT' in client_names:
            self.node.add_data_client_factory(BYBIT, BybitLiveDataClientFactory())
            self.node.add_exec_client_factory(BYBIT, BybitLiveExecClientFactory())
            logger.info("Registered Bybit client factories")
        
        # Register OKX factories
        if 'OKX' in client_names:
            self.node.add_data_client_factory(OKX, OKXLiveDataClientFactory())
            self.node.add_exec_client_factory(OKX, OKXLiveExecClientFactory())
            logger.info("Registered OKX client factories")
    
    async def start(self):
        """Start TradingNode."""
        if self.node is None:
            await self.initialize()
        
        if self._running:
            logger.warning("TradingNode is already running")
            return
        
        try:
            # Subscribe to events
            self._subscribe_to_events()
            
            # Start the node
            await self.node.run()
            self._running = True
            
            logger.info("TradingNode started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start TradingNode: {e}", exc_info=True)
            raise
    
    async def stop(self):
        """Stop TradingNode."""
        if not self._running:
            logger.warning("TradingNode is not running")
            return
        
        try:
            await self.node.stop()
            self._running = False
            
            logger.info("TradingNode stopped successfully")
            
        except Exception as e:
            logger.error(f"Failed to stop TradingNode: {e}", exc_info=True)
            raise
    
    def _subscribe_to_events(self):
        """Subscribe to TradingNode events."""
        if self.node is None:
            return
        
        # Subscribe to order events
        # Note: Event subscription will be implemented when Unified OMS is ready
        # For now, this is a placeholder for the event subscription framework
        logger.info("Event subscription framework ready (will be connected to Unified OMS in Phase 4)")
    
    def set_order_event_handler(self, handler: callable):
        """Set handler for order events (to be called by Unified OMS)."""
        self._order_event_handler = handler
    
    def set_position_update_handler(self, handler: callable):
        """Set handler for position updates (to be called by Unified Position Tracker)."""
        self._position_update_handler = handler
    
    async def get_positions(self) -> Dict[str, Any]:
        """
        Get positions from NautilusTrader Portfolio.
        
        Returns:
            Dictionary of positions keyed by canonical_id
        """
        if self.node is None:
            return {}
        
        # Query portfolio for positions
        # This will be implemented when Unified Position Tracker is ready
        # For now, return empty dict
        logger.info("Position sync framework ready (will be implemented in Phase 4)")
        return {}
    
    def is_running(self) -> bool:
        """Check if TradingNode is running."""
        return self._running
    
    def get_node(self) -> Optional[TradingNode]:
        """Get underlying TradingNode instance."""
        return self.node

