"""Example: Integrating TradFi data into Nautilus Trader backtest."""
from pathlib import Path
from nautilus_trader.persistence.catalog import ParquetDataCatalog
from nautilus_trader.config import BacktestDataConfig
from nautilus_trader.model.data import DataType
from nautilus_trader.trading.strategy import Strategy, StrategyConfig
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.objects import Quantity, Price

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from tradfi_data_types import TradFiOHLCV, TradFiCorporateAction


class TradFiStrategyConfig(StrategyConfig):
    """Configuration for TradFi strategy."""
    instrument_id: str = "AAPL.NASDAQ"


class TradFiStrategy(Strategy):
    """Example strategy using TradFi data."""
    
    def __init__(self, config: TradFiStrategyConfig):
        super().__init__(config)
        self._instrument_id = config.instrument_id
        self._last_close = None
        self._dividend_count = 0
    
    def on_start(self):
        """Called when strategy starts."""
        self.log.info(f"TradFiStrategy started for {self._instrument_id}")
        
        # Subscribe to TradFi OHLCV data
        self.subscribe_data(
            DataType(TradFiOHLCV, metadata={"exchange": "NASDAQ"}),
        )
        
        # Subscribe to corporate actions
        self.subscribe_data(
            DataType(TradFiCorporateAction, metadata={"action_type": "dividend"}),
        )
    
    def on_data(self, data):
        """Handle custom data updates."""
        if isinstance(data, TradFiOHLCV):
            if data.instrument_id == self._instrument_id:
                self._last_close = data.close
                self.log.info(
                    f"Received OHLCV: {data.bar_type} bar - "
                    f"O:{data.open} H:{data.high} L:{data.low} C:{data.close} V:{data.volume}"
                )
                
                # Simple strategy: buy on upward momentum
                if self._last_close and data.close > data.open:
                    self.log.info(f"Bullish bar detected, considering buy order")
        
        elif isinstance(data, TradFiCorporateAction):
            if data.instrument_id == self._instrument_id:
                self._dividend_count += 1
                self.log.info(
                    f"Corporate action: {data.action_type} - Value: {data.value} "
                    f"on {data.ex_date}"
                )


def example_load_tradfi_data():
    """Example: Load TradFi data into catalog."""
    # Initialize catalog
    catalog_path = Path("./data/parquet")
    catalog_path.mkdir(parents=True, exist_ok=True)
    catalog = ParquetDataCatalog(str(catalog_path))
    
    # Load TradFi OHLCV data from Parquet file
    import pyarrow.parquet as pq
    
    tradfi_file = Path(__file__).parent / "tradfi_sample.parquet"
    if tradfi_file.exists():
        table = pq.read_table(tradfi_file)
        data_objects = TradFiOHLCV.from_catalog(table)
        
        # Write to catalog
        catalog.write_data(data_objects)
        print(f"Loaded {len(data_objects)} TradFi OHLCV records to catalog")
    
    # Load corporate actions
    corporate_actions_file = Path(__file__).parent / "tradfi_corporate_actions_sample.parquet"
    if corporate_actions_file.exists():
        table = pq.read_table(corporate_actions_file)
        data_objects = TradFiCorporateAction.from_catalog(table)
        
        catalog.write_data(data_objects)
        print(f"Loaded {len(data_objects)} corporate actions to catalog")
    
    return catalog


def example_query_tradfi_data(catalog: ParquetDataCatalog):
    """Example: Query TradFi data from catalog."""
    # Query OHLCV data
    ohlcv_data = catalog.query(
        data_cls=TradFiOHLCV,
        start="2024-01-01",
        end="2024-12-31",
        where="exchange == 'NASDAQ'",
    )
    
    print(f"Queried {len(ohlcv_data)} TradFi OHLCV records")
    
    # Query corporate actions
    corporate_actions = catalog.query(
        data_cls=TradFiCorporateAction,
        start="2024-01-01",
        end="2024-12-31",
        where="action_type == 'dividend'",
    )
    
    print(f"Queried {len(corporate_actions)} corporate actions")


if __name__ == "__main__":
    print("TradFi Integration Example")
    print("=" * 50)
    
    # Load data
    catalog = example_load_tradfi_data()
    
    # Query data
    example_query_tradfi_data(catalog)
    
    print("\n✅ TradFi integration example complete!")
    print("\nTo use in a backtest:")
    print("1. Generate sample data: python tradfi_data_generator.py")
    print("2. Load data into catalog (see example_load_tradfi_data)")
    print("3. Configure BacktestDataConfig with TradFi data types")
    print("4. Use TradFiStrategy in your backtest")

