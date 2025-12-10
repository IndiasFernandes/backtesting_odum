"""Upload all Parquet files to Nautilus Trader catalog - optimized for best practices."""
import sys
from pathlib import Path
from typing import List

try:
    from nautilus_trader.persistence.catalog import ParquetDataCatalog
    from nautilus_trader.model.data import TradeTick
    from nautilus_trader.model.identifiers import InstrumentId
    import pyarrow.parquet as pq
except ImportError as e:
    print(f"Error: Missing required dependencies. Please install: pip install nautilus-trader pyarrow")
    print(f"Details: {e}")
    sys.exit(1)

# Add paths for custom data types
sys.path.insert(0, str(Path(__file__).parent / "tradfi"))
sys.path.insert(0, str(Path(__file__).parent / "sports"))
sys.path.insert(0, str(Path(__file__).parent / "defi"))

try:
    from tradfi_data_types import TradFiOHLCV, TradFiCorporateAction
    from sports_data_types import SportsEvent, BettingOdds
    from defi_data_types import DeFiSwap, LiquidityPool
except ImportError as e:
    print(f"Warning: Could not import custom data types: {e}")
    print("Make sure data type files are in the correct directories")


def upload_trade_ticks_to_catalog(
    catalog: ParquetDataCatalog,
    parquet_path: Path,
    instrument_id: InstrumentId,
    price_precision: int = 2,
    size_precision: int = 3
) -> int:
    """
    Upload TradeTick Parquet file to catalog.
    
    This is optimized for Nautilus Trader's expected format.
    """
    if not parquet_path.exists():
        print(f"⚠️  File not found: {parquet_path}")
        return 0
    
    print(f"📥 Loading TradeTick file: {parquet_path.name}")
    
    # Read Parquet file
    table = pq.read_table(parquet_path)
    df = table.to_pandas()
    
    # Convert to TradeTick objects
    from nautilus_trader.model.data import TradeTick
    from nautilus_trader.model.objects import Price, Quantity
    from nautilus_trader.model.enums import AggressorSide
    from nautilus_trader.model.identifiers import TradeId
    
    trade_ticks = []
    
    for _, row in df.iterrows():
        # Map aggressor side
        aggressor_str = str(row['aggressor_side']).upper()
        aggressor_side = AggressorSide.BUYER if aggressor_str == 'BUYER' else AggressorSide.SELLER
        
        trade_tick = TradeTick(
            instrument_id=instrument_id,
            price=Price(float(row['price']), price_precision),
            size=Quantity(float(row['size']), size_precision),
            aggressor_side=aggressor_side,
            trade_id=TradeId(str(row['trade_id'])),
            ts_event=int(row['ts_event']),
            ts_init=int(row['ts_init']),
        )
        trade_ticks.append(trade_tick)
    
    # Write to catalog in batches for performance
    batch_size = 10000
    total_written = 0
    
    for i in range(0, len(trade_ticks), batch_size):
        batch = trade_ticks[i:i+batch_size]
        catalog.write_data(batch)
        total_written += len(batch)
        print(f"  ✅ Wrote batch {i//batch_size + 1}: {len(batch)} trades")
    
    print(f"  ✅ Total: {total_written} TradeTick records uploaded")
    return total_written


def upload_custom_data_to_catalog(
    catalog: ParquetDataCatalog,
    parquet_path: Path,
    data_class: type
) -> int:
    """Upload custom data type Parquet file to catalog."""
    if not parquet_path.exists():
        print(f"⚠️  File not found: {parquet_path}")
        return 0
    
    print(f"📥 Loading {data_class.__name__} file: {parquet_path.name}")
    
    # Read Parquet file
    table = pq.read_table(parquet_path)
    
    # Convert using from_catalog method
    data_objects = data_class.from_catalog(table)
    
    # Write to catalog
    catalog.write_data(data_objects)
    
    print(f"  ✅ Uploaded {len(data_objects)} {data_class.__name__} records")
    return len(data_objects)


def main():
    """Upload all Parquet files to catalog."""
    print("=" * 70)
    print("Uploading All Parquet Files to Nautilus Trader Catalog")
    print("=" * 70)
    
    # Initialize catalog
    catalog_path = Path("./data/parquet")
    catalog_path.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📂 Catalog path: {catalog_path.absolute()}")
    catalog = ParquetDataCatalog(str(catalog_path))
    
    base_dir = Path(__file__).parent
    
    # Upload TradeTick files
    print("\n" + "=" * 70)
    print("UPLOADING TRADETICK FILES")
    print("=" * 70)
    
    tradfi_ticks_path = base_dir / "tradfi" / "tradfi_trade_ticks.parquet"
    if tradfi_ticks_path.exists():
        instrument_id = InstrumentId.from_str("AAPL.NASDAQ")
        upload_trade_ticks_to_catalog(catalog, tradfi_ticks_path, instrument_id)
    
    sports_ticks_path = base_dir / "sports" / "sports_trade_ticks.parquet"
    if sports_ticks_path.exists():
        instrument_id = InstrumentId.from_str("SPORTS.BETTING")
        upload_trade_ticks_to_catalog(catalog, sports_ticks_path, instrument_id)
    
    defi_ticks_path = base_dir / "defi" / "defi_trade_ticks.parquet"
    if defi_ticks_path.exists():
        instrument_id = InstrumentId.from_str("USDC.WETH.UNISWAP")
        upload_trade_ticks_to_catalog(catalog, defi_ticks_path, instrument_id, price_precision=6)
    
    # Upload TradFi custom data
    print("\n" + "=" * 70)
    print("UPLOADING TRADFI CUSTOM DATA")
    print("=" * 70)
    
    tradfi_dir = base_dir / "tradfi"
    if (tradfi_dir / "tradfi_sample.parquet").exists():
        upload_custom_data_to_catalog(catalog, tradfi_dir / "tradfi_sample.parquet", TradFiOHLCV)
    if (tradfi_dir / "tradfi_corporate_actions_sample.parquet").exists():
        upload_custom_data_to_catalog(catalog, tradfi_dir / "tradfi_corporate_actions_sample.parquet", TradFiCorporateAction)
    
    # Upload Sports custom data
    print("\n" + "=" * 70)
    print("UPLOADING SPORTS CUSTOM DATA")
    print("=" * 70)
    
    sports_dir = base_dir / "sports"
    if (sports_dir / "sports_sample.parquet").exists():
        upload_custom_data_to_catalog(catalog, sports_dir / "sports_sample.parquet", SportsEvent)
    if (sports_dir / "sports_betting_odds_sample.parquet").exists():
        upload_custom_data_to_catalog(catalog, sports_dir / "sports_betting_odds_sample.parquet", BettingOdds)
    
    # Upload DeFi custom data
    print("\n" + "=" * 70)
    print("UPLOADING DEFI CUSTOM DATA")
    print("=" * 70)
    
    defi_dir = base_dir / "defi"
    if (defi_dir / "defi_sample.parquet").exists():
        upload_custom_data_to_catalog(catalog, defi_dir / "defi_sample.parquet", DeFiSwap)
    if (defi_dir / "defi_liquidity_pools_sample.parquet").exists():
        upload_custom_data_to_catalog(catalog, defi_dir / "defi_liquidity_pools_sample.parquet", LiquidityPool)
    
    print("\n" + "=" * 70)
    print("✅ ALL FILES UPLOADED TO CATALOG SUCCESSFULLY!")
    print("=" * 70)
    print(f"\nCatalog location: {catalog_path.absolute()}")
    print("\nYou can now use these data types in your backtests:")
    print("  - TradeTick (for all three: TradFi, Sports, DeFi)")
    print("  - TradFiOHLCV, TradFiCorporateAction")
    print("  - SportsEvent, BettingOdds")
    print("  - DeFiSwap, LiquidityPool")


if __name__ == "__main__":
    main()

