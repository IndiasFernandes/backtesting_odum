"""Create Parquet files for TradFi, Sports, and DeFi data types compatible with Nautilus Trader."""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import secrets

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent / "tradfi"))
sys.path.insert(0, str(Path(__file__).parent / "sports"))
sys.path.insert(0, str(Path(__file__).parent / "defi"))

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    import numpy as np
except ImportError as e:
    print(f"Error: Missing required dependencies. Please install: pip install pyarrow numpy")
    print(f"Details: {e}")
    sys.exit(1)


def create_tradfi_ohlcv_parquet(output_path: Path):
    """Create TradFi OHLCV Parquet file."""
    print("Creating TradFi OHLCV Parquet file...")
    
    # Generate sample data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    current_time = start_date
    
    data = []
    base_price = 150.0
    
    # Generate hourly bars
    while current_time < end_date:
        # Simulate price movement
        price_change = np.random.normal(0, 0.5)
        base_price += price_change
        
        open_price = base_price
        high_price = base_price + abs(np.random.normal(0, 1.0))
        low_price = base_price - abs(np.random.normal(0, 1.0))
        close_price = base_price + np.random.normal(0, 0.5)
        
        high_price = max(high_price, open_price, close_price)
        low_price = min(low_price, open_price, close_price)
        volume = np.random.uniform(1000000, 10000000)
        
        ts_event_ns = int(current_time.timestamp() * 1_000_000_000)
        
        data.append({
            "ts_event": ts_event_ns,
            "ts_init": ts_event_ns,
            "instrument_id": "AAPL.NASDAQ",
            "open": round(float(open_price), 2),
            "high": round(float(high_price), 2),
            "low": round(float(low_price), 2),
            "close": round(float(close_price), 2),
            "volume": round(float(volume), 2),
            "bar_type": "1hour",
            "exchange": "NASDAQ",
        })
        
        current_time += timedelta(hours=1)
    
    # Create Arrow schema
    schema = pa.schema([
        pa.field("ts_event", pa.int64()),
        pa.field("ts_init", pa.int64()),
        pa.field("instrument_id", pa.string()),
        pa.field("open", pa.float64()),
        pa.field("high", pa.float64()),
        pa.field("low", pa.float64()),
        pa.field("close", pa.float64()),
        pa.field("volume", pa.float64()),
        pa.field("bar_type", pa.string()),
        pa.field("exchange", pa.string()),
    ])
    
    # Create table and write
    table = pa.Table.from_pylist(data, schema=schema)
    pq.write_table(table, output_path, compression='zstd')
    
    print(f"✅ Created {len(data)} TradFi OHLCV records: {output_path}")
    return len(data)


def create_sports_events_parquet(output_path: Path):
    """Create Sports Events Parquet file."""
    print("Creating Sports Events Parquet file...")
    
    end_date = datetime.now() + timedelta(days=7)
    start_date = end_date - timedelta(days=30)
    current_date = start_date
    
    teams = [
        ("Patriots", "Bills"),
        ("Chiefs", "Broncos"),
        ("Packers", "Vikings"),
        ("Cowboys", "Giants"),
        ("49ers", "Rams"),
    ]
    
    data = []
    team_idx = 0
    
    while current_date < end_date:
        home_team, away_team = teams[team_idx % len(teams)]
        event_id = f"football_NFL_{current_date.strftime('%Y%m%d')}_{secrets.token_hex(4)}"
        
        event_datetime = current_date.replace(hour=19, minute=0, second=0)
        event_date_ns = int(event_datetime.timestamp() * 1_000_000_000)
        
        if current_date < datetime.now():
            status = "finished"
            home_score = np.random.randint(10, 35)
            away_score = np.random.randint(10, 35)
        elif current_date.date() == datetime.now().date():
            status = "live"
            home_score = np.random.randint(0, 21)
            away_score = np.random.randint(0, 21)
        else:
            status = "scheduled"
            home_score = 0
            away_score = 0
        
        ts_event_ns = int(current_date.timestamp() * 1_000_000_000)
        
        data.append({
            "ts_event": ts_event_ns,
            "ts_init": ts_event_ns,
            "event_id": event_id,
            "sport": "football",
            "league": "NFL",
            "home_team": home_team,
            "away_team": away_team,
            "home_score": home_score if status != "scheduled" else 0,
            "away_score": away_score if status != "scheduled" else 0,
            "status": status,
            "venue": f"{home_team} Stadium",
            "event_date": event_date_ns,
        })
        
        current_date += timedelta(days=3)
        team_idx += 1
    
    schema = pa.schema([
        pa.field("ts_event", pa.int64()),
        pa.field("ts_init", pa.int64()),
        pa.field("event_id", pa.string()),
        pa.field("sport", pa.string()),
        pa.field("league", pa.string()),
        pa.field("home_team", pa.string()),
        pa.field("away_team", pa.string()),
        pa.field("home_score", pa.int64()),
        pa.field("away_score", pa.int64()),
        pa.field("status", pa.string()),
        pa.field("venue", pa.string()),
        pa.field("event_date", pa.int64()),
    ])
    
    table = pa.Table.from_pylist(data, schema=schema)
    pq.write_table(table, output_path, compression='zstd')
    
    print(f"✅ Created {len(data)} Sports Events records: {output_path}")
    return len(data)


def create_defi_swaps_parquet(output_path: Path):
    """Create DeFi Swaps Parquet file."""
    print("Creating DeFi Swaps Parquet file...")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    current_time = start_date
    
    data = []
    block_number = 18000000
    
    pool_address = "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640"
    
    while current_time < end_date:
        amount_in = np.random.uniform(1000, 100000)
        base_price = 2000.0 + np.random.normal(0, 50)
        amount_out = amount_in / base_price
        price_impact = min(0.001 * (amount_in / 10000), 0.05)
        fee = amount_in * 0.003
        
        tx_hash = "0x" + secrets.token_hex(32)
        trader = "0x" + secrets.token_hex(20)
        
        ts_event_ns = int(current_time.timestamp() * 1_000_000_000)
        
        data.append({
            "ts_event": ts_event_ns,
            "ts_init": ts_event_ns,
            "transaction_hash": tx_hash,
            "block_number": block_number,
            "dex": "uniswap",
            "pool_address": pool_address,
            "token_in": "USDC",
            "token_out": "WETH",
            "amount_in": round(float(amount_in), 2),
            "amount_out": round(float(amount_out), 6),
            "price_impact": round(float(price_impact), 6),
            "fee": round(float(fee), 2),
            "trader": trader,
        })
        
        current_time += timedelta(minutes=5)
        block_number += np.random.randint(1, 5)
    
    schema = pa.schema([
        pa.field("ts_event", pa.int64()),
        pa.field("ts_init", pa.int64()),
        pa.field("transaction_hash", pa.string()),
        pa.field("block_number", pa.int64()),
        pa.field("dex", pa.string()),
        pa.field("pool_address", pa.string()),
        pa.field("token_in", pa.string()),
        pa.field("token_out", pa.string()),
        pa.field("amount_in", pa.float64()),
        pa.field("amount_out", pa.float64()),
        pa.field("price_impact", pa.float64()),
        pa.field("fee", pa.float64()),
        pa.field("trader", pa.string()),
    ])
    
    table = pa.Table.from_pylist(data, schema=schema)
    pq.write_table(table, output_path, compression='zstd')
    
    print(f"✅ Created {len(data)} DeFi Swap records: {output_path}")
    return len(data)


def main():
    """Create all Parquet files."""
    print("=" * 60)
    print("Creating Nautilus Trader Compatible Parquet Files")
    print("=" * 60)
    
    base_dir = Path(__file__).parent
    
    # Create directories
    tradfi_dir = base_dir / "tradfi"
    sports_dir = base_dir / "sports"
    defi_dir = base_dir / "defi"
    
    tradfi_dir.mkdir(exist_ok=True)
    sports_dir.mkdir(exist_ok=True)
    defi_dir.mkdir(exist_ok=True)
    
    # Create TradFi files
    tradfi_ohlcv = create_tradfi_ohlcv_parquet(tradfi_dir / "tradfi_sample.parquet")
    
    # Create Sports files
    sports_events = create_sports_events_parquet(sports_dir / "sports_sample.parquet")
    
    # Create DeFi files
    defi_swaps = create_defi_swaps_parquet(defi_dir / "defi_sample.parquet")
    
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  TradFi OHLCV: {tradfi_ohlcv} records")
    print(f"  Sports Events: {sports_events} records")
    print(f"  DeFi Swaps: {defi_swaps} records")
    print("=" * 60)
    print("\n✅ All Parquet files created successfully!")
    print("\nFiles created:")
    print(f"  - {tradfi_dir / 'tradfi_sample.parquet'}")
    print(f"  - {sports_dir / 'sports_sample.parquet'}")
    print(f"  - {defi_dir / 'defi_sample.parquet'}")


if __name__ == "__main__":
    main()

