"""Example: Integrating DeFi data into Nautilus Trader backtest."""
from pathlib import Path
from nautilus_trader.persistence.catalog import ParquetDataCatalog
from nautilus_trader.config import BacktestDataConfig
from nautilus_trader.model.data import DataType
from nautilus_trader.trading.strategy import Strategy, StrategyConfig

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from defi_data_types import DeFiSwap, LiquidityPool


class DeFiStrategyConfig(StrategyConfig):
    """Configuration for DeFi strategy."""
    dex: str = "uniswap"
    pool_address: str = "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640"


class DeFiStrategy(Strategy):
    """Example strategy using DeFi data."""
    
    def __init__(self, config: DeFiStrategyConfig):
        super().__init__(config)
        self._dex = config.dex
        self._pool_address = config.pool_address
        self._swaps = []
        self._pool_snapshots = {}
    
    def on_start(self):
        """Called when strategy starts."""
        self.log.info(f"DeFiStrategy started for {self._dex} - Pool: {self._pool_address}")
        
        # Subscribe to DeFi swaps
        self.subscribe_data(
            DataType(DeFiSwap, metadata={"dex": self._dex}),
        )
        
        # Subscribe to liquidity pool snapshots
        self.subscribe_data(
            DataType(LiquidityPool, metadata={"dex": self._dex}),
        )
    
    def on_data(self, data):
        """Handle custom data updates."""
        if isinstance(data, DeFiSwap):
            if data.dex == self._dex and data.pool_address == self._pool_address:
                self._swaps.append(data)
                self.log.info(
                    f"Swap: {data.amount_in:.2f} {data.token_in} -> "
                    f"{data.amount_out:.6f} {data.token_out} "
                    f"(Price Impact: {data.price_impact:.4%}, Fee: {data.fee:.2f})"
                )
                
                # Simple strategy: detect large swaps (potential arbitrage opportunities)
                if data.amount_in > 50000:
                    self.log.info(f"Large swap detected: {data.amount_in:.2f} {data.token_in}")
        
        elif isinstance(data, LiquidityPool):
            if data.dex == self._dex and data.pool_address == self._pool_address:
                self._pool_snapshots[data.ts_event] = data
                self.log.info(
                    f"Pool snapshot: {data.token0}/{data.token1} - "
                    f"Reserves: {data.reserve0:.2f}/{data.reserve1:.6f}, "
                    f"Price: {data.price:.6f}, TVL: ${data.tvl:,.2f}"
                )
                
                # Simple strategy: monitor TVL changes
                if len(self._pool_snapshots) > 1:
                    prev_snapshot = sorted(self._pool_snapshots.items())[-2][1]
                    tvl_change = data.tvl - prev_snapshot.tvl
                    
                    if abs(tvl_change) > 100000:  # Significant TVL change
                        self.log.info(
                            f"Significant TVL change: ${tvl_change:+,.2f} "
                            f"({tvl_change/prev_snapshot.tvl:.2%})"
                        )


def example_load_defi_data():
    """Example: Load DeFi data into catalog."""
    # Initialize catalog
    catalog_path = Path("./data/parquet")
    catalog_path.mkdir(parents=True, exist_ok=True)
    catalog = ParquetDataCatalog(str(catalog_path))
    
    # Load DeFi swaps from Parquet file
    import pyarrow.parquet as pq
    
    defi_file = Path(__file__).parent / "defi_sample.parquet"
    if defi_file.exists():
        table = pq.read_table(defi_file)
        data_objects = DeFiSwap.from_catalog(table)
        
        # Write to catalog
        catalog.write_data(data_objects)
        print(f"Loaded {len(data_objects)} DeFi swaps to catalog")
    
    # Load liquidity pools
    pools_file = Path(__file__).parent / "defi_liquidity_pools_sample.parquet"
    if pools_file.exists():
        table = pq.read_table(pools_file)
        data_objects = LiquidityPool.from_catalog(table)
        
        catalog.write_data(data_objects)
        print(f"Loaded {len(data_objects)} liquidity pool snapshots to catalog")
    
    return catalog


def example_query_defi_data(catalog: ParquetDataCatalog):
    """Example: Query DeFi data from catalog."""
    # Query DeFi swaps
    swaps = catalog.query(
        data_cls=DeFiSwap,
        start="2024-01-01",
        end="2024-12-31",
        where="dex == 'uniswap'",
    )
    
    print(f"Queried {len(swaps)} DeFi swaps")
    
    # Query liquidity pools
    pools = catalog.query(
        data_cls=LiquidityPool,
        start="2024-01-01",
        end="2024-12-31",
        where="dex == 'uniswap'",
    )
    
    print(f"Queried {len(pools)} liquidity pool snapshots")


if __name__ == "__main__":
    print("DeFi Integration Example")
    print("=" * 50)
    
    # Load data
    catalog = example_load_defi_data()
    
    # Query data
    example_query_defi_data(catalog)
    
    print("\n✅ DeFi integration example complete!")
    print("\nTo use in a backtest:")
    print("1. Generate sample data: python defi_data_generator.py")
    print("2. Load data into catalog (see example_load_defi_data)")
    print("3. Configure BacktestDataConfig with DeFi data types")
    print("4. Use DeFiStrategy in your backtest")

