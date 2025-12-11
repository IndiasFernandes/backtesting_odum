"""
Data availability checker for validating data exists before backtest.

Checks both local files and GCS bucket based on data_source.
"""
import os
from pathlib import Path
from datetime import datetime, date
from typing import Dict, Any, Optional, List
import asyncio

try:
    from backend.data.loader import UCSDataLoader
    UCS_AVAILABLE = True
except ImportError:
    UCS_AVAILABLE = False
    UCSDataLoader = None


def _convert_instrument_id_to_gcs_format(instrument_id: str) -> str:
    """
    Convert instrument ID from config format to GCS format.
    
    Uses the centralized instrument_registry for conversion.
    """
    from backend.instruments.utils import convert_instrument_id_to_gcs_format
    return convert_instrument_id_to_gcs_format(instrument_id)


class DataAvailabilityChecker:
    """Checks data availability for a given time window and instrument."""
    
    def __init__(self, data_source: str = "gcs"):
        """
        Initialize data checker.
        
        Args:
            data_source: 'local' or 'gcs' (default: 'gcs')
        """
        # Handle 'auto' - prefer GCS
        if data_source == "auto":
            data_source = "gcs"
        
        self.data_source = data_source
        self.ucs_loader: Optional[UCSDataLoader] = None
        self.ucs_error: Optional[str] = None
        
        # Store the requested source (before any fallback)
        self.requested_source = data_source
        
        if data_source == "gcs":
            if not UCS_AVAILABLE:
                # If UCS is not available, keep "gcs" as source but mark error
                import sys
                print(f"⚠️  unified-cloud-services not installed. GCS checks will fail.", file=sys.stderr)
                self.data_source = "gcs"  # Keep as "gcs" to show user's intent
                self.ucs_error = "unified-cloud-services not installed. Install with: pip install git+https://github.com/IggyIkenna/unified-cloud-services.git"
            else:
                try:
                    self.ucs_loader = UCSDataLoader()
                except Exception as e:
                    error_msg = str(e)
                    self.ucs_error = error_msg
                    print(f"⚠️  Failed to initialize UCS loader: {error_msg}")
                    # Keep as "gcs" to show user's intent, but mark error
                    self.data_source = "gcs"
    
    def _extract_date_from_window(self, start: datetime, end: datetime) -> date:
        """Extract date from time window (use start date)."""
        return start.date() if hasattr(start, 'date') else start.date()
    
    def _build_local_path(
        self,
        date_str: str,
        instrument_id: str,
        data_type: str
    ) -> Path:
        """Build local file path."""
        base_path_str = os.getenv("UNIFIED_CLOUD_LOCAL_PATH", "/app/data_downloads")
        base_path = Path(base_path_str).resolve()
        
        # Try both encoded and non-encoded versions
        # Some systems store files with colons, others URL-encode them
        instrument_key_encoded = instrument_id.replace(":", "%3A").replace("@", "%40")
        instrument_key_raw = instrument_id
        
        # Return path with encoded version first (most common)
        return base_path / "raw_tick_data" / "by_date" / f"day-{date_str}" / f"data_type-{data_type}" / f"{instrument_key_encoded}.parquet"
    
    def check_local_file_exists(
        self,
        date_str: str,
        instrument_id: str,
        data_type: str
    ) -> bool:
        """Check if local file exists (tries both encoded and raw formats)."""
        base_path_str = os.getenv("UNIFIED_CLOUD_LOCAL_PATH", "/app/data_downloads")
        base_path = Path(base_path_str).resolve()
        data_dir = base_path / "raw_tick_data" / "by_date" / f"day-{date_str}" / f"data_type-{data_type}"
        
        if not data_dir.exists():
            return False
        
        # Try multiple formats:
        # 1. Encoded version (URL-encoded colons and @)
        instrument_key_encoded = instrument_id.replace(":", "%3A").replace("@", "%40")
        encoded_path = data_dir / f"{instrument_key_encoded}.parquet"
        if encoded_path.exists():
            return True
        
        # 2. Raw version (with colons and @ suffix)
        instrument_key_raw = instrument_id
        raw_path = data_dir / f"{instrument_key_raw}.parquet"
        if raw_path.exists():
            return True
        
        # 3. Without @ suffix (files often don't include @LIN/@SPOT suffix)
        instrument_key_no_suffix = instrument_id.split("@")[0] if "@" in instrument_id else instrument_id
        no_suffix_path = data_dir / f"{instrument_key_no_suffix}.parquet"
        if no_suffix_path.exists():
            return True
        
        # 4. Encoded without @ suffix
        instrument_key_encoded_no_suffix = instrument_key_no_suffix.replace(":", "%3A")
        encoded_no_suffix_path = data_dir / f"{instrument_key_encoded_no_suffix}.parquet"
        if encoded_no_suffix_path.exists():
            return True
        
        # 5. Try listing files to find matches (for partial matches)
        try:
            for file_path in data_dir.glob("*.parquet"):
                file_name = file_path.name
                # Remove .parquet extension
                file_base = file_name.replace(".parquet", "")
                
                # Try matching all variations
                if file_base == instrument_key_encoded:
                    return True
                if file_base == instrument_key_raw:
                    return True
                if file_base == instrument_key_no_suffix:
                    return True
                if file_base == instrument_key_encoded_no_suffix:
                    return True
                
                # Try matching by symbol (e.g., BTC-USDT) - fallback for partial matches
                if "BTC-USDT" in instrument_id and "BTC-USDT" in file_base:
                    return True
                if "BTCUSDT" in instrument_id.replace("-", "") and "BTC" in file_base and "USDT" in file_base:
                    return True
        except Exception:
            pass
        
        return False
    
    async def check_gcs_file_exists(
        self,
        date_str: str,
        instrument_id: str,
        data_type: str
    ) -> bool:
        """Check if GCS file exists using direct GCS client check."""
        import sys
        import os
        # Force output to stdout to ensure it's visible
        print(f"🚀 check_gcs_file_exists CALLED", flush=True)
        print(f"   date={date_str}, instrument={instrument_id}, data_type={data_type}", flush=True)
        print(f"   ucs_loader exists: {self.ucs_loader is not None}", flush=True)
        
        if not self.ucs_loader:
            print(f"⚠️  No UCS loader available", file=sys.stderr, flush=True)
            if self.ucs_error:
                raise ValueError(f"GCS access not available: {self.ucs_error}")
            return False
        
        try:
            # Use unified-cloud-services instead of direct google.cloud.storage
            import sys
            from unified_cloud_services.domain.standardized_service import StandardizedDomainCloudService
            
            bucket_name = self.ucs_loader.bucket_name
            if not bucket_name:
                print(f"⚠️  Bucket name is None in UCS loader", file=sys.stderr, flush=True)
                return False
            
            print(f"🔍 check_gcs_file_exists: bucket={bucket_name}, date={date_str}, instrument={instrument_id}, data_type={data_type}", file=sys.stderr, flush=True)
            
            # Create standardized service for market_data domain
            standardized_service = StandardizedDomainCloudService(
                domain="market_data",
                cloud_target=self.ucs_loader.target
            )
            
            # Try multiple instrument ID formats (with and without @ suffix)
            instrument_ids_to_try = [
                instrument_id,  # Full ID with @LIN
                instrument_id.split("@")[0] if "@" in instrument_id else instrument_id,  # Without @ suffix
            ]
            
            # Map data_type to GCS path format
            data_type_map = {
                "trades": "trades",
                "book_snapshot_5": "book_snapshot_5",
            }
            gcs_data_type = data_type_map.get(data_type, data_type)
            
            # Try each instrument ID format
            for inst_id in instrument_ids_to_try:
                # Build GCS path (raw format, matching working download script)
                gcs_path = f"raw_tick_data/by_date/day-{date_str}/data_type-{gcs_data_type}/{inst_id}.parquet"
                
                # Check if file exists using UCS
                exists = standardized_service.check_gcs_path_exists(gcs_path)
                
                # Debug logging
                print(f"🔍 Checking GCS: {gcs_path}", file=sys.stderr, flush=True)
                print(f"   Exists: {exists}", file=sys.stderr, flush=True)
                
                if exists:
                    print(f"   ✅ Found: {gcs_path}", file=sys.stderr, flush=True)
                    return True
            
            # File not found with any format
            print(f"   ❌ Not found with any format", file=sys.stderr, flush=True)
            return False
            
        except ValueError:
            # Re-raise ValueError (configuration errors)
            raise
        except Exception as e:
            # Log error and re-raise for proper error handling upstream
            error_msg = f"Error checking GCS file existence: {str(e)}"
            print(f"⚠️  {error_msg}")
            import traceback
            traceback.print_exc()
            raise ValueError(f"GCS check failed: {error_msg}")
    
    async def check_data_availability(
        self,
        instrument_id: str,
        start: datetime,
        end: datetime,
        snapshot_mode: str = "both"
    ) -> Dict[str, Any]:
        """
        Check data availability for time window.
        
        Returns:
            {
                "valid": bool,
                "has_trades": bool,
                "has_book": bool,
                "date": str,  # YYYY-MM-DD
                "dataset": str,  # day-YYYY-MM-DD
                "source": str,  # "local" or "gcs"
                "messages": List[str],
                "errors": List[str],
                "warnings": List[str]
            }
        """
        date_obj = self._extract_date_from_window(start, end)
        date_str = date_obj.strftime("%Y-%m-%d")
        dataset = f"day-{date_str}"
        
        result = {
            "valid": False,
            "has_trades": False,
            "has_book": False,
            "date": date_str,
            "dataset": dataset,
            "source": self.data_source,
            "messages": [],
            "errors": [],
            "warnings": []
        }
        
        # Determine actual source (defaults to GCS)
        # Use the requested source, not the fallback
        actual_source = self.data_source if hasattr(self, 'requested_source') else self.data_source
        
        if actual_source == "auto":
            actual_source = "gcs"  # Default to GCS
        elif actual_source == "gcs":
            # Explicitly use GCS - check if available
            if not self.ucs_loader:
                # GCS was requested but not available - add clear error
                result["errors"].append(
                    f"❌ GCS data source requested but GCS access not available.\n"
                    f"   Error: {self.ucs_error or 'Unknown error'}\n"
                    f"   Please check GCS configuration or use 'local' data source."
                )
                result["valid"] = False
                result["source"] = "gcs"  # Show what was requested
                return result  # Return early with error
            actual_source = "gcs"
        
        result["source"] = actual_source
        
        # Convert instrument ID to GCS format if needed (for GCS checks)
        # Local files might use different format, so we'll try both
        gcs_instrument_id = _convert_instrument_id_to_gcs_format(instrument_id)
        
        # ALWAYS check both trades and book data availability (for informational purposes)
        # Then validate based on snapshot_mode requirements
        
        # Check trades data
        try:
            if actual_source == "local":
                # Try both formats for local files
                has_trades = self.check_local_file_exists(date_str, instrument_id, "trades")
                if not has_trades:
                    has_trades = self.check_local_file_exists(date_str, gcs_instrument_id, "trades")
            else:
                # Use GCS format for GCS checks
                import sys
                print(f"🔍 Checking trades: date={date_str}, instrument={gcs_instrument_id}, source={actual_source}", file=sys.stderr, flush=True)
                has_trades = await self.check_gcs_file_exists(date_str, gcs_instrument_id, "trades")
                print(f"🔍 Trades check result: {has_trades}", file=sys.stderr, flush=True)
        except Exception as e:
            # If GCS check fails, add error message
            import sys
            import traceback
            print(f"⚠️  Exception in trades check: {e}", file=sys.stderr, flush=True)
            traceback.print_exc(file=sys.stderr)
            result["errors"].append(f"❌ Error checking trades data: {str(e)}")
            has_trades = False
        
        result["has_trades"] = has_trades
        
        # Check book snapshot data
        try:
            if actual_source == "local":
                # Try both formats for local files
                has_book = self.check_local_file_exists(date_str, instrument_id, "book_snapshot_5")
                if not has_book:
                    has_book = self.check_local_file_exists(date_str, gcs_instrument_id, "book_snapshot_5")
            else:
                # Use GCS format for GCS checks
                has_book = await self.check_gcs_file_exists(date_str, gcs_instrument_id, "book_snapshot_5")
        except Exception as e:
            # If GCS check fails, add error message
            result["errors"].append(f"❌ Error checking book snapshot data: {str(e)}")
            has_book = False
        
        result["has_book"] = has_book
        
        # Validate based on snapshot_mode requirements
        if snapshot_mode in ("trades", "both"):
            # Trades are required for these modes
            if not has_trades:
                # Show the expected GCS format in error message
                if actual_source == "gcs":
                    expected_format = gcs_instrument_id
                else:
                    # For local, show both formats
                    expected_format = f"{instrument_id} (or {gcs_instrument_id})"
                
                result["errors"].append(
                    f"❌ Trades data NOT FOUND for {date_str}\n"
                    f"   Required for backtest. Data source: {actual_source}\n"
                    f"   Expected: {dataset}/data_type-trades/{expected_format}.parquet"
                )
                result["valid"] = False
            else:
                result["messages"].append(f"✅ Trades data found for {date_str}")
        
        if snapshot_mode in ("book", "both"):
            # Book is required for "book" mode, optional for "both" mode
            if not has_book:
                if snapshot_mode == "book":
                    # Book-only mode requires book data
                    if actual_source == "gcs":
                        expected_format = gcs_instrument_id
                    else:
                        expected_format = f"{instrument_id} (or {gcs_instrument_id})"
                    
                    result["errors"].append(
                        f"❌ Book snapshot data NOT FOUND for {date_str}\n"
                        f"   Required for snapshot_mode='book'. Data source: {actual_source}\n"
                        f"   Expected: {dataset}/data_type-book_snapshot_5/{expected_format}.parquet"
                    )
                    result["valid"] = False
                else:
                    # "both" mode - book is optional
                    result["warnings"].append(
                        f"⚠️  Book snapshot data NOT FOUND for {date_str}\n"
                        f"   Will use trades-only mode. Data source: {actual_source}"
                    )
            else:
                result["messages"].append(f"✅ Book snapshot data found for {date_str}")
        
        # Final validation: trades are required
        if result["has_trades"]:
            if snapshot_mode == "book" and not result["has_book"]:
                result["valid"] = False
            else:
                result["valid"] = True
        
        return result

