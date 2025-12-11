"""
UCS Data Loader for loading data from GCS with automatic FUSE detection.

This module provides a unified interface for loading data from either:
1. GCS bucket (via UCS API with byte-range streaming)
2. Local filesystem (via FUSE mount or direct file access)
"""
import os
import asyncio
from pathlib import Path
from datetime import datetime, date
from typing import Optional, List, Dict, Any
import pandas as pd

try:
    from unified_cloud_services import UnifiedCloudService, CloudTarget
    UCS_AVAILABLE = True
except ImportError:
    UCS_AVAILABLE = False
    UnifiedCloudService = None
    CloudTarget = None


class UCSDataLoader:
    """
    Loads data from GCS using UCS with automatic FUSE detection and fallback.
    
    Supports:
    - Byte-range streaming from GCS (efficient for time windows)
    - FUSE mount detection (if available)
    - Direct GCS API access (fallback)
    - Local file access (if FUSE mounted)
    """
    
    def __init__(self, bucket_name: Optional[str] = None):
        """
        Initialize UCS Data Loader.
        
        Args:
            bucket_name: GCS bucket name (defaults to env var)
        """
        if not UCS_AVAILABLE:
            raise ImportError(
                "unified-cloud-services not installed. "
                "Install with: pip install git+https://github.com/IggyIkenna/unified-cloud-services.git"
            )
        
        self.ucs = UnifiedCloudService()
        self.bucket_name = bucket_name or os.getenv("UNIFIED_CLOUD_SERVICES_GCS_BUCKET")
        if not self.bucket_name:
            raise ValueError(
                "GCS bucket name not provided. "
                "Set UNIFIED_CLOUD_SERVICES_GCS_BUCKET env var or pass bucket_name"
            )
        
        self.target = CloudTarget(
            gcs_bucket=self.bucket_name,
            bigquery_dataset="market_data"  # Not used for GCS operations
        )
        
        # Check for FUSE mount
        self.local_path = os.getenv("UNIFIED_CLOUD_LOCAL_PATH", "/app/data_downloads")
        self.use_fuse = self._check_fuse_mount()
        
        if self.use_fuse:
            print(f"✅ FUSE mount detected at: {self.local_path}")
        else:
            print(f"ℹ️  Using direct GCS access (no FUSE mount)")
    
    def _check_fuse_mount(self) -> bool:
        """Check if FUSE mount is available."""
        if not os.path.exists(self.local_path):
            return False
        
        # Check if it's a mount point
        if os.path.ismount(self.local_path):
            return True
        
        # Check if UCS detects FUSE
        try:
            # UCS auto-detects FUSE mounts internally
            # We'll try to use local path first, fall back to API if needed
            return True  # Assume available if path exists
        except Exception:
            return False
    
    def _build_gcs_path(
        self,
        date_str: str,
        data_type: str,
        instrument_id: str
    ) -> str:
        """
        Build GCS path for data file.
        
        Args:
            date_str: Date string in format YYYY-MM-DD
            data_type: 'trades' or 'book_snapshot_5'
            instrument_id: Instrument ID (e.g., 'BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN')
            
        Returns:
            GCS path string
            
        Note: GCS uses raw format (colons and @ symbols as-is), matching the working download script.
        """
        # Use raw format (GCS accepts colons and @ symbols directly)
        # This matches the working download script format
        return f"raw_tick_data/by_date/day-{date_str}/data_type-{data_type}/{instrument_id}.parquet"
    
    def _build_local_path(
        self,
        date_str: str,
        data_type: str,
        instrument_id: str
    ) -> Path:
        """
        Build local path for data file (FUSE mount).
        
        Args:
            date_str: Date string in format YYYY-MM-DD
            data_type: 'trades' or 'book_snapshot_5'
            instrument_id: Instrument ID
            
        Returns:
            Local Path object
        """
        instrument_key = instrument_id.replace(":", "%3A").replace("@", "%40")
        return Path(self.local_path) / "raw_tick_data" / "by_date" / f"day-{date_str}" / f"data_type-{data_type}" / f"{instrument_key}.parquet"
    
    async def load_trades(
        self,
        date_str: str,
        instrument_id: str,
        start_ts: Optional[datetime] = None,
        end_ts: Optional[datetime] = None,
        use_streaming: bool = True
    ) -> pd.DataFrame:
        """
        Load trades data for a specific date and instrument.
        
        Args:
            date_str: Date string in format YYYY-MM-DD
            instrument_id: Instrument ID
            start_ts: Optional start timestamp for byte-range streaming
            end_ts: Optional end timestamp for byte-range streaming
            use_streaming: If True, use byte-range streaming when time window provided
            
        Returns:
            DataFrame with trades data
        """
        # Try FUSE mount first if available
        if self.use_fuse:
            local_path = self._build_local_path(date_str, "trades", instrument_id)
            if local_path.exists():
                print(f"📂 Loading from FUSE mount: {local_path}")
                df = pd.read_parquet(local_path)
                
                # Filter by time window if provided
                if start_ts and end_ts:
                    start_ns = int(start_ts.timestamp() * 1_000_000_000)
                    end_ns = int(end_ts.timestamp() * 1_000_000_000)
                    
                    # Detect timestamp column
                    if 'timestamp' in df.columns:
                        ts_col = 'timestamp'
                        # Convert microseconds to nanoseconds for comparison
                        df_filtered = df[(df[ts_col] * 1000 >= start_ns) & (df[ts_col] * 1000 <= end_ns)]
                    elif 'ts_event' in df.columns:
                        ts_col = 'ts_event'
                        df_filtered = df[(df[ts_col] >= start_ns) & (df[ts_col] <= end_ns)]
                    else:
                        df_filtered = df  # No filtering if timestamp column not found
                    
                    print(f"   Filtered to {len(df_filtered)}/{len(df)} rows in time window")
                    return df_filtered
                
                return df
        
        # Fall back to GCS API
        gcs_path = self._build_gcs_path(date_str, "trades", instrument_id)
        print(f"☁️  Loading from GCS: {gcs_path}")
        
        # Use byte-range streaming if time window provided
        if use_streaming and start_ts and end_ts:
            try:
                print(f"   Using byte-range streaming for time window")
                df = await self.ucs.download_from_gcs_streaming(
                    target=self.target,
                    gcs_path=gcs_path,
                    start_timestamp=start_ts,
                    end_timestamp=end_ts
                )
                return df
            except Exception as e:
                print(f"   ⚠️  Streaming failed, falling back to full download: {e}")
        
        # Full file download
        df = await self.ucs.download_from_gcs(
            target=self.target,
            gcs_path=gcs_path
        )
        return df
    
    async def load_book_snapshots(
        self,
        date_str: str,
        instrument_id: str,
        start_ts: Optional[datetime] = None,
        end_ts: Optional[datetime] = None,
        use_streaming: bool = True
    ) -> pd.DataFrame:
        """
        Load book snapshot data for a specific date and instrument.
        
        Args:
            date_str: Date string in format YYYY-MM-DD
            instrument_id: Instrument ID
            start_ts: Optional start timestamp for byte-range streaming
            end_ts: Optional end timestamp for byte-range streaming
            use_streaming: If True, use byte-range streaming when time window provided
            
        Returns:
            DataFrame with book snapshot data
        """
        # Try FUSE mount first if available
        if self.use_fuse:
            local_path = self._build_local_path(date_str, "book_snapshot_5", instrument_id)
            if local_path.exists():
                print(f"📂 Loading from FUSE mount: {local_path}")
                df = pd.read_parquet(local_path)
                
                # Filter by time window if provided
                if start_ts and end_ts:
                    start_ns = int(start_ts.timestamp() * 1_000_000_000)
                    end_ns = int(end_ts.timestamp() * 1_000_000_000)
                    
                    # Detect timestamp column
                    if 'timestamp' in df.columns:
                        ts_col = 'timestamp'
                        df_filtered = df[(df[ts_col] * 1000 >= start_ns) & (df[ts_col] * 1000 <= end_ns)]
                    elif 'ts_event' in df.columns:
                        ts_col = 'ts_event'
                        df_filtered = df[(df[ts_col] >= start_ns) & (df[ts_col] <= end_ns)]
                    else:
                        df_filtered = df
                    
                    print(f"   Filtered to {len(df_filtered)}/{len(df)} rows in time window")
                    return df_filtered
                
                return df
        
        # Fall back to GCS API
        gcs_path = self._build_gcs_path(date_str, "book_snapshot_5", instrument_id)
        print(f"☁️  Loading from GCS: {gcs_path}")
        
        # Use byte-range streaming if time window provided
        if use_streaming and start_ts and end_ts:
            try:
                print(f"   Using byte-range streaming for time window")
                df = await self.ucs.download_from_gcs_streaming(
                    target=self.target,
                    gcs_path=gcs_path,
                    start_timestamp=start_ts,
                    end_timestamp=end_ts
                )
                return df
            except Exception as e:
                print(f"   ⚠️  Streaming failed, falling back to full download: {e}")
        
        # Full file download
        df = await self.ucs.download_from_gcs(
            target=self.target,
            gcs_path=gcs_path
        )
        return df
    
    async def list_available_dates(
        self,
        instrument_id: str,
        data_type: str = "trades"
    ) -> List[date]:
        """
        List available dates for an instrument and data type.
        
        Args:
            instrument_id: Instrument ID
            data_type: 'trades' or 'book_snapshot_5'
            
        Returns:
            List of available dates
        """
        prefix = "raw_tick_data/by_date/day-"
        
        # Try multiple instrument ID formats (with and without @ suffix)
        instrument_ids_to_try = [
            instrument_id,  # Full ID with @LIN
            instrument_id.split("@")[0] if "@" in instrument_id else instrument_id,  # Without @ suffix
        ]
        
        all_dates = set()
        
        for inst_id in instrument_ids_to_try:
            # Try raw format first (matches working download script), then encoded as fallback
            suffixes_to_try = [
                f"/data_type-{data_type}/{inst_id}.parquet",  # Raw format (matches working script)
                f"/data_type-{data_type}/{inst_id.replace(':', '%3A').replace('@', '%40')}.parquet",  # URL-encoded (fallback)
            ]
            
            for suffix in suffixes_to_try:
                try:
                    dates = await self.ucs.list_gcs_directories(
                        target=self.target,
                        prefix=prefix,
                        delimiter="/",
                        date_format="day-%Y-%m-%d",
                        suffix=suffix
                    )
                    if dates:
                        all_dates.update(dates)
                        # If we found dates with this format, prefer it for future checks
                        break
                except Exception as e:
                    # Try next format
                    continue
        
        return sorted(all_dates) if all_dates else []
    
    def check_local_file_exists(
        self,
        date_str: str,
        instrument_id: str,
        data_type: str = "trades"
    ) -> bool:
        """
        Check if local file exists (FUSE mount).
        
        Args:
            date_str: Date string in format YYYY-MM-DD
            instrument_id: Instrument ID
            data_type: 'trades' or 'book_snapshot_5'
            
        Returns:
            True if file exists locally
        """
        if not self.use_fuse:
            return False
        
        local_path = self._build_local_path(date_str, data_type, instrument_id)
        return local_path.exists()

