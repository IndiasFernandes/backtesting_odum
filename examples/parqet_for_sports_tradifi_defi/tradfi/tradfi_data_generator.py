"""Generate sample TradFi data for Nautilus Trader."""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import pyarrow.parquet as pq

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from tradfi_data_types import TradFiOHLCV, TradFiCorporateAction


def generate_sample_tradfi_ohlcv(
    start_date: datetime,
    end_date: datetime,
    instrument_id: str = "AAPL.NASDAQ",
    exchange: str = "NASDAQ",
    bar_type: str = "1hour",
    output_path: Path = Path("tradfi_sample.parquet")
) -> None:
    """
    Generate sample TradFi OHLCV data.
    
    Args:
        start_date: Start date for data generation
        end_date: End date for data generation
        instrument_id: Instrument identifier
        exchange: Exchange name
        bar_type: Bar type (1min, 5min, 1hour, 1day)
        output_path: Output Parquet file path
    """
    # Calculate number of bars based on bar_type
    bar_intervals = {
        "1min": timedelta(minutes=1),
        "5min": timedelta(minutes=5),
        "1hour": timedelta(hours=1),
        "1day": timedelta(days=1),
    }
    
    interval = bar_intervals.get(bar_type, timedelta(hours=1))
    current_time = start_date
    bars = []
    
    # Starting price (simulated)
    base_price = 150.0
    
    while current_time < end_date:
        # Generate realistic OHLCV data
        # Use random walk with some trend
        price_change = np.random.normal(0, 0.5)  # Small random change
        base_price += price_change
        
        # OHLC from base price
        open_price = base_price
        high_price = base_price + abs(np.random.normal(0, 1.0))
        low_price = base_price - abs(np.random.normal(0, 1.0))
        close_price = base_price + np.random.normal(0, 0.5)
        
        # Ensure high >= max(open, close) and low <= min(open, close)
        high_price = max(high_price, open_price, close_price)
        low_price = min(low_price, open_price, close_price)
        
        # Volume (random but realistic)
        volume = np.random.uniform(1000000, 10000000)
        
        # Convert datetime to nanoseconds
        ts_event_ns = int(current_time.timestamp() * 1_000_000_000)
        ts_init_ns = ts_event_ns  # Same for simplicity
        
        bar = TradFiOHLCV(
            ts_event=ts_event_ns,
            ts_init=ts_init_ns,
            instrument_id=instrument_id,
            open=round(open_price, 2),
            high=round(high_price, 2),
            low=round(low_price, 2),
            close=round(close_price, 2),
            volume=round(volume, 2),
            bar_type=bar_type,
            exchange=exchange,
        )
        bars.append(bar)
        
        current_time += interval
    
    # Convert to Arrow table and write to Parquet
    table = TradFiOHLCV.to_catalog(bars)
    pq.write_table(table, output_path, compression='zstd')
    
    print(f"Generated {len(bars)} TradFi OHLCV bars")
    print(f"Saved to: {output_path}")
    print(f"Date range: {start_date} to {end_date}")
    print(f"Instrument: {instrument_id} on {exchange}")


def generate_sample_corporate_actions(
    start_date: datetime,
    end_date: datetime,
    instrument_id: str = "AAPL.NASDAQ",
    output_path: Path = Path("tradfi_corporate_actions_sample.parquet")
) -> None:
    """
    Generate sample corporate action data.
    
    Args:
        start_date: Start date for data generation
        end_date: End date for data generation
        instrument_id: Instrument identifier
        output_path: Output Parquet file path
    """
    actions = []
    current_date = start_date
    
    # Generate quarterly dividends
    while current_date < end_date:
        # Quarterly dividend
        dividend_date = current_date + timedelta(days=90)
        if dividend_date > end_date:
            break
        
        ts_event_ns = int(dividend_date.timestamp() * 1_000_000_000)
        ts_init_ns = ts_event_ns
        
        action = TradFiCorporateAction(
            ts_event=ts_event_ns,
            ts_init=ts_init_ns,
            instrument_id=instrument_id,
            action_type="dividend",
            value=round(np.random.uniform(0.20, 0.50), 2),  # $0.20-$0.50 dividend
            ex_date=ts_event_ns,
            record_date=ts_event_ns + int(timedelta(days=2).total_seconds() * 1_000_000_000),
            payment_date=ts_event_ns + int(timedelta(days=30).total_seconds() * 1_000_000_000),
        )
        actions.append(action)
        
        current_date = dividend_date
    
    # Add a stock split example
    split_date = start_date + timedelta(days=180)
    if split_date < end_date:
        ts_event_ns = int(split_date.timestamp() * 1_000_000_000)
        action = TradFiCorporateAction(
            ts_event=ts_event_ns,
            ts_init=ts_event_ns,
            instrument_id=instrument_id,
            action_type="split",
            value=2.0,  # 2:1 split
            ex_date=ts_event_ns,
            record_date=None,
            payment_date=None,
        )
        actions.append(action)
    
    if actions:
        table = TradFiCorporateAction.to_catalog(actions)
        pq.write_table(table, output_path, compression='zstd')
        
        print(f"Generated {len(actions)} corporate actions")
        print(f"Saved to: {output_path}")


if __name__ == "__main__":
    # Generate sample data for the past 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    output_dir = Path(__file__).parent
    output_dir.mkdir(exist_ok=True)
    
    # Generate OHLCV data
    generate_sample_tradfi_ohlcv(
        start_date=start_date,
        end_date=end_date,
        instrument_id="AAPL.NASDAQ",
        exchange="NASDAQ",
        bar_type="1hour",
        output_path=output_dir / "tradfi_sample.parquet"
    )
    
    # Generate corporate actions
    generate_sample_corporate_actions(
        start_date=start_date,
        end_date=end_date,
        instrument_id="AAPL.NASDAQ",
        output_path=output_dir / "tradfi_corporate_actions_sample.parquet"
    )
    
    print("\n✅ TradFi sample data generation complete!")

