"""Result serialization for fast and report modes."""
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from backend.utils.paths import ensure_dir


class ResultSerializer:
    """Serializes backtest results to JSON."""
    
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
        start_str = start.isoformat()
        end_str = end.isoformat()
        if start.tzinfo:
            # Already has timezone info, just ensure it ends with Z
            start_str = start_str.replace('+00:00', 'Z').replace('-00:00', 'Z')
        else:
            start_str = start_str + "Z"
        if end.tzinfo:
            end_str = end_str.replace('+00:00', 'Z').replace('-00:00', 'Z')
        else:
            end_str = end_str + "Z"
        
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
        Save fast mode result to file.
        
        Args:
            result: Serialized result dictionary
            output_dir: Output directory
        
        Returns:
            Path to saved file
        """
        ensure_dir(output_dir)
        output_file = output_dir / f"{result['run_id']}.json"
        
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        return output_file
    
    @staticmethod
    def save_report(result: Dict[str, Any], output_dir: Path) -> Path:
        """
        Save report mode results to directory.
        
        Args:
            result: Serialized result dictionary
            output_dir: Output directory
        
        Returns:
            Path to summary.json file
        """
        run_id = result['run_id']
        run_dir = output_dir / run_id
        ensure_dir(run_dir)
        
        # Save summary
        summary_file = run_dir / "summary.json"
        with open(summary_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        # Save timeline
        timeline_file = run_dir / "timeline.json"
        with open(timeline_file, 'w') as f:
            json.dump(result['timeline'], f, indent=2, default=str)
        
        # Save orders
        orders_file = run_dir / "orders.json"
        with open(orders_file, 'w') as f:
            json.dump(result['orders'], f, indent=2, default=str)
        
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

