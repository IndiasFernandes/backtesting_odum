#!/usr/bin/env python3
"""
Upload backtest results to GCS using unified-cloud-services.

This script uploads the entire backtest_results folder structure to GCS
according to the specification requirements.

Spec Requirements:
- Bucket: execution-store-cefi-central-element-323112
- Structure:
  - backtest_results/{run_id}/summary.json
  - backtest_results/{run_id}/orders.parquet (if available)
  - backtest_results/{run_id}/fills.parquet (if available)
  - backtest_results/{run_id}/positions.parquet (if available)
  - backtest_results/{run_id}/equity_curve.parquet (if available)
  - config/{run_id}/backtest_config.json
  - logs/{run_id}/execution.log (if available)
"""
import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from unified_cloud_services import UnifiedCloudService, CloudTarget
    from unified_cloud_services.domain.standardized_service import StandardizedDomainCloudService
    UCS_AVAILABLE = True
except ImportError as e:
    print(f"❌ Error importing unified-cloud-services: {e}")
    UCS_AVAILABLE = False

try:
    from google.cloud import storage
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False


class BacktestResultsUploader:
    """Upload backtest results to GCS according to spec."""
    
    def __init__(self, bucket_name: str = None):
        """
        Initialize uploader.
        
        Args:
            bucket_name: GCS bucket name (defaults to EXECUTION_STORE_GCS_BUCKET env var)
        """
        if not UCS_AVAILABLE:
            raise ImportError("unified-cloud-services not available")
        
        # Use execution store bucket (output bucket) per spec
        self.bucket_name = bucket_name or os.getenv(
            "EXECUTION_STORE_GCS_BUCKET",
            "execution-store-cefi-central-element-323112"
        )
        
        self.target = CloudTarget(
            gcs_bucket=self.bucket_name,
            bigquery_dataset="execution"
        )
        
        self.ucs = UnifiedCloudService()
        self.service = StandardizedDomainCloudService(
            domain="execution",
            cloud_target=self.target
        )
        
        print(f"✅ Initialized uploader for bucket: {self.bucket_name}")
    
    def _convert_json_to_dataframe(self, json_data: List[Dict[str, Any]]) -> Optional[pd.DataFrame]:
        """Convert JSON list to DataFrame if not empty."""
        if not json_data:
            return None
        try:
            return pd.DataFrame(json_data)
        except Exception as e:
            print(f"⚠️  Warning: Could not convert to DataFrame: {e}")
            return None
    
    async def upload_file_to_gcs(
        self,
        gcs_path: str,
        local_path: Path,
        content_type: str = None
    ) -> bool:
        """
        Upload a single file to GCS.
        
        Args:
            gcs_path: GCS destination path
            local_path: Local file path
            content_type: Content type (auto-detected if None)
            
        Returns:
            True if successful
        """
        if not local_path.exists():
            print(f"⚠️  File not found: {local_path}")
            return False
        
        try:
            # Determine format from extension
            ext = local_path.suffix.lower()
            if ext == '.json':
                # Read JSON and upload as string (unified-cloud-services requires string for JSON)
                with open(local_path, 'r') as f:
                    json_string = f.read()
                await self.ucs.upload_to_gcs(
                    target=self.target,
                    gcs_path=gcs_path,
                    data=json_string,
                    format='json'
                )
            elif ext == '.parquet':
                # Read Parquet and upload as DataFrame
                df = pd.read_parquet(local_path)
                await self.ucs.upload_to_gcs(
                    target=self.target,
                    gcs_path=gcs_path,
                    data=df,
                    format='parquet'
                )
            elif ext == '.csv':
                # Read CSV and upload as DataFrame
                df = pd.read_csv(local_path)
                await self.ucs.upload_to_gcs(
                    target=self.target,
                    gcs_path=gcs_path,
                    data=df,
                    format='csv'
                )
            else:
                # Use direct GCS client for other files (text files, logs, etc.)
                if not GCS_AVAILABLE:
                    raise ImportError("google.cloud.storage not available for non-standard file types")
                client = storage.Client()
                bucket = client.bucket(self.bucket_name)
                blob = bucket.blob(gcs_path)
                blob.upload_from_filename(str(local_path), content_type=content_type or "application/octet-stream")
            
            print(f"✅ Uploaded: {gcs_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error uploading {local_path} to {gcs_path}: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def upload_run_results(
        self,
        run_id: str,
        local_results_dir: Path,
        config_path: Optional[Path] = None,
        log_path: Optional[Path] = None
    ) -> Dict[str, bool]:
        """
        Upload all results for a single run.
        
        Args:
            run_id: Run identifier
            local_results_dir: Local directory containing results
            config_path: Path to config file (optional)
            log_path: Path to log file (optional)
            
        Returns:
            Dictionary of upload results {file: success}
        """
        results = {}
        
        # Upload summary.json
        summary_path = local_results_dir / "summary.json"
        if summary_path.exists():
            results['summary.json'] = await self.upload_file_to_gcs(
                gcs_path=f"backtest_results/{run_id}/summary.json",
                local_path=summary_path
            )
        
        # Load summary for context
        summary_data = None
        if summary_path.exists():
            try:
                with open(summary_path, 'r') as f:
                    summary_data = json.load(f)
            except Exception:
                pass
        
        # Upload timeline.json (convert to positions.parquet if possible)
        timeline_path = local_results_dir / "timeline.json"
        if timeline_path.exists():
            try:
                with open(timeline_path, 'r') as f:
                    timeline_data = json.load(f)
                
                # Try to extract position data from timeline
                if isinstance(timeline_data, list) and timeline_data:
                    positions_df = self._extract_positions_from_timeline(timeline_data, summary_data)
                    if positions_df is not None and not positions_df.empty:
                        results['positions.parquet'] = await self.upload_dataframe_to_gcs(
                            gcs_path=f"backtest_results/{run_id}/positions.parquet",
                            df=positions_df
                        )
            except Exception as e:
                print(f"⚠️  Could not process timeline.json: {e}")
        
        # Upload orders.json (convert to orders.parquet)
        orders_path = local_results_dir / "orders.json"
        if orders_path.exists():
            try:
                with open(orders_path, 'r') as f:
                    orders_data = json.load(f)
                
                orders_df = self._convert_json_to_dataframe(orders_data)
                if orders_df is not None and not orders_df.empty:
                    results['orders.parquet'] = await self.upload_dataframe_to_gcs(
                        gcs_path=f"backtest_results/{run_id}/orders.parquet",
                        df=orders_df
                    )
            except Exception as e:
                print(f"⚠️  Could not process orders.json: {e}")
        
        # Try to extract fills from timeline/orders
        fills_df = self._extract_fills_from_results(local_results_dir)
        if fills_df is not None and not fills_df.empty:
            results['fills.parquet'] = await self.upload_dataframe_to_gcs(
                gcs_path=f"backtest_results/{run_id}/fills.parquet",
                df=fills_df
            )
        
        # Try to extract equity curve from timeline
        equity_df = self._extract_equity_curve_from_results(local_results_dir)
        if equity_df is not None and not equity_df.empty:
            results['equity_curve.parquet'] = await self.upload_dataframe_to_gcs(
                gcs_path=f"backtest_results/{run_id}/equity_curve.parquet",
                df=equity_df
            )
        
        # Upload config
        if config_path and config_path.exists():
            results['config.json'] = await self.upload_file_to_gcs(
                gcs_path=f"config/{run_id}/backtest_config.json",
                local_path=config_path
            )
        
        # Upload logs
        if log_path and log_path.exists():
            results['execution.log'] = await self.upload_file_to_gcs(
                gcs_path=f"logs/{run_id}/execution.log",
                local_path=log_path,
                content_type="text/plain"
            )
        
        return results
    
    async def upload_dataframe_to_gcs(
        self,
        gcs_path: str,
        df: pd.DataFrame
    ) -> bool:
        """Upload DataFrame to GCS as Parquet."""
        try:
            await self.ucs.upload_to_gcs(
                target=self.target,
                gcs_path=gcs_path,
                data=df,
                format='parquet'
            )
            print(f"✅ Uploaded DataFrame ({len(df)} rows) to: {gcs_path}")
            return True
        except Exception as e:
            print(f"❌ Error uploading DataFrame to {gcs_path}: {type(e).__name__}: {e}")
            return False
    
    def _extract_positions_from_timeline(self, timeline: List[Dict[str, Any]], summary: Dict[str, Any] = None) -> Optional[pd.DataFrame]:
        """Extract position data from timeline events or summary."""
        positions = []
        
        # Try to extract from timeline
        for event in timeline:
            event_type = event.get('event', '').lower()
            if event_type == 'position' or 'position' in str(event.get('data', {})).lower():
                pos_data = event.get('data', {}).get('position', event.get('data', {}))
                if pos_data:
                    ts_str = event.get('ts', '')
                    ts_event = 0
                    if ts_str:
                        try:
                            from datetime import datetime
                            dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                            ts_event = int(dt.timestamp() * 1e9)
                        except:
                            pass
                    
                    positions.append({
                        'ts_event': ts_event,
                        'instrument_key': pos_data.get('instrument_id', pos_data.get('instrument', '')),
                        'quantity': pos_data.get('quantity', pos_data.get('size', 0)),
                        'avg_entry_price': pos_data.get('avg_entry_price', pos_data.get('entry_price', 0)),
                        'current_price': pos_data.get('current_price', pos_data.get('price', 0)),
                        'unrealized_pnl': pos_data.get('unrealized_pnl', 0),
                        'realized_pnl': pos_data.get('realized_pnl', 0),
                    })
        
        # If no timeline positions, create from summary
        if not positions and summary:
            pos_data = summary.get('summary', {}).get('position', {})
            if pos_data:
                try:
                    from datetime import datetime
                    end_str = summary.get('end', '')
                    dt = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                    ts_event = int(dt.timestamp() * 1e9)
                except:
                    ts_event = 0
                
                positions.append({
                    'ts_event': ts_event,
                    'instrument_key': summary.get('instrument', ''),
                    'quantity': pos_data.get('quantity', 0),
                    'avg_entry_price': pos_data.get('entry_price', 0),
                    'current_price': pos_data.get('current_price', 0),
                    'unrealized_pnl': pos_data.get('unrealized_pnl', 0),
                    'realized_pnl': pos_data.get('realized_pnl', 0),
                })
        
        if positions:
            return pd.DataFrame(positions)
        return None
    
    def _extract_fills_from_results(self, results_dir: Path) -> Optional[pd.DataFrame]:
        """Extract fill data from timeline or orders."""
        fills = []
        
        # Try timeline.json
        timeline_path = results_dir / "timeline.json"
        if timeline_path.exists():
            try:
                with open(timeline_path, 'r') as f:
                    timeline = json.load(f)
                
                for event in timeline:
                    if event.get('type') == 'fill' or 'fill' in event.get('data', {}):
                        fill_data = event.get('data', {}).get('fill', event.get('data', {}))
                        if fill_data:
                            fills.append({
                                'fill_id': fill_data.get('fill_id', event.get('id', '')),
                                'order_id': fill_data.get('order_id', ''),
                                'instrument_key': fill_data.get('instrument_id', fill_data.get('instrument', '')),
                                'side': fill_data.get('side', ''),
                                'quantity': fill_data.get('quantity', fill_data.get('size', 0)),
                                'price': fill_data.get('price', 0),
                                'fee': fill_data.get('fee', 0),
                                'fee_currency': fill_data.get('fee_currency', 'USDT'),
                                'ts_event': event.get('timestamp', event.get('ts_event', 0)),
                                'venue': fill_data.get('venue', ''),
                            })
            except Exception:
                pass
        
        # Try orders.json for filled orders
        orders_path = results_dir / "orders.json"
        if orders_path.exists():
            try:
                with open(orders_path, 'r') as f:
                    orders = json.load(f)
                
                for order in orders:
                    if order.get('status') == 'FILLED' and order.get('filled_quantity', 0) > 0:
                        fills.append({
                            'fill_id': f"{order.get('order_id', '')}_fill",
                            'order_id': order.get('order_id', ''),
                            'instrument_key': order.get('instrument_id', order.get('instrument', '')),
                            'side': order.get('side', ''),
                            'quantity': order.get('filled_quantity', order.get('quantity', 0)),
                            'price': order.get('fill_price', order.get('price', 0)),
                            'fee': order.get('fee', 0),
                            'fee_currency': order.get('fee_currency', 'USDT'),
                            'ts_event': order.get('filled_at', order.get('timestamp', 0)),
                            'venue': order.get('venue', ''),
                        })
            except Exception:
                pass
        
        if fills:
            return pd.DataFrame(fills)
        return None
    
    def _extract_equity_curve_from_results(self, results_dir: Path) -> Optional[pd.DataFrame]:
        """Extract equity curve from timeline or summary."""
        equity_points = []
        
        # Try timeline.json
        timeline_path = results_dir / "timeline.json"
        if timeline_path.exists():
            try:
                with open(timeline_path, 'r') as f:
                    timeline = json.load(f)
                
                portfolio_value = None
                for event in timeline:
                    if 'portfolio_value' in event.get('data', {}) or 'equity' in event.get('data', {}):
                        data = event.get('data', {})
                        equity_points.append({
                            'ts_event': event.get('timestamp', event.get('ts_event', 0)),
                            'portfolio_value': data.get('portfolio_value', data.get('equity', 0)),
                            'cash_balance': data.get('cash_balance', data.get('cash', 0)),
                            'margin_used': data.get('margin_used', 0),
                            'unrealized_pnl': data.get('unrealized_pnl', 0),
                            'drawdown_pct': data.get('drawdown_pct', 0),
                        })
            except Exception:
                pass
        
        # If no timeline data, create from summary
        if not equity_points:
            summary_path = results_dir / "summary.json"
            if summary_path.exists():
                try:
                    with open(summary_path, 'r') as f:
                        summary = json.load(f)
                    
                    # Create single point from summary
                    equity_points.append({
                        'ts_event': summary.get('execution_time', summary.get('end', '')),
                        'portfolio_value': summary.get('summary', {}).get('final_equity', summary.get('summary', {}).get('pnl', {}).get('net_pnl', 0)),
                        'cash_balance': summary.get('summary', {}).get('cash_balance', 0),
                        'margin_used': 0,
                        'unrealized_pnl': summary.get('summary', {}).get('unrealized_pnl', 0),
                        'drawdown_pct': summary.get('summary', {}).get('max_drawdown_pct', 0),
                    })
                except Exception:
                    pass
        
        if equity_points:
            return pd.DataFrame(equity_points)
        return None
    
    async def upload_all_results(
        self,
        local_results_base: Path,
        config_base: Optional[Path] = None
    ) -> Dict[str, Dict[str, bool]]:
        """
        Upload all backtest results from local directory.
        
        Args:
            local_results_base: Base directory containing backtest_results/
            config_base: Base directory containing config files (optional)
            
        Returns:
            Dictionary mapping run_id to upload results
        """
        all_results = {}
        
        # Process fast mode results
        fast_dir = local_results_base / "fast"
        if fast_dir.exists():
            for json_file in fast_dir.glob("*.json"):
                run_id = json_file.stem
                print(f"\n📤 Processing fast mode result: {run_id}")
                
                # Create temp directory structure
                temp_dir = Path(f"/tmp/backtest_upload_{run_id}")
                temp_dir.mkdir(exist_ok=True)
                
                # Copy summary.json
                import shutil
                shutil.copy(json_file, temp_dir / "summary.json")
                
                # Find config if available
                config_path = None
                if config_base:
                    # Try to find config by run_id or instrument
                    for config_file in config_base.glob("**/*.json"):
                        if run_id in config_file.name or any(inst in config_file.name for inst in ['BTC', 'ETH']):
                            config_path = config_file
                            break
                
                results = await self.upload_run_results(
                    run_id=run_id,
                    local_results_dir=temp_dir,
                    config_path=config_path
                )
                all_results[run_id] = results
                
                # Cleanup
                shutil.rmtree(temp_dir, ignore_errors=True)
        
        # Process report mode results
        report_dir = local_results_base / "report"
        if report_dir.exists():
            for run_dir in report_dir.iterdir():
                if run_dir.is_dir():
                    run_id = run_dir.name
                    print(f"\n📤 Processing report mode result: {run_id}")
                    
                    # Find config if available
                    config_path = None
                    if config_base:
                        for config_file in config_base.glob("**/*.json"):
                            if run_id in config_file.name or any(inst in config_file.name for inst in ['BTC', 'ETH']):
                                config_path = config_file
                                break
                    
                    results = await self.upload_run_results(
                        run_id=run_id,
                        local_results_dir=run_dir,
                        config_path=config_path
                    )
                    all_results[run_id] = results
        
        return all_results


async def main():
    """Main function to upload backtest results."""
    print("="*60)
    print("Upload Backtest Results to GCS")
    print("="*60)
    
    if not UCS_AVAILABLE:
        print("\n❌ unified-cloud-services not available")
        return
    
    # Setup credentials
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path or not Path(creds_path).exists():
        print("\n⚠️  Warning: GOOGLE_APPLICATION_CREDENTIALS not set or file not found")
        print("   Uploads may fail without proper credentials")
    
    # Get bucket name
    bucket_name = os.getenv(
        "EXECUTION_STORE_GCS_BUCKET",
        "execution-store-cefi-central-element-323112"
    )
    
    print(f"\n📦 Output Bucket: {bucket_name}")
    print(f"🔑 Credentials: {creds_path or 'Not set'}")
    
    # Initialize uploader
    try:
        uploader = BacktestResultsUploader(bucket_name=bucket_name)
    except Exception as e:
        print(f"\n❌ Failed to initialize uploader: {e}")
        return
    
    # Find local results directory
    local_results_base = Path("backend/backtest_results")
    if not local_results_base.exists():
        # Try Docker path
        local_results_base = Path("/app/backend/backtest_results")
    
    if not local_results_base.exists():
        print(f"\n❌ Results directory not found: {local_results_base}")
        return
    
    print(f"\n📁 Local Results Directory: {local_results_base}")
    
    # Find config directory
    config_base = Path("external/data_downloads/configs")
    if not config_base.exists():
        config_base = Path("/app/external/data_downloads/configs")
    
    if config_base.exists():
        print(f"📁 Config Directory: {config_base}")
    else:
        print(f"⚠️  Config directory not found: {config_base}")
        config_base = None
    
    # Upload all results
    print("\n" + "="*60)
    print("Starting upload...")
    print("="*60)
    
    try:
        all_results = await uploader.upload_all_results(
            local_results_base=local_results_base,
            config_base=config_base
        )
        
        # Summary
        print("\n" + "="*60)
        print("Upload Summary")
        print("="*60)
        
        total_runs = len(all_results)
        successful_runs = sum(1 for results in all_results.values() if any(results.values()))
        
        print(f"\n📊 Total runs processed: {total_runs}")
        print(f"✅ Successful uploads: {successful_runs}")
        
        for run_id, results in all_results.items():
            print(f"\n  Run: {run_id}")
            for file, success in results.items():
                status = "✅" if success else "❌"
                print(f"    {status} {file}")
        
        if successful_runs > 0:
            print(f"\n🎉 Successfully uploaded {successful_runs} run(s) to GCS!")
            print(f"   Bucket: gs://{bucket_name}/backtest_results/")
        else:
            print("\n⚠️  No successful uploads. Check errors above.")
            
    except Exception as e:
        print(f"\n❌ Error during upload: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

