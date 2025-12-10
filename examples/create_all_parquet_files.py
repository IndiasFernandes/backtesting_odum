"""Create ALL Parquet files for TradFi, Sports, and DeFi data types compatible with Nautilus Trader."""
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


def create_tradfi_corporate_actions_parquet(output_path: Path):
    """Create TradFi Corporate Actions Parquet file."""
    print("Creating TradFi Corporate Actions Parquet file...")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    current_date = start_date
    
    data = []
    
    # Generate quarterly dividends
    while current_date < end_date:
        dividend_date = current_date + timedelta(days=90)
        if dividend_date > end_date:
            break
        
        ts_event_ns = int(dividend_date.timestamp() * 1_000_000_000)
        
        data.append({
            "ts_event": ts_event_ns,
            "ts_init": ts_event_ns,
            "instrument_id": "AAPL.NASDAQ",
            "action_type": "dividend",
            "value": round(np.random.uniform(0.20, 0.50), 2),
            "ex_date": ts_event_ns,
            "record_date": ts_event_ns + int(timedelta(days=2).total_seconds() * 1_000_000_000),
            "payment_date": ts_event_ns + int(timedelta(days=30).total_seconds() * 1_000_000_000),
        })
        
        current_date = dividend_date
    
    # Add a stock split
    split_date = start_date + timedelta(days=180)
    if split_date < end_date:
        ts_event_ns = int(split_date.timestamp() * 1_000_000_000)
        data.append({
            "ts_event": ts_event_ns,
            "ts_init": ts_event_ns,
            "instrument_id": "AAPL.NASDAQ",
            "action_type": "split",
            "value": 2.0,
            "ex_date": ts_event_ns,
            "record_date": 0,
            "payment_date": 0,
        })
    
    schema = pa.schema([
        pa.field("ts_event", pa.int64()),
        pa.field("ts_init", pa.int64()),
        pa.field("instrument_id", pa.string()),
        pa.field("action_type", pa.string()),
        pa.field("value", pa.float64()),
        pa.field("ex_date", pa.int64()),
        pa.field("record_date", pa.int64()),
        pa.field("payment_date", pa.int64()),
    ])
    
    table = pa.Table.from_pylist(data, schema=schema)
    pq.write_table(table, output_path, compression='zstd')
    
    print(f"✅ Created {len(data)} TradFi Corporate Actions records: {output_path}")
    return len(data)


def create_betting_odds_parquet(output_path: Path, event_ids: list):
    """Create Betting Odds Parquet file."""
    print("Creating Betting Odds Parquet file...")
    
    bookmakers = ["DraftKings", "FanDuel", "BetMGM", "Caesars", "Bet365"]
    data = []
    
    for event_id in event_ids:
        # Generate odds at different times (opening, mid, closing)
        for hour_offset in [0, 12, 24]:
            ts_event_ns = int((datetime.now() - timedelta(hours=hour_offset)).timestamp() * 1_000_000_000)
            
            for bookmaker in bookmakers:
                home_odds = np.random.uniform(1.5, 3.5)
                away_odds = np.random.uniform(1.5, 3.5)
                draw_odds = np.random.uniform(2.5, 4.0)
                
                total_prob = (1/home_odds) + (1/away_odds) + (1/draw_odds)
                implied_prob_home = (1/home_odds) / total_prob
                implied_prob_away = (1/away_odds) / total_prob
                implied_prob_draw = (1/draw_odds) / total_prob
                
                data.append({
                    "ts_event": ts_event_ns,
                    "ts_init": ts_event_ns,
                    "event_id": event_id,
                    "market_type": "moneyline",
                    "bookmaker": bookmaker,
                    "home_odds": round(float(home_odds), 2),
                    "away_odds": round(float(away_odds), 2),
                    "draw_odds": round(float(draw_odds), 2),
                    "implied_probability_home": round(float(implied_prob_home), 4),
                    "implied_probability_away": round(float(implied_prob_away), 4),
                    "implied_probability_draw": round(float(implied_prob_draw), 4),
                })
    
    schema = pa.schema([
        pa.field("ts_event", pa.int64()),
        pa.field("ts_init", pa.int64()),
        pa.field("event_id", pa.string()),
        pa.field("market_type", pa.string()),
        pa.field("bookmaker", pa.string()),
        pa.field("home_odds", pa.float64()),
        pa.field("away_odds", pa.float64()),
        pa.field("draw_odds", pa.float64()),
        pa.field("implied_probability_home", pa.float64()),
        pa.field("implied_probability_away", pa.float64()),
        pa.field("implied_probability_draw", pa.float64()),
    ])
    
    table = pa.Table.from_pylist(data, schema=schema)
    pq.write_table(table, output_path, compression='zstd')
    
    print(f"✅ Created {len(data)} Betting Odds records: {output_path}")
    return len(data)


def create_liquidity_pools_parquet(output_path: Path):
    """Create Liquidity Pools Parquet file."""
    print("Creating Liquidity Pools Parquet file...")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    current_time = start_date
    
    pool_configs = [
        {
            "pool_address": "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",
            "dex": "uniswap",
            "token0": "USDC",
            "token1": "WETH",
            "base_reserve0": 10000000,
            "base_reserve1": 5000,
            "fee_tier": 0.003,
        },
        {
            "pool_address": "0x11b815efB8f581194ae79006d24E0d814B7697F6",
            "dex": "uniswap",
            "token0": "USDC",
            "token1": "USDT",
            "base_reserve0": 50000000,
            "base_reserve1": 50000000,
            "fee_tier": 0.0005,
        },
        {
            "pool_address": "0x8ad599c3A0ff1De082011EFDDc58f1908eb6e6D8",
            "dex": "uniswap",
            "token0": "USDC",
            "token1": "WBTC",
            "base_reserve0": 20000000,
            "base_reserve1": 300,
            "fee_tier": 0.003,
        },
    ]
    
    data = []
    interval = timedelta(hours=1)
    
    while current_time < end_date:
        for pool_config in pool_configs:
            reserve0_change = np.random.uniform(0.95, 1.05)
            reserve1_change = np.random.uniform(0.95, 1.05)
            
            reserve0 = pool_config["base_reserve0"] * reserve0_change
            reserve1 = pool_config["base_reserve1"] * reserve1_change
            price = reserve1 / reserve0 if reserve0 > 0 else 0
            total_liquidity = reserve0 + (reserve1 * price)
            tvl = reserve0 + (reserve1 * price * reserve0 / reserve1) if reserve1 > 0 else reserve0
            
            ts_event_ns = int(current_time.timestamp() * 1_000_000_000)
            
            data.append({
                "ts_event": ts_event_ns,
                "ts_init": ts_event_ns,
                "pool_address": pool_config["pool_address"],
                "dex": pool_config["dex"],
                "token0": pool_config["token0"],
                "token1": pool_config["token1"],
                "reserve0": round(float(reserve0), 2),
                "reserve1": round(float(reserve1), 6),
                "total_liquidity": round(float(total_liquidity), 2),
                "price": round(float(price), 6),
                "fee_tier": pool_config["fee_tier"],
                "tvl": round(float(tvl), 2),
            })
        
        current_time += interval
    
    schema = pa.schema([
        pa.field("ts_event", pa.int64()),
        pa.field("ts_init", pa.int64()),
        pa.field("pool_address", pa.string()),
        pa.field("dex", pa.string()),
        pa.field("token0", pa.string()),
        pa.field("token1", pa.string()),
        pa.field("reserve0", pa.float64()),
        pa.field("reserve1", pa.float64()),
        pa.field("total_liquidity", pa.float64()),
        pa.field("price", pa.float64()),
        pa.field("fee_tier", pa.float64()),
        pa.field("tvl", pa.float64()),
    ])
    
    table = pa.Table.from_pylist(data, schema=schema)
    pq.write_table(table, output_path, compression='zstd')
    
    print(f"✅ Created {len(data)} Liquidity Pool records: {output_path}")
    return len(data)


def main():
    """Create all Parquet files including additional types."""
    print("=" * 60)
    print("Creating ALL Nautilus Trader Compatible Parquet Files")
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
    tradfi_corporate = create_tradfi_corporate_actions_parquet(tradfi_dir / "tradfi_corporate_actions_sample.parquet")
    
    # Create Sports files
    sports_events = create_sports_events_parquet(sports_dir / "sports_sample.parquet")
    
    # Get event IDs for betting odds
    import pyarrow.parquet as pq
    events_table = pq.read_table(sports_dir / "sports_sample.parquet")
    event_ids = [row["event_id"] for row in events_table.to_pylist()]
    
    betting_odds = create_betting_odds_parquet(sports_dir / "sports_betting_odds_sample.parquet", event_ids)
    
    # Create DeFi files
    defi_swaps = create_defi_swaps_parquet(defi_dir / "defi_sample.parquet")
    liquidity_pools = create_liquidity_pools_parquet(defi_dir / "defi_liquidity_pools_sample.parquet")
    
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  TradFi OHLCV: {tradfi_ohlcv} records")
    print(f"  TradFi Corporate Actions: {tradfi_corporate} records")
    print(f"  Sports Events: {sports_events} records")
    print(f"  Betting Odds: {betting_odds} records")
    print(f"  DeFi Swaps: {defi_swaps} records")
    print(f"  Liquidity Pools: {liquidity_pools} records")
    print("=" * 60)
    print("\n✅ All Parquet files created successfully!")
    print("\nFiles created:")
    print(f"  TradFi:")
    print(f"    - {tradfi_dir / 'tradfi_sample.parquet'}")
    print(f"    - {tradfi_dir / 'tradfi_corporate_actions_sample.parquet'}")
    print(f"  Sports:")
    print(f"    - {sports_dir / 'sports_sample.parquet'}")
    print(f"    - {sports_dir / 'sports_betting_odds_sample.parquet'}")
    print(f"  DeFi:")
    print(f"    - {defi_dir / 'defi_sample.parquet'}")
    print(f"    - {defi_dir / 'defi_liquidity_pools_sample.parquet'}")


# Import the functions from the first script
def create_tradfi_ohlcv_parquet(output_path: Path):
    """Create TradFi OHLCV Parquet file."""
    print("Creating TradFi OHLCV Parquet file...")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    current_time = start_date
    
    data = []
    base_price = 150.0
    
    while current_time < end_date:
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


if __name__ == "__main__":
    main()

