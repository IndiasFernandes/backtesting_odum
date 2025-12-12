"""
TradingNode configuration builder for live execution.

Purpose: Build NautilusTrader TradingNodeConfig from JSON configuration.
Service: Live service only (port 8001)

Converts JSON config (from LiveConfigLoader) into NautilusTrader TradingNodeConfig.
"""
from typing import Dict, Any, Optional
from nautilus_trader.config import TradingNodeConfig
from nautilus_trader.config import CacheConfig
from nautilus_trader.config import MessageBusConfig
from nautilus_trader.config import LiveDataEngineConfig
from nautilus_trader.config import LiveRiskEngineConfig
from nautilus_trader.config import LiveExecEngineConfig
from nautilus_trader.config import PortfolioConfig
from nautilus_trader.config import InstrumentProviderConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.adapters.binance import (
    BinanceDataClientConfig,
    BinanceExecClientConfig,
    BinanceAccountType,
)
from nautilus_trader.adapters.bybit import (
    BybitDataClientConfig,
    BybitExecClientConfig,
)
from nautilus_trader.adapters.okx import (
    OKXDataClientConfig,
    OKXExecClientConfig,
    OKXInstrumentType,
    OKXContractType,
)
from nautilus_trader.model.identifiers import TraderId

from backend.live.config.loader import LiveConfigLoader


class TradingNodeConfigBuilder:
    """Builds NautilusTrader TradingNodeConfig from JSON configuration."""
    
    def __init__(self, config_loader: LiveConfigLoader):
        """
        Initialize config builder.
        
        Args:
            config_loader: LiveConfigLoader instance with loaded config
        """
        self.config = config_loader.config
        self.trading_node_config = config_loader.get_trading_node_config()
    
    def build(self) -> TradingNodeConfig:
        """
        Build TradingNodeConfig from JSON configuration.
        
        Returns:
            Configured TradingNodeConfig instance
        """
        # Get trader ID from config or use default
        trader_id = self.trading_node_config.get('trader_id', 'ODUM-LIVE-001')
        
        # Build data clients
        data_clients = self._build_data_clients()
        
        # Build execution clients
        exec_clients = self._build_exec_clients()
        
        # Build portfolio config
        portfolio = self._build_portfolio_config()
        
        # Create TradingNodeConfig
        config = TradingNodeConfig(
            trader_id=TraderId(trader_id),
            logging=LoggingConfig(log_level=self.config.get('logging', {}).get('level', 'INFO')),
            cache=CacheConfig(
                timestamps_as_iso8601=True,
                flush_on_start=False,
            ),
            message_bus=MessageBusConfig(),
            data_engine=LiveDataEngineConfig(),
            risk_engine=LiveRiskEngineConfig(),
            exec_engine=LiveExecEngineConfig(
                reconciliation=True,
                reconciliation_lookback_mins=1440,
                filter_unclaimed_external_orders=False,
            ),
            portfolio=portfolio,
            data_clients=data_clients,
            exec_clients=exec_clients,
        )
        
        return config
    
    def _build_data_clients(self) -> Dict[str, Any]:
        """Build data client configurations."""
        data_clients = {}
        data_clients_config = self.trading_node_config.get('data_clients', [])
        
        for client_config in data_clients_config:
            name = client_config.get('name', '').upper()
            
            if name == 'BINANCE_SPOT':
                data_clients['BINANCE_SPOT'] = BinanceDataClientConfig(
                    api_key=client_config.get('api_key'),
                    api_secret=client_config.get('api_secret'),
                    account_type=BinanceAccountType.SPOT,
                    testnet=client_config.get('testnet', False),
                    base_url_http=client_config.get('base_url'),
                    instrument_provider=InstrumentProviderConfig(load_all=True),
                )
            elif name == 'BINANCE_FUTURES':
                data_clients['BINANCE_FUTURES'] = BinanceDataClientConfig(
                    api_key=client_config.get('api_key'),
                    api_secret=client_config.get('api_secret'),
                    account_type=BinanceAccountType.USDT_FUTURES,
                    testnet=client_config.get('testnet', False),
                    base_url_http=client_config.get('base_url'),
                    instrument_provider=InstrumentProviderConfig(load_all=True),
                )
            elif name == 'BYBIT':
                data_clients['BYBIT'] = BybitDataClientConfig(
                    api_key=client_config.get('api_key'),
                    api_secret=client_config.get('api_secret'),
                    testnet=client_config.get('testnet', False),
                    base_url_http=client_config.get('base_url'),
                    instrument_provider=InstrumentProviderConfig(load_all=True),
                )
            elif name == 'OKX':
                data_clients['OKX'] = OKXDataClientConfig(
                    api_key=client_config.get('api_key'),
                    api_secret=client_config.get('api_secret'),
                    api_passphrase=client_config.get('api_passphrase'),
                    base_url_http=client_config.get('base_url'),
                    instrument_provider=InstrumentProviderConfig(load_all=True),
                    instrument_types=(OKXInstrumentType.SWAP, OKXInstrumentType.SPOT),
                    contract_types=(OKXContractType.LINEAR,),
                    is_demo=client_config.get('is_demo', False),
                )
        
        return data_clients
    
    def _build_exec_clients(self) -> Dict[str, Any]:
        """Build execution client configurations."""
        exec_clients = {}
        exec_clients_config = self.trading_node_config.get('exec_clients', [])
        
        for client_config in exec_clients_config:
            name = client_config.get('name', '').upper()
            
            if name == 'BINANCE_SPOT':
                exec_clients['BINANCE_SPOT'] = BinanceExecClientConfig(
                    api_key=client_config.get('api_key'),
                    api_secret=client_config.get('api_secret'),
                    account_type=BinanceAccountType.SPOT,
                    testnet=client_config.get('testnet', False),
                    base_url_http=client_config.get('base_url'),
                    instrument_provider=InstrumentProviderConfig(load_all=True),
                )
            elif name == 'BINANCE_FUTURES':
                exec_clients['BINANCE_FUTURES'] = BinanceExecClientConfig(
                    api_key=client_config.get('api_key'),
                    api_secret=client_config.get('api_secret'),
                    account_type=BinanceAccountType.USDT_FUTURES,
                    testnet=client_config.get('testnet', False),
                    base_url_http=client_config.get('base_url'),
                    instrument_provider=InstrumentProviderConfig(load_all=True),
                )
            elif name == 'BYBIT':
                exec_clients['BYBIT'] = BybitExecClientConfig(
                    api_key=client_config.get('api_key'),
                    api_secret=client_config.get('api_secret'),
                    testnet=client_config.get('testnet', False),
                    base_url_http=client_config.get('base_url'),
                    instrument_provider=InstrumentProviderConfig(load_all=True),
                )
            elif name == 'OKX':
                exec_clients['OKX'] = OKXExecClientConfig(
                    api_key=client_config.get('api_key'),
                    api_secret=client_config.get('api_secret'),
                    api_passphrase=client_config.get('api_passphrase'),
                    base_url_http=client_config.get('base_url'),
                    base_url_ws=client_config.get('base_url_ws'),
                    instrument_provider=InstrumentProviderConfig(load_all=True),
                    instrument_types=(OKXInstrumentType.SWAP, OKXInstrumentType.SPOT),
                    contract_types=(OKXContractType.LINEAR,),
                    is_demo=client_config.get('is_demo', False),
                )
        
        return exec_clients
    
    def _build_portfolio_config(self) -> PortfolioConfig:
        """Build portfolio configuration."""
        portfolio_config = self.trading_node_config.get('portfolio', {})
        accounts = portfolio_config.get('accounts', [])
        
        # Build account configurations
        account_configs = []
        for account in accounts:
            account_configs.append({
                'account_id': account.get('account_id'),
                'base_currency': account.get('base_currency', 'USDT'),
            })
        
        return PortfolioConfig(accounts=account_configs)

