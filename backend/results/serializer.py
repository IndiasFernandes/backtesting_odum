"""Result serialization for fast and report modes."""
import json
import time
import uuid
import os
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

# Module-level marker to verify this file is loaded
import sys
print("=" * 80, file=sys.stderr)
print("LOADING backend.results module - NEW VERSION WITH PARQUET SUPPORT", file=sys.stderr)
print(f"File location: {__file__}", file=sys.stderr)
print("=" * 80, file=sys.stderr)

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
    print(f"✓ pandas imported successfully")
except ImportError as e:
    print(f"ERROR: pandas not available: {e}")
    PANDAS_AVAILABLE = False
    pd = None

# Try importing unified-cloud-services for GCS upload
try:
    from unified_cloud_services import UnifiedCloudService, CloudTarget
    from unified_cloud_services.domain.standardized_service import StandardizedDomainCloudService
    UCS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  unified-cloud-services not available: {e}")
    UCS_AVAILABLE = False

from backend.utils.paths import ensure_dir


class ResultSerializer:
    """Serializes backtest results to JSON and uploads to GCS."""
    
    # GCS bucket for execution store
    GCS_BUCKET = os.getenv("EXECUTION_STORE_GCS_BUCKET", "execution-store-cefi-central-element-323112")
    
    @staticmethod
    def _get_gcs_uploader():
        """Get GCS uploader instance if available."""
        if not UCS_AVAILABLE:
            return None
        
        try:
            target = CloudTarget(
                gcs_bucket=ResultSerializer.GCS_BUCKET,
                bigquery_dataset="execution"
            )
            ucs = UnifiedCloudService()
            service = StandardizedDomainCloudService(
                domain="execution",
                cloud_target=target
            )
            return ucs, target
        except Exception as e:
            print(f"⚠️  Warning: Could not initialize GCS uploader: {e}")
            return None
    
    @staticmethod
    async def _upload_file_to_gcs(local_path: Path, gcs_path: str) -> bool:
        """Upload a single file to GCS."""
        if not local_path.exists():
            print(f"⚠️  File not found for GCS upload: {local_path}")
            return False
        
        uploader = ResultSerializer._get_gcs_uploader()
        if not uploader:
            print(f"⚠️  GCS uploader not available, skipping upload")
            return False
        
        ucs, target = uploader
        
        try:
            ext = local_path.suffix.lower()
            if ext == '.json':
                # Read JSON and upload as string
                with open(local_path, 'r') as f:
                    json_string = f.read()
                await ucs.upload_to_gcs(
                    target=target,
                    gcs_path=gcs_path,
                    data=json_string,
                    format='json'
                )
            elif ext == '.parquet' and PANDAS_AVAILABLE:
                # Read Parquet and upload as DataFrame
                df = pd.read_parquet(local_path)
                await ucs.upload_to_gcs(
                    target=target,
                    gcs_path=gcs_path,
                    data=df,
                    format='parquet'
                )
            else:
                print(f"⚠️  Unsupported file type for GCS upload: {ext}")
                return False
            
            print(f"✅ Uploaded to GCS: gs://{ResultSerializer.GCS_BUCKET}/{gcs_path}")
            return True
        except Exception as e:
            print(f"❌ Error uploading {local_path} to GCS: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def _upload_to_gcs_sync(local_path: Path, gcs_path: str) -> bool:
        """Synchronous wrapper for GCS upload."""
        try:
            # Try to get existing event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Loop is running - use thread executor to run async code
                    import concurrent.futures
                    import threading
                    result = [None]
                    exception = [None]
                    
                    def run_async():
                        try:
                            new_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(new_loop)
                            result[0] = new_loop.run_until_complete(
                                ResultSerializer._upload_file_to_gcs(local_path, gcs_path)
                            )
                            new_loop.close()
                        except Exception as e:
                            exception[0] = e
                    
                    thread = threading.Thread(target=run_async)
                    thread.start()
                    thread.join()
                    
                    if exception[0]:
                        raise exception[0]
                    return result[0]
                else:
                    # Loop exists but not running
                    return loop.run_until_complete(
                        ResultSerializer._upload_file_to_gcs(local_path, gcs_path)
                    )
            except RuntimeError:
                # No event loop exists, create new one
                return asyncio.run(ResultSerializer._upload_file_to_gcs(local_path, gcs_path))
        except Exception as e:
            print(f"❌ Error in GCS upload wrapper: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def generate_run_id(venue: str, instrument: str, dataset: str, start: datetime, end: datetime, config_hash: str) -> str:
        """
        Generate unique run ID (short and readable).
        
        Uses NautilusTrader best practices for unique identifiers:
        - Includes venue, instrument, date for organization
        - Includes precise timestamp (with microseconds)
        - Includes config hash to identify configuration
        - Adds unique UUID suffix to ensure uniqueness even for simultaneous runs
        
        Format: VENUE_INSTRUMENT_DATE_TIME_CONFIGHASH_UUID
        Example: BNF_BTC_20230524_02061234_018dd777_c549886d
        
        Args:
            venue: Venue name (e.g., BINANCE-FUTURES)
            instrument: Instrument identifier (e.g., BTCUSDT)
            dataset: Dataset name
            start: Start timestamp
            end: End timestamp
            config_hash: Hash of config file
        
        Returns:
            Unique run ID string (short and readable)
        """
        # Shorten venue name
        venue_short = venue.replace("BINANCE-FUTURES", "BNF").replace("BINANCE", "BN").replace("OKX", "OKX").replace("BYBIT", "BYB").replace("DERIBIT", "DER")
        
        # Shorten instrument (BTCUSDT -> BTC, ETHUSDT -> ETH)
        instrument_short = instrument.replace("USDT", "").replace("BTC", "BTC").replace("ETH", "ETH")
        
        # Compact date format: YYYYMMDD
        date_str = start.strftime("%Y%m%d")
        
        # Compact timestamp: HHMMSS + first 2 digits of microseconds
        timestamp_str = start.strftime("%H%M%S")
        microsecond_str = f"{start.microsecond:06d}"[:2]  # First 2 digits of microseconds
        
        # Short config hash (6 chars)
        config_short = config_hash[:6]
        
        # Short UUID (6 chars) for uniqueness
        unique_suffix = str(uuid.uuid4())[:6]
        
        # Format: VENUE_INSTRUMENT_DATE_TIME_CONFIGHASH_UUID
        return f"{venue_short}_{instrument_short}_{date_str}_{timestamp_str}{microsecond_str}_{config_short}_{unique_suffix}"
    
    @staticmethod
    def serialize_fast(
        run_id: str,
        instrument: str,
        dataset: str,
        start: datetime,
        end: datetime,
        summary: Dict[str, Any],
        config_path: str,
        snapshot_mode: str
    ) -> Dict[str, Any]:
        """
        Serialize fast mode results (minimal summary).
        
        Args:
            run_id: Unique run identifier
            instrument: Instrument identifier
            dataset: Dataset name
            start: Start timestamp
            end: End timestamp
            summary: Summary metrics
            config_path: Path to config file
            snapshot_mode: Snapshot mode used
        
        Returns:
            Serialized result dictionary
        """
        # Format dates properly - if timezone-aware, use UTC format; otherwise add Z
        def format_date(dt: datetime) -> str:
            if dt.tzinfo:
                # Already has timezone info, replace +00:00 with Z
                return dt.isoformat().replace('+00:00', 'Z').replace('-00:00', 'Z')
            else:
                return dt.isoformat() + "Z"
        
        start_str = format_date(start)
        end_str = format_date(end)
        
        # Add execution time (when backtest was run)
        execution_time = datetime.now(timezone.utc)
        
        return {
            "run_id": run_id,
            "mode": "fast",
            "instrument": instrument,
            "dataset": dataset,
            "start": start_str,
            "end": end_str,
            "execution_time": format_date(execution_time),
            "summary": summary,
            "metadata": {
                "config_path": config_path,
                "snapshot_mode": snapshot_mode
            }
        }
    
    @staticmethod
    def serialize_report(
        run_id: str,
        instrument: str,
        dataset: str,
        start: datetime,
        end: datetime,
        summary: Dict[str, Any],
        timeline: List[Dict[str, Any]],
        orders: List[Dict[str, Any]],
        config_path: str,
        snapshot_mode: str,
        catalog_root: str
    ) -> Dict[str, Any]:
        """
        Serialize report mode results (full details).
        
        Args:
            run_id: Unique run identifier
            instrument: Instrument identifier
            dataset: Dataset name
            start: Start timestamp
            end: End timestamp
            summary: Summary metrics
            timeline: Timeline events
            orders: Order details
            config_path: Path to config file
            snapshot_mode: Snapshot mode used
            catalog_root: Catalog root path
        
        Returns:
            Serialized result dictionary
        """
        # Format dates properly - if timezone-aware, use UTC format; otherwise add Z
        def format_date(dt: datetime) -> str:
            if dt.tzinfo:
                # Already has timezone info, replace +00:00 with Z
                return dt.isoformat().replace('+00:00', 'Z').replace('-00:00', 'Z')
            else:
                return dt.isoformat() + "Z"
        
        # Add execution time (when backtest was run)
        execution_time = datetime.now(timezone.utc)
        
        return {
            "run_id": run_id,
            "mode": "report",
            "instrument": instrument,
            "dataset": dataset,
            "start": format_date(start),
            "end": format_date(end),
            "execution_time": format_date(execution_time),
            "summary": summary,
            "timeline": timeline,
            "orders": orders,
            "ticks_path": f"frontend/public/tickdata/{run_id}.json",
            "metadata": {
                "config_path": config_path,
                "snapshot_mode": snapshot_mode,
                "catalog_root": catalog_root
            }
        }
    
    @staticmethod
    def save_fast(result: Dict[str, Any], output_dir: Path) -> Path:
        """
        Save fast mode result to file and upload to GCS.
        
        Args:
            result: Serialized result dictionary
            output_dir: Output directory
        
        Returns:
            Path to saved file
        """
        ensure_dir(output_dir)
        output_file = output_dir / f"{result['run_id']}.json"
        
        # Save locally
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        print(f"✓ Saved fast mode result locally: {output_file}")
        
        # Upload to GCS in fast/ folder
        gcs_path = f"fast/{result['run_id']}.json"
        ResultSerializer._upload_to_gcs_sync(output_file, gcs_path)
        
        return output_file
    
    @staticmethod
    def save_report(result: Dict[str, Any], output_dir: Path) -> Path:
        """
        Save report mode results to directory following the schema:
        - summary.json: High-level results
        - orders.parquet: All orders
        - fills.parquet: All fills/trades
        - positions.parquet: Position timeline
        - equity_curve.parquet: Portfolio value over time
        
        Args:
            result: Serialized result dictionary
            output_dir: Output directory
        
        Returns:
            Path to summary.json file
        """
        # CRITICAL: Print immediately to verify this code path is being executed
        import sys
        print("=" * 80, file=sys.stderr)
        print("NEW save_report METHOD CALLED - PARQUET FORMAT", file=sys.stderr)
        print(f"File: {__file__}", file=sys.stderr)
        print("=" * 80, file=sys.stderr)
        
        # Version marker to verify new code is running
        SAVE_REPORT_VERSION = "2.0-parquet-format"
        print(f"=== ResultSerializer.save_report v{SAVE_REPORT_VERSION} ===")
        print(f"PANDAS_AVAILABLE: {PANDAS_AVAILABLE}")
        
        if not PANDAS_AVAILABLE:
            error_msg = "pandas is required for parquet export but is not available. Please install: pip install pandas pyarrow"
            print(f"ERROR: {error_msg}", file=sys.stderr)
            raise ImportError(error_msg)
        run_id = result['run_id']
        run_dir = output_dir / run_id
        ensure_dir(run_dir)
        
        # Remove old JSON files if they exist (from previous runs with old code)
        old_timeline_file = run_dir / "timeline.json"
        old_orders_file = run_dir / "orders.json"
        if old_timeline_file.exists():
            try:
                old_timeline_file.unlink()
                print(f"Removed old timeline.json file")
            except Exception as e:
                print(f"Warning: Could not remove old timeline.json: {e}")
        if old_orders_file.exists():
            try:
                old_orders_file.unlink()
                print(f"Removed old orders.json file")
            except Exception as e:
                print(f"Warning: Could not remove old orders.json: {e}")
        
        timeline = result.get('timeline', [])
        orders = result.get('orders', [])
        summary = result.get('summary', {})
        
        print(f"Debug: save_report called for run_id={run_id}")
        print(f"Debug: timeline has {len(timeline)} events")
        print(f"Debug: orders has {len(orders)} orders")
        print(f"Debug: Using NEW parquet export format")
        
        # Extract fills from timeline
        # Fills can come from:
        # 1. Fill events (event='Fill')
        # 2. Order events with status='filled' (when Fill events aren't generated)
        fills = []
        for event in timeline:
            event_type = event.get('event', '')
            event_data = event.get('data', {})
            
            if event_type == 'Fill':
                # Direct Fill event
                fills.append({
                    'timestamp': event.get('ts'),
                    'order_id': event_data.get('order_id', ''),
                    'price': event_data.get('price', 0.0),
                    'quantity': event_data.get('quantity', 0.0),
                    'side': event_data.get('side', 'unknown'),
                })
            elif event_type == 'Order' and event_data.get('status') == 'filled':
                # Order event with filled status - treat as fill
                fills.append({
                    'timestamp': event.get('ts'),
                    'order_id': event_data.get('id', ''),
                    'price': event_data.get('price', 0.0),
                    'quantity': event_data.get('amount', 0.0),  # amount in orders = quantity in fills
                    'side': event_data.get('side', 'unknown'),
                })
        
        # Extract order timestamps from timeline
        order_timestamps = {}
        for event in timeline:
            if event.get('event') == 'Order':
                order_data = event.get('data', {})
                order_id = order_data.get('id', '')
                if order_id:
                    order_timestamps[order_id] = event.get('ts', '')
        
        # Convert orders to DataFrame and save as parquet
        try:
            if orders:
                orders_df = pd.DataFrame(orders)
                # Add timestamp from timeline if available
                if 'timestamp' not in orders_df.columns:
                    orders_df['timestamp'] = orders_df['id'].map(order_timestamps)
                    # Fill missing timestamps with start time
                    orders_df['timestamp'] = orders_df['timestamp'].fillna(result.get('start', ''))
                orders_df['timestamp'] = pd.to_datetime(orders_df['timestamp'], errors='coerce')
                orders_parquet_file = run_dir / "orders.parquet"
                orders_df.to_parquet(orders_parquet_file, index=False, engine='pyarrow')
                print(f"✓ Saved {len(orders_df)} orders to {orders_parquet_file}")
            else:
                # Create empty orders parquet file
                orders_df = pd.DataFrame(columns=['id', 'side', 'price', 'amount', 'status', 'timestamp'])
                orders_parquet_file = run_dir / "orders.parquet"
                orders_df.to_parquet(orders_parquet_file, index=False, engine='pyarrow')
                print(f"✓ Created empty orders.parquet file")
        except Exception as e:
            print(f"Error saving orders.parquet: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        # Convert fills to DataFrame and save as parquet
        try:
            print(f"Debug: Extracted {len(fills)} fills from timeline")
            if fills:
                fills_df = pd.DataFrame(fills)
                fills_df['timestamp'] = pd.to_datetime(fills_df['timestamp'])
                fills_parquet_file = run_dir / "fills.parquet"
                fills_df.to_parquet(fills_parquet_file, index=False, engine='pyarrow')
                print(f"✓ Saved {len(fills_df)} fills to {fills_parquet_file}")
            else:
                # Create empty fills parquet file
                fills_df = pd.DataFrame(columns=['timestamp', 'order_id', 'price', 'quantity', 'side'])
                fills_parquet_file = run_dir / "fills.parquet"
                fills_df.to_parquet(fills_parquet_file, index=False, engine='pyarrow')
                print(f"✓ Created empty fills.parquet file")
        except Exception as e:
            print(f"Error saving fills.parquet: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        # Calculate position timeline from fills
        positions = []
        if fills:
            current_position = 0.0
            avg_entry_price = 0.0
            
            for fill in fills:
                timestamp = fill['timestamp']
                price = fill['price']
                quantity = fill['quantity']
                side = fill['side'].lower()
                
                # Determine if buy or sell
                is_buy = side in ['buy', 'long']
                position_change = quantity if is_buy else -quantity
                
                # Update position
                prev_position = current_position
                current_position += position_change
                
                # Calculate average entry price
                if prev_position == 0:
                    # Opening new position
                    avg_entry_price = price
                elif (prev_position > 0 and current_position < 0) or (prev_position < 0 and current_position > 0):
                    # Position flipped (closed and reversed)
                    avg_entry_price = price
                elif prev_position != 0 and (prev_position > 0) == (current_position > 0):
                    # Adding to existing position
                    total_cost = abs(prev_position) * avg_entry_price + abs(position_change) * price
                    avg_entry_price = total_cost / abs(current_position) if current_position != 0 else price
                
                # Calculate unrealized PnL (simplified - assumes current price is fill price)
                unrealized_pnl = 0.0
                if current_position != 0:
                    if current_position > 0:
                        unrealized_pnl = (price - avg_entry_price) * current_position
                    else:
                        unrealized_pnl = (avg_entry_price - price) * abs(current_position)
                
                positions.append({
                    'timestamp': timestamp,
                    'quantity': current_position,
                    'avg_entry_price': avg_entry_price,
                    'current_price': price,
                    'unrealized_pnl': unrealized_pnl,
                })
        
        # Convert positions to DataFrame and save as parquet
        try:
            if positions:
                positions_df = pd.DataFrame(positions)
                positions_df['timestamp'] = pd.to_datetime(positions_df['timestamp'])
                positions_parquet_file = run_dir / "positions.parquet"
                positions_df.to_parquet(positions_parquet_file, index=False, engine='pyarrow')
                print(f"✓ Saved {len(positions_df)} position snapshots to {positions_parquet_file}")
            else:
                # Create empty positions parquet file
                positions_df = pd.DataFrame(columns=['timestamp', 'quantity', 'avg_entry_price', 'current_price', 'unrealized_pnl'])
                positions_parquet_file = run_dir / "positions.parquet"
                positions_df.to_parquet(positions_parquet_file, index=False, engine='pyarrow')
                print(f"✓ Created empty positions.parquet file")
        except Exception as e:
            print(f"Error saving positions.parquet: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        # Calculate equity curve (portfolio value over time) from positions
        equity_curve = []
        starting_balance = summary.get('account', {}).get('starting_balance', 1000000.0)
        
        if positions:
            # Use positions_df we already calculated
            positions_df_sorted = positions_df.sort_values('timestamp')
            
            # Calculate cumulative realized PnL by tracking position changes
            cumulative_realized_pnl = 0.0
            prev_position = 0.0
            prev_avg_entry = 0.0
            
            for _, pos in positions_df_sorted.iterrows():
                timestamp = pos['timestamp']
                current_position = pos['quantity']
                avg_entry_price = pos['avg_entry_price']
                current_price = pos['current_price']
                unrealized_pnl = pos['unrealized_pnl']
                
                # Calculate realized PnL when position flips sign (closing/reversing)
                if prev_position != 0 and (prev_position > 0) != (current_position > 0):
                    # Position flipped - calculate realized PnL
                    closed_qty = abs(prev_position)
                    if prev_position > 0:
                        # Closing long position
                        cumulative_realized_pnl += (current_price - prev_avg_entry) * closed_qty
                    else:
                        # Closing short position
                        cumulative_realized_pnl += (prev_avg_entry - current_price) * closed_qty
                
                # Calculate total portfolio value
                portfolio_value = starting_balance + cumulative_realized_pnl + unrealized_pnl
                
                equity_curve.append({
                    'timestamp': timestamp,
                    'portfolio_value': portfolio_value,
                    'realized_pnl': cumulative_realized_pnl,
                    'unrealized_pnl': unrealized_pnl,
                    'position': current_position,
                    'price': current_price,
                })
                
                prev_position = current_position
                prev_avg_entry = avg_entry_price
        else:
            # No positions - equity curve is flat at starting balance
            if fills and 'fills_df' in locals():
                # Use fill timestamps
                for _, fill in fills_df.sort_values('timestamp').iterrows():
                    equity_curve.append({
                        'timestamp': fill['timestamp'],
                        'portfolio_value': starting_balance,
                        'realized_pnl': 0.0,
                        'unrealized_pnl': 0.0,
                        'position': 0.0,
                        'price': fill['price'],
                    })
            else:
                # No fills either - just add start and end timestamps
                start_time = pd.to_datetime(result.get('start', ''))
                end_time = pd.to_datetime(result.get('end', ''))
                equity_curve.append({
                    'timestamp': start_time,
                    'portfolio_value': starting_balance,
                    'realized_pnl': 0.0,
                    'unrealized_pnl': 0.0,
                    'position': 0.0,
                    'price': 0.0,
                })
                if end_time != start_time:
                    equity_curve.append({
                        'timestamp': end_time,
                        'portfolio_value': starting_balance,
                        'realized_pnl': 0.0,
                        'unrealized_pnl': 0.0,
                        'position': 0.0,
                        'price': 0.0,
                    })
        
        # Convert equity curve to DataFrame and save as parquet
        try:
            if equity_curve:
                equity_df = pd.DataFrame(equity_curve)
                equity_df['timestamp'] = pd.to_datetime(equity_df['timestamp'])
                equity_parquet_file = run_dir / "equity_curve.parquet"
                equity_df.to_parquet(equity_parquet_file, index=False, engine='pyarrow')
                print(f"✓ Saved {len(equity_df)} equity curve points to {equity_parquet_file}")
            else:
                # Create empty equity curve parquet file
                equity_df = pd.DataFrame(columns=['timestamp', 'portfolio_value', 'realized_pnl', 'unrealized_pnl', 'position', 'price'])
                equity_parquet_file = run_dir / "equity_curve.parquet"
                equity_df.to_parquet(equity_parquet_file, index=False, engine='pyarrow')
                print(f"✓ Created empty equity_curve.parquet file")
        except Exception as e:
            print(f"Error saving equity_curve.parquet: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        # Save summary.json (high-level results only, without timeline/orders)
        summary_data = {
            'run_id': result.get('run_id'),
            'mode': result.get('mode'),
            'instrument': result.get('instrument'),
            'dataset': result.get('dataset'),
            'start': result.get('start'),
            'end': result.get('end'),
            'execution_time': result.get('execution_time'),
            'summary': summary,
            'metadata': result.get('metadata', {}),
        }
        summary_file = run_dir / "summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary_data, f, indent=2, default=str)
        
        print(f"✓ Saved summary.json to {summary_file}")
        print(f"✓ Report export complete: summary.json, orders.parquet, fills.parquet, positions.parquet, equity_curve.parquet")
        
        # Upload all files to GCS in report/{run_id}/ folder
        print(f"\n📤 Uploading report results to GCS...")
        base_gcs_path = f"report/{run_id}"
        
        # Upload summary.json
        ResultSerializer._upload_to_gcs_sync(summary_file, f"{base_gcs_path}/summary.json")
        
        # Upload parquet files if they exist
        if orders_parquet_file.exists():
            ResultSerializer._upload_to_gcs_sync(orders_parquet_file, f"{base_gcs_path}/orders.parquet")
        if fills_parquet_file.exists():
            ResultSerializer._upload_to_gcs_sync(fills_parquet_file, f"{base_gcs_path}/fills.parquet")
        if positions_parquet_file.exists():
            ResultSerializer._upload_to_gcs_sync(positions_parquet_file, f"{base_gcs_path}/positions.parquet")
        if equity_parquet_file.exists():
            ResultSerializer._upload_to_gcs_sync(equity_parquet_file, f"{base_gcs_path}/equity_curve.parquet")
        
        print(f"✅ All report files uploaded to GCS: gs://{ResultSerializer.GCS_BUCKET}/{base_gcs_path}/")
        
        return summary_file
    
    @staticmethod
    def save_ticks(ticks: List[Dict[str, Any]], output_dir: Path, run_id: str) -> Path:
        """
        Save tick data to JSON file.
        
        Args:
            ticks: List of tick data dictionaries
            output_dir: Output directory
            run_id: Run identifier
        
        Returns:
            Path to saved ticks file
        """
        ensure_dir(output_dir)
        ticks_file = output_dir / f"{run_id}.json"
        
        with open(ticks_file, 'w') as f:
            json.dump(ticks, f, indent=2, default=str)
        
        return ticks_file

