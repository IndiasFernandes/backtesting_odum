"""Create TradeTick Parquet files optimized for Nautilus Trader catalog upload."""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import secrets

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    import numpy as np
except ImportError as e:
    print(f"Error: Missing required dependencies. Please install: pip install pyarrow numpy")
    print(f"Details: {e}")
    sys.exit(1)


def create_tradfi_trade_ticks_parquet(output_path: Path):
    """Create TradFi TradeTick Parquet file - optimized for catalog."""
    print("Creating TradFi TradeTick Parquet file...")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1)  # One day of tick data
    current_time = start_date
    
    data = []
    base_price = 150.0
    trade_id_counter = 1
    
    # Generate trade ticks every 10 seconds
    interval = timedelta(seconds=10)
    
    while current_time < end_date:
        # Simulate price movement
        price_change = np.random.normal(0, 0.1)
        base_price += price_change
        
        # Ensure price stays realistic
        base_price = max(140.0, min(160.0, base_price))
        
        # Trade size (shares)
        size = np.random.uniform(100, 10000)
        
        # Aggressor side (random buy/sell)
        aggressor_side = np.random.choice(["BUYER", "SELLER"])
        
        ts_event_ns = int(current_time.timestamp() * 1_000_000_000)
        
        data.append({
            "ts_event": ts_event_ns,
            "ts_init": ts_event_ns,
            "instrument_id": "AAPL.NASDAQ",
            "price": round(float(base_price), 2),
            "size": round(float(size), 2),
            "aggressor_side": aggressor_side,
            "trade_id": f"TRADFI_{trade_id_counter:08d}",
        })
        
        current_time += interval
        trade_id_counter += 1
    
    # Sort by ts_event (required for Nautilus Trader)
    data.sort(key=lambda x: x["ts_event"])
    
    # Create Arrow schema matching Nautilus Trader TradeTick format
    schema = pa.schema([
        pa.field("ts_event", pa.int64()),
        pa.field("ts_init", pa.int64()),
        pa.field("instrument_id", pa.string()),
        pa.field("price", pa.float64()),
        pa.field("size", pa.float64()),
        pa.field("aggressor_side", pa.string()),
        pa.field("trade_id", pa.string()),
    ])
    
    table = pa.Table.from_pylist(data, schema=schema)
    pq.write_table(table, output_path, compression='zstd')
    
    print(f"✅ Created {len(data)} TradFi TradeTick records: {output_path}")
    return len(data)


def create_sports_betting_trades_parquet(output_path: Path):
    """Create Sports Betting TradeTick Parquet file - optimized for catalog."""
    print("Creating Sports Betting TradeTick Parquet file...")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1)
    current_time = start_date
    
    data = []
    trade_id_counter = 1
    
    # Sample events (betting markets)
    events = [
        ("football_NFL_20241215_PATRIOTS_vs_BILLS", "moneyline", 1.85, 2.10),
        ("football_NFL_20241215_CHIEFS_vs_BRONCOS", "moneyline", 1.65, 2.35),
        ("football_NFL_20241218_PACKERS_vs_VIKINGS", "moneyline", 1.95, 1.95),
    ]
    
    interval = timedelta(minutes=1)
    
    while current_time < end_date:
        # Random event selection
        event_id, market_type, home_odds, away_odds = events[np.random.randint(0, len(events))]
        
        # Simulate odds movement (betting trades)
        odds_shift = np.random.uniform(-0.05, 0.05)
        current_home_odds = home_odds + odds_shift
        current_away_odds = away_odds - odds_shift
        
        # Bet size (stake amount)
        bet_size = np.random.uniform(10, 1000)
        
        # Side (betting on home or away)
        side = np.random.choice(["BUYER", "SELLER"])  # BUYER = backing, SELLER = laying
        
        # Price is the odds
        price = current_home_odds if side == "BUYER" else current_away_odds
        
        ts_event_ns = int(current_time.timestamp() * 1_000_000_000)
        
        data.append({
            "ts_event": ts_event_ns,
            "ts_init": ts_event_ns,
            "instrument_id": f"{event_id}.{market_type}",
            "price": round(float(price), 2),
            "size": round(float(bet_size), 2),
            "aggressor_side": side,
            "trade_id": f"SPORTS_{trade_id_counter:08d}",
        })
        
        current_time += interval
        trade_id_counter += 1
    
    # Sort by ts_event
    data.sort(key=lambda x: x["ts_event"])
    
    schema = pa.schema([
        pa.field("ts_event", pa.int64()),
        pa.field("ts_init", pa.int64()),
        pa.field("instrument_id", pa.string()),
        pa.field("price", pa.float64()),
        pa.field("size", pa.float64()),
        pa.field("aggressor_side", pa.string()),
        pa.field("trade_id", pa.string()),
    ])
    
    table = pa.Table.from_pylist(data, schema=schema)
    pq.write_table(table, output_path, compression='zstd')
    
    print(f"✅ Created {len(data)} Sports Betting TradeTick records: {output_path}")
    return len(data)


def create_defi_swap_trades_parquet(output_path: Path):
    """Create DeFi Swap TradeTick Parquet file - optimized for catalog."""
    print("Creating DeFi Swap TradeTick Parquet file...")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1)
    current_time = start_date
    
    data = []
    trade_id_counter = 1
    
    # Pool configurations
    pools = [
        ("USDC.WETH.UNISWAP", 2000.0),  # USDC/WETH pool, ETH price
        ("USDC.USDT.UNISWAP", 1.0),     # USDC/USDT pool, stable
        ("USDC.WBTC.UNISWAP", 45000.0), # USDC/WBTC pool, BTC price
    ]
    
    interval = timedelta(seconds=30)
    
    while current_time < end_date:
        # Random pool selection
        pool_id, base_price = pools[np.random.randint(0, len(pools))]
        
        # Price movement
        price_change = np.random.normal(0, base_price * 0.01)  # 1% volatility
        current_price = base_price + price_change
        
        # Swap size (in token0 units)
        swap_size = np.random.uniform(100, 50000)
        
        # Direction (buying token1 with token0 = BUYER, selling token1 for token0 = SELLER)
        aggressor_side = np.random.choice(["BUYER", "SELLER"])
        
        ts_event_ns = int(current_time.timestamp() * 1_000_000_000)
        
        data.append({
            "ts_event": ts_event_ns,
            "ts_init": ts_event_ns,
            "instrument_id": pool_id,
            "price": round(float(current_price), 6),
            "size": round(float(swap_size), 2),
            "aggressor_side": aggressor_side,
            "trade_id": f"DEFI_{trade_id_counter:08d}",
        })
        
        current_time += interval
        trade_id_counter += 1
        
        # Update base price slightly for next iteration
        base_price = current_price
    
    # Sort by ts_event
    data.sort(key=lambda x: x["ts_event"])
    
    schema = pa.schema([
        pa.field("ts_event", pa.int64()),
        pa.field("ts_init", pa.int64()),
        pa.field("instrument_id", pa.string()),
        pa.field("price", pa.float64()),
        pa.field("size", pa.float64()),
        pa.field("aggressor_side", pa.string()),
        pa.field("trade_id", pa.string()),
    ])
    
    table = pa.Table.from_pylist(data, schema=schema)
    pq.write_table(table, output_path, compression='zstd')
    
    print(f"✅ Created {len(data)} DeFi Swap TradeTick records: {output_path}")
    return len(data)


def main():
    """Create all TradeTick Parquet files."""
    print("=" * 60)
    print("Creating TradeTick Parquet Files for Catalog Upload")
    print("=" * 60)
    
    base_dir = Path(__file__).parent
    
    # Create directories
    tradfi_dir = base_dir / "tradfi"
    sports_dir = base_dir / "sports"
    defi_dir = base_dir / "defi"
    
    tradfi_dir.mkdir(exist_ok=True)
    sports_dir.mkdir(exist_ok=True)
    defi_dir.mkdir(exist_ok=True)
    
    # Create TradeTick files
    tradfi_ticks = create_tradfi_trade_ticks_parquet(tradfi_dir / "tradfi_trade_ticks.parquet")
    sports_ticks = create_sports_betting_trades_parquet(sports_dir / "sports_trade_ticks.parquet")
    defi_ticks = create_defi_swap_trades_parquet(defi_dir / "defi_trade_ticks.parquet")
    
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  TradFi TradeTicks: {tradfi_ticks} records")
    print(f"  Sports TradeTicks: {sports_ticks} records")
    print(f"  DeFi TradeTicks: {defi_ticks} records")
    print("=" * 60)
    print("\n✅ All TradeTick Parquet files created successfully!")
    print("\nFiles created:")
    print(f"  - {tradfi_dir / 'tradfi_trade_ticks.parquet'}")
    print(f"  - {sports_dir / 'sports_trade_ticks.parquet'}")
    print(f"  - {defi_dir / 'defi_trade_ticks.parquet'}")
    print("\nThese files are optimized for direct catalog upload using:")
    print("  catalog.write_data() or DataConverter.convert_trades_parquet_to_catalog()")


if __name__ == "__main__":
    main()

