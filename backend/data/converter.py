"""Data conversion utilities for registering raw Parquet files into NautilusTrader catalog."""
import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path
from typing import List, Optional, Union
from datetime import datetime

from nautilus_trader.model.data import TradeTick, OrderBookDeltas, OrderBookDelta
from nautilus_trader.model.identifiers import InstrumentId, TradeId
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.model.enums import AggressorSide, OrderSide, BookAction
from nautilus_trader.persistence.catalog import ParquetDataCatalog


class DataConverter:
    """Converts raw Parquet files to NautilusTrader catalog format."""
    
    @staticmethod
    def convert_trades_parquet_to_catalog(
        parquet_path: Union[Path, pd.DataFrame],
        instrument_id: InstrumentId,
        catalog: ParquetDataCatalog,
        price_precision: int = 2,
        size_precision: int = 3,
        skip_if_exists: bool = True
    ) -> int:
        """
        Convert raw TradeTick Parquet file or DataFrame to catalog format.
        
        NOTE: Data in GCS is already pre-converted to NautilusTrader schema format
        by market-tick-data-handler. This function only converts:
        - DataFrame → TradeTick objects (NautilusTrader requirement)
        - int8 aggressor_side → AggressorSide enum
        - Uses instrument_id parameter (does NOT extract from DataFrame's instrument_key)
        
        Supports multiple Parquet schemas:
        
        1. Pre-converted NautilusTrader format (from GCS):
           - instrument_key (canonical format, NOT used - instrument_id parameter is used)
           - ts_event, ts_init (nanoseconds - already converted)
           - price, size (already renamed from amount)
           - aggressor_side (int8: 1=buy, 2=sell - needs enum conversion)
           - trade_id (already renamed from id)
        
        2. Legacy raw exchange format (for backward compatibility):
           - timestamp (microseconds), local_timestamp, price, amount, side, id
           - exchange, symbol (for instrument_id construction)
        
        Args:
            parquet_path: Path to raw Parquet file (local or GCS path) OR DataFrame
            instrument_id: Instrument ID for the trades (NautilusTrader format)
                          NOTE: This is passed in, NOT extracted from DataFrame's instrument_key
            catalog: ParquetDataCatalog instance to write to
            price_precision: Price decimal precision
            size_precision: Size decimal precision
            skip_if_exists: If True, skip conversion if data already exists (faster)
            
        Returns:
            Number of TradeTick objects written (0 if skipped)
        """
        # Handle DataFrame or file path
        if isinstance(parquet_path, pd.DataFrame):
            df = parquet_path.copy()
            source_info = f"DataFrame ({len(df)} rows)"
        else:
            if not parquet_path.exists():
                raise FileNotFoundError(f"Parquet file not found: {parquet_path}")
            source_info = str(parquet_path)
        
        # OPTIMIZATION: Check if data already exists in catalog for this file
        # Skip conversion if data already exists (major performance improvement)
        if skip_if_exists:
            try:
                # Check if we have data for this instrument
                existing = catalog.query(
                    data_cls=TradeTick,
                    instrument_ids=[instrument_id],
                    limit=1
                )
                if existing:
                    # Data exists - skip conversion for performance
                    if isinstance(parquet_path, pd.DataFrame):
                        print(f"Data already exists in catalog for {instrument_id} (DataFrame: {len(parquet_path)} rows) - skipping conversion for performance")
                    else:
                        file_size_mb = parquet_path.stat().st_size / (1024 * 1024)
                        print(f"Data already exists in catalog for {instrument_id} (file: {file_size_mb:.2f} MB) - skipping conversion for performance")
                    return 0  # Return 0 to indicate no new data was written
            except Exception:
                # If check fails, proceed with conversion
                pass
        
        # Read Parquet file if path provided, otherwise use DataFrame
        if not isinstance(parquet_path, pd.DataFrame):
            # Read Parquet file using PyArrow directly (faster than pandas)
            print(f"Reading Parquet file: {parquet_path}")
            table = pq.read_table(parquet_path)
            df = table.to_pandas()
        else:
            print(f"Using provided DataFrame: {len(df)} rows")
        
        # Detect schema format and map columns
        if 'ts_event' in df.columns:
            # Already in NautilusTrader format
            ts_event_col = 'ts_event'
            ts_init_col = 'ts_init' if 'ts_init' in df.columns else 'ts_event'
            price_col = 'price'
            size_col = 'size'
            aggressor_col = 'aggressor_side'
            trade_id_col = 'trade_id'
            timestamp_unit = 'nanoseconds'  # Already in nanoseconds
        elif 'timestamp' in df.columns:
            # Common exchange format
            ts_event_col = 'timestamp'
            ts_init_col = 'local_timestamp' if 'local_timestamp' in df.columns else 'timestamp'
            price_col = 'price'
            size_col = 'amount'  # Common name for size
            aggressor_col = 'side'
            trade_id_col = 'id'
            timestamp_unit = 'microseconds'  # Common format uses microseconds
        else:
            raise ValueError(f"Unknown Parquet schema. Columns: {df.columns.tolist()}")
        
        # OPTIMIZATION: Use vectorized operations instead of row-by-row iteration
        print(f"Processing {len(df)} rows using vectorized operations...")
        
        # Convert timestamps vectorized
        ts_event_raw = df[ts_event_col].astype('int64')
        ts_init_raw = df[ts_init_col].astype('int64')
        
        if timestamp_unit == 'microseconds':
            ts_event_ns = ts_event_raw * 1000
            ts_init_ns = ts_init_raw * 1000
        elif timestamp_unit == 'milliseconds':
            ts_event_ns = ts_event_raw * 1_000_000
            ts_init_ns = ts_init_raw * 1_000_000
        else:  # nanoseconds
            ts_event_ns = ts_event_raw
            ts_init_ns = ts_init_raw
        
        # Convert prices and sizes vectorized
        prices = df[price_col].astype('float64')
        sizes = df[size_col].astype('float64')
        
        # Map aggressor side vectorized
        # Handles both pre-converted format (int8: 1/2) and legacy format (string: 'buy'/'sell')
        # Convert to string codes first, then map to enum objects when creating TradeTick
        aggressor_str = df[aggressor_col].astype(str).str.upper()
        aggressor_side_codes = aggressor_str.map({
            # Pre-converted format (from market-tick-data-handler)
            '1': 'BUYER',      # int8: 1 = buy
            '2': 'SELLER',     # int8: 2 = sell
            # Legacy string formats (for backward compatibility)
            'BUY': 'BUYER',
            'BUYER': 'BUYER',
            'AGGRESSOR_BUY': 'BUYER',
            'B': 'BUYER',
            'SELL': 'SELLER',
            'SELLER': 'SELLER',
            'AGGRESSOR_SELL': 'SELLER',
            'S': 'SELLER',
        }).fillna('BUYER')  # Default to BUYER (edge case handling)
        
        # Convert trade IDs vectorized
        trade_ids_str = df[trade_id_col].astype(str)
        
        # Create TradeTick objects in batches (more efficient than one-by-one)
        trade_ticks = []
        batch_size = 10000  # Process in batches to avoid memory issues
        
        for i in range(0, len(df), batch_size):
            batch_end = min(i + batch_size, len(df))
            batch_df = df.iloc[i:batch_end]
            batch_ts_event = ts_event_ns.iloc[i:batch_end]
            batch_ts_init = ts_init_ns.iloc[i:batch_end]
            batch_prices = prices.iloc[i:batch_end]
            batch_sizes = sizes.iloc[i:batch_end]
            batch_aggressor = aggressor_side_codes.iloc[i:batch_end]
            batch_trade_ids = trade_ids_str.iloc[i:batch_end]
            
            # Create TradeTick objects for this batch
            for j in range(len(batch_df)):
                try:
                    # Convert aggressor side code to enum
                    aggressor_code = str(batch_aggressor.iloc[j])
                    aggressor_side = AggressorSide.BUYER if aggressor_code == 'BUYER' else AggressorSide.SELLER
                    
                    trade_tick = TradeTick(
                        instrument_id=instrument_id,
                        price=Price(float(batch_prices.iloc[j]), price_precision),
                        size=Quantity(float(batch_sizes.iloc[j]), size_precision),
                        aggressor_side=aggressor_side,
                        trade_id=TradeId(str(batch_trade_ids.iloc[j])),
                        ts_event=int(batch_ts_event.iloc[j]),
                        ts_init=int(batch_ts_init.iloc[j]),
                    )
                    trade_ticks.append(trade_tick)
                except Exception as e:
                    if i + j < 5:  # Only print first few errors
                        print(f"Warning: Skipping row {i+j} due to error: {e}")
                    continue
            
            # Progress indicator
            if (i + batch_size) % 100000 == 0 or batch_end == len(df):
                print(f"  Converted {min(batch_end, len(df))}/{len(df)} trades...")
        
        # Write all trades to catalog at once
        # Note: For very large datasets, we might need to write in batches
        # But ParquetDataCatalog should handle large writes efficiently
        if trade_ticks:
            print(f"Writing {len(trade_ticks)} trades to catalog...")
            try:
                catalog.write_data(trade_ticks)
                print(f"Successfully wrote {len(trade_ticks)} trades to catalog")
                return len(trade_ticks)
            except Exception as e:
                print(f"Error writing to catalog: {e}")
                import traceback
                traceback.print_exc()
                # Try writing in smaller batches as fallback
                batch_size = 50000
                total_written = 0
                for i in range(0, len(trade_ticks), batch_size):
                    batch = trade_ticks[i:i+batch_size]
                    try:
                        catalog.write_data(batch)
                        total_written += len(batch)
                        print(f"Wrote batch {i//batch_size + 1}: {len(batch)} trades (total: {total_written})")
                    except Exception as batch_error:
                        print(f"Error writing batch {i//batch_size + 1}: {batch_error}")
                        break
                return total_written
        
        return 0
    
    @staticmethod
    def convert_orderbook_parquet_to_catalog(
        parquet_path: Union[Path, pd.DataFrame],
        instrument_id: InstrumentId,
        catalog: ParquetDataCatalog,
        is_snapshot: bool = True,
        price_precision: int = 2,
        size_precision: int = 3,
        skip_if_exists: bool = True
    ) -> int:
        """
        Convert raw OrderBook snapshot Parquet file or DataFrame to catalog format.
        
        Expected Parquet schema (book_snapshot_5 format):
        - timestamp (int64): Event timestamp in microseconds
        - local_timestamp (int64): Local timestamp in microseconds
        - asks[0-4].price, asks[0-4].amount: 5 levels of ask prices/sizes
        - bids[0-4].price, bids[0-4].amount: 5 levels of bid prices/sizes
        
        Args:
            parquet_path: Path to raw Parquet file OR DataFrame
            instrument_id: Instrument ID for the order book
            catalog: ParquetDataCatalog instance to write to
            is_snapshot: Whether this is a snapshot (True) or deltas (False)
            price_precision: Price decimal precision
            size_precision: Size decimal precision
            
        Returns:
            Number of OrderBookDeltas objects written
        """
        # Handle DataFrame or file path
        if isinstance(parquet_path, pd.DataFrame):
            df = parquet_path.copy()
            source_info = f"DataFrame ({len(df)} rows)"
        else:
            if not parquet_path.exists():
                raise FileNotFoundError(f"Parquet file not found: {parquet_path}")
            source_info = str(parquet_path)
        
        # OPTIMIZATION: Check if data already exists in catalog for this file
        # Skip conversion if data already exists (major performance improvement)
        if skip_if_exists:
            try:
                # Check if we have orderbook data for this instrument
                existing = catalog.query(
                    data_cls=OrderBookDeltas,
                    instrument_ids=[instrument_id],
                    limit=1
                )
                if existing:
                    # Data exists - skip conversion for performance
                    if isinstance(parquet_path, pd.DataFrame):
                        print(f"Orderbook data already exists in catalog for {instrument_id} (DataFrame: {len(parquet_path)} rows) - skipping conversion for performance")
                    else:
                        file_size_mb = parquet_path.stat().st_size / (1024 * 1024)
                        print(f"Orderbook data already exists in catalog for {instrument_id} (file: {file_size_mb:.2f} MB) - skipping conversion for performance")
                    return 0  # Return 0 to indicate no new data was written
            except Exception:
                # If check fails, proceed with conversion
                pass
        
        # Read Parquet file if path provided, otherwise use DataFrame
        if not isinstance(parquet_path, pd.DataFrame):
            print(f"Reading order book Parquet file: {parquet_path}")
            df = pd.read_parquet(parquet_path)
            print(f"Loaded {len(df)} rows")
        else:
            print(f"Using provided DataFrame: {len(df)} rows")
        
        # Detect timestamp columns
        timestamp_col = None
        local_timestamp_col = None
        for col in ['timestamp', 'ts_event', 'ts']:
            if col in df.columns:
                timestamp_col = col
                break
        
        for col in ['local_timestamp', 'ts_init', 'local_ts']:
            if col in df.columns:
                local_timestamp_col = col
                break
        
        if timestamp_col is None:
            raise ValueError("Could not find timestamp column (expected 'timestamp', 'ts_event', or 'ts')")
        
        if local_timestamp_col is None:
            local_timestamp_col = timestamp_col
        
        # Detect bid/ask columns - support multiple formats:
        # Format 1: asks[0].price, bids[0].price (Tardis format)
        # Format 2: ask_price_0, bid_price_0 (GCS/NautilusTrader format)
        ask_price_cols = [col for col in df.columns if col.startswith('asks[') and col.endswith('].price')]
        ask_amount_cols = [col for col in df.columns if col.startswith('asks[') and col.endswith('].amount')]
        bid_price_cols = [col for col in df.columns if col.startswith('bids[') and col.endswith('].price')]
        bid_amount_cols = [col for col in df.columns if col.startswith('bids[') and col.endswith('].amount')]
        
        # If Format 1 not found, try Format 2 (GCS format: ask_price_0, bid_price_0, ask_size_0, bid_size_0)
        if not ask_price_cols or not bid_price_cols:
            ask_price_cols = [col for col in df.columns if col.startswith('ask_price_')]
            ask_amount_cols = [col for col in df.columns if col.startswith('ask_size_')]
            bid_price_cols = [col for col in df.columns if col.startswith('bid_price_')]
            bid_amount_cols = [col for col in df.columns if col.startswith('bid_size_')]
            
            # Sort by level number (extract number from column name)
            if ask_price_cols:
                ask_price_cols.sort(key=lambda x: int(x.split('_')[-1]) if x.split('_')[-1].isdigit() else 999)
            if ask_amount_cols:
                ask_amount_cols.sort(key=lambda x: int(x.split('_')[-1]) if x.split('_')[-1].isdigit() else 999)
            if bid_price_cols:
                bid_price_cols.sort(key=lambda x: int(x.split('_')[-1]) if x.split('_')[-1].isdigit() else 999)
            if bid_amount_cols:
                bid_amount_cols.sort(key=lambda x: int(x.split('_')[-1]) if x.split('_')[-1].isdigit() else 999)
        else:
            # Sort Format 1 columns by index to maintain order
            ask_price_cols.sort(key=lambda x: int(x.split('[')[1].split(']')[0]))
            ask_amount_cols.sort(key=lambda x: int(x.split('[')[1].split(']')[0]))
            bid_price_cols.sort(key=lambda x: int(x.split('[')[1].split(']')[0]))
            bid_amount_cols.sort(key=lambda x: int(x.split('[')[1].split(']')[0]))
        
        if not ask_price_cols or not bid_price_cols:
            available_cols = ', '.join(df.columns.tolist()[:20])  # Show first 20 columns
            raise ValueError(
                f"Could not find ask/bid price columns.\n"
                f"Expected formats:\n"
                f"  - asks[0].price, bids[0].price (Tardis format)\n"
                f"  - ask_price_0, bid_price_0 (GCS/NautilusTrader format)\n"
                f"Available columns: {available_cols}{'...' if len(df.columns) > 20 else ''}"
            )
        
        print(f"Found {len(ask_price_cols)} ask levels and {len(bid_price_cols)} bid levels")
        
        # Convert to OrderBookDeltas objects
        orderbook_deltas_list = []
        sequence = 0
        
        # Process in batches to avoid memory issues
        batch_size = 10000
        total_written = 0
        
        for batch_start in range(0, len(df), batch_size):
            batch_df = df.iloc[batch_start:batch_start + batch_size]
            batch_deltas = []
            
            for idx, row in batch_df.iterrows():
                try:
                    # Convert timestamps to nanoseconds
                    # Handle both microseconds and nanoseconds
                    ts_event_raw = row[timestamp_col]
                    ts_init_raw = row[local_timestamp_col]
                    
                    # Check if timestamps are already in nanoseconds (ts_event format) or microseconds
                    if timestamp_col == 'ts_event':
                        # Already in nanoseconds
                        ts_event_ns = int(ts_event_raw)
                    else:
                        # Assume microseconds, convert to nanoseconds
                        ts_event_ns = int(ts_event_raw * 1000)
                    
                    if local_timestamp_col == 'ts_init':
                        # Already in nanoseconds
                        ts_init_ns = int(ts_init_raw)
                    else:
                        # Assume microseconds, convert to nanoseconds
                        ts_init_ns = int(ts_init_raw * 1000)
                    
                    # Build deltas list for this snapshot
                    deltas = []
                    
                    # Process asks (sell side)
                    for i, (price_col, amount_col) in enumerate(zip(ask_price_cols, ask_amount_cols)):
                        price_val = row[price_col]
                        amount_val = row[amount_col]
                        
                        # Skip if price/amount is NaN or zero
                        if pd.isna(price_val) or pd.isna(amount_val) or price_val == 0 or amount_val == 0:
                            continue
                        
                        # Create Price and Quantity objects
                        price_obj = Price(float(price_val), price_precision)
                        size_obj = Quantity(float(amount_val), size_precision)
                        
                        # Use from_raw to create OrderBookDelta (positional arguments)
                        delta = OrderBookDelta.from_raw(
                            instrument_id,
                            BookAction.ADD,
                            OrderSide.SELL,
                            price_obj.raw,
                            price_precision,
                            size_obj.raw,
                            size_precision,
                            i,  # Use level index as order ID
                            0,  # flags
                            sequence,
                            ts_event_ns,
                            ts_init_ns,
                        )
                        deltas.append(delta)
                    
                    # Process bids (buy side)
                    for i, (price_col, amount_col) in enumerate(zip(bid_price_cols, bid_amount_cols)):
                        price_val = row[price_col]
                        amount_val = row[amount_col]
                        
                        # Skip if price/amount is NaN or zero
                        if pd.isna(price_val) or pd.isna(amount_val) or price_val == 0 or amount_val == 0:
                            continue
                        
                        # Create Price and Quantity objects
                        price_obj = Price(float(price_val), price_precision)
                        size_obj = Quantity(float(amount_val), size_precision)
                        
                        # Use from_raw to create OrderBookDelta (positional arguments)
                        delta = OrderBookDelta.from_raw(
                            instrument_id,
                            BookAction.ADD,
                            OrderSide.BUY,
                            price_obj.raw,
                            price_precision,
                            size_obj.raw,
                            size_precision,
                            i + 1000,  # Use level index + offset as order ID (different from asks)
                            0,  # flags
                            sequence,
                            ts_event_ns,
                            ts_init_ns,
                        )
                        deltas.append(delta)
                    
                    # Create OrderBookDeltas for this snapshot
                    if deltas:
                        orderbook_deltas = OrderBookDeltas(
                            instrument_id=instrument_id,
                            deltas=deltas,
                            ts_event=ts_event_ns,
                            ts_init=ts_init_ns,
                            sequence=sequence,
                            is_snapshot=is_snapshot,
                        )
                        batch_deltas.append(orderbook_deltas)
                        sequence += 1
                    
                except Exception as e:
                    if idx < 5:  # Only print first few errors
                        print(f"Warning: Skipping row {idx} due to error: {e}")
                    continue
            
            # Write batch to catalog
            if batch_deltas:
                try:
                    catalog.write_data(batch_deltas)
                    total_written += len(batch_deltas)
                    print(f"Wrote batch {batch_start//batch_size + 1}: {len(batch_deltas)} order book snapshots (total: {total_written})")
                except Exception as e:
                    print(f"Error writing batch {batch_start//batch_size + 1}: {e}")
                    import traceback
                    traceback.print_exc()
                    # Try writing in smaller batches
                    smaller_batch_size = 1000
                    for i in range(0, len(batch_deltas), smaller_batch_size):
                        smaller_batch = batch_deltas[i:i+smaller_batch_size]
                        try:
                            catalog.write_data(smaller_batch)
                            total_written += len(smaller_batch)
                        except Exception as batch_error:
                            print(f"Error writing smaller batch: {batch_error}")
                            break
        
        print(f"Successfully converted and registered {total_written} order book snapshots")
        return total_written
    
    @staticmethod
    def register_raw_files(
        trades_path: Optional[Path],
        book_path: Optional[Path],
        instrument_id: InstrumentId,
        catalog: ParquetDataCatalog,
        price_precision: int = 2,
        size_precision: int = 3
    ) -> tuple[int, int]:
        """
        Register raw Parquet files into the catalog.
        
        Args:
            trades_path: Path to trades Parquet file (optional)
            book_path: Path to order book Parquet file (optional)
            instrument_id: Instrument ID
            catalog: ParquetDataCatalog instance
            price_precision: Price decimal precision
            size_precision: Size decimal precision
            
        Returns:
            Tuple of (trades_count, orderbook_count) registered
        """
        trades_count = 0
        orderbook_count = 0
        
        if trades_path and trades_path.exists():
            trades_count = DataConverter.convert_trades_parquet_to_catalog(
                trades_path, instrument_id, catalog, price_precision, size_precision, skip_if_exists=True
            )
        
        if book_path and book_path.exists():
            orderbook_count = DataConverter.convert_orderbook_parquet_to_catalog(
                book_path, instrument_id, catalog, is_snapshot=True, skip_if_exists=True
            )
        
        return trades_count, orderbook_count

