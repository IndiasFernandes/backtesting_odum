# GCS Upload Alignment Analysis

## Specification Requirements (from Final Spec)

### Output Bucket
- **Required**: `gs://execution-store-cefi-central-element-323112/`
- **Alternative mentioned**: `gs://results-central-element-3-backtest-cefi/`

### Required File Structure
```
gs://execution-store-cefi-central-element-323112/
├── backtest_results/
│   └── {run_id}/
│       ├── summary.json           ✅ Required
│       ├── orders.parquet         ❌ Missing
│       ├── fills.parquet          ❌ Missing
│       ├── positions.parquet      ❌ Missing
│       └── equity_curve.parquet   ❌ Missing
├── config/
│   └── {run_id}/
│       └── backtest_config.json   ❌ Missing
└── logs/
    └── {run_id}/
        └── execution.log          ❌ Missing
```

### Upload Method (from spec)
```python
async def save_backtest_results(run_id: str, summary: dict, fills_df, equity_df):
    ucs = UnifiedCloudService()
    target = CloudTarget(
        gcs_bucket='execution-store-cefi-central-element-323112',
        bigquery_dataset='execution'
    )
    
    # Upload summary JSON
    await ucs.upload_to_gcs(
        target=target,
        gcs_path=f'backtest_results/{run_id}/summary.json',
        data=summary,
        format='json'
    )
    
    # Upload fills Parquet
    await ucs.upload_to_gcs(
        target=target,
        gcs_path=f'backtest_results/{run_id}/fills.parquet',
        data=fills_df,
        format='parquet'
    )
    
    # Upload equity curve Parquet
    await ucs.upload_to_gcs(
        target=target,
        gcs_path=f'backtest_results/{run_id}/equity_curve.parquet',
        data=equity_df,
        format='parquet'
    )
```

## Current Implementation Status

### ❌ Issues Found

1. **No GCS Upload**: Results are only saved locally to `backend/backtest_results/`
   - No automatic upload to GCS after backtest completes
   - No integration with unified-cloud-services for result uploads

2. **Wrong Bucket in Examples**: 
   - Examples use `market-data-tick-cefi-central-element-323112` (input bucket)
   - Should use `execution-store-cefi-central-element-323112` (output bucket)

3. **Missing Files**:
   - ❌ `orders.parquet` - Not generated or uploaded
   - ❌ `fills.parquet` - Not generated or uploaded
   - ❌ `positions.parquet` - Not generated or uploaded
   - ❌ `equity_curve.parquet` - Not generated or uploaded
   - ❌ `backtest_config.json` - Config not uploaded
   - ❌ `execution.log` - Logs not uploaded

4. **File Structure Mismatch**:
   - Current: `backend/backtest_results/fast/{run_id}.json` or `backend/backtest_results/report/{run_id}/summary.json`
   - Required: `gs://execution-store-cefi-central-element-323112/backtest_results/{run_id}/summary.json`

5. **Upload Method**:
   - Spec uses async `await ucs.upload_to_gcs()`
   - Current examples use synchronous `service.upload_to_gcs()` (works but not aligned)

6. **Missing Data Extraction**:
   - Need to extract orders, fills, positions, equity curve from NautilusTrader results
   - Currently only saving summary JSON

## What Needs to Be Fixed

### 1. Add GCS Upload Integration

Create `backend/gcs_result_uploader.py`:

```python
import os
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd

try:
    from unified_cloud_services import UnifiedCloudService, CloudTarget
    from unified_cloud_services.domain.standardized_service import StandardizedDomainCloudService
    UCS_AVAILABLE = True
except ImportError:
    UCS_AVAILABLE = False

class GCSResultUploader:
    """Upload backtest results to GCS according to spec."""
    
    def __init__(self, bucket_name: str = None):
        self.bucket_name = bucket_name or os.getenv(
            "EXECUTION_STORE_GCS_BUCKET", 
            "execution-store-cefi-central-element-323112"
        )
        
        if not UCS_AVAILABLE:
            raise ImportError("unified-cloud-services not available")
        
        self.target = CloudTarget(
            gcs_bucket=self.bucket_name,
            bigquery_dataset="execution"
        )
        
        self.service = StandardizedDomainCloudService(
            domain="execution",  # or "market_data"
            cloud_target=self.target
        )
    
    async def upload_backtest_results(
        self,
        run_id: str,
        summary: Dict[str, Any],
        orders_df: Optional[pd.DataFrame] = None,
        fills_df: Optional[pd.DataFrame] = None,
        positions_df: Optional[pd.DataFrame] = None,
        equity_df: Optional[pd.DataFrame] = None,
        config: Optional[Dict[str, Any]] = None,
        log_content: Optional[str] = None
    ):
        """
        Upload all backtest results to GCS according to spec.
        
        Args:
            run_id: Unique run identifier
            summary: Summary JSON dict
            orders_df: Orders DataFrame (optional)
            fills_df: Fills DataFrame (optional)
            positions_df: Positions DataFrame (optional)
            equity_df: Equity curve DataFrame (optional)
            config: Backtest config dict (optional)
            log_content: Execution log content (optional)
        """
        ucs = UnifiedCloudService()
        
        # Upload summary.json
        summary_json = json.dumps(summary, indent=2, default=str)
        await ucs.upload_to_gcs(
            target=self.target,
            gcs_path=f'backtest_results/{run_id}/summary.json',
            data=summary_json,
            format='json'
        )
        
        # Upload orders.parquet
        if orders_df is not None and not orders_df.empty:
            await ucs.upload_to_gcs(
                target=self.target,
                gcs_path=f'backtest_results/{run_id}/orders.parquet',
                data=orders_df,
                format='parquet'
            )
        
        # Upload fills.parquet
        if fills_df is not None and not fills_df.empty:
            await ucs.upload_to_gcs(
                target=self.target,
                gcs_path=f'backtest_results/{run_id}/fills.parquet',
                data=fills_df,
                format='parquet'
            )
        
        # Upload positions.parquet
        if positions_df is not None and not positions_df.empty:
            await ucs.upload_to_gcs(
                target=self.target,
                gcs_path=f'backtest_results/{run_id}/positions.parquet',
                data=positions_df,
                format='parquet'
            )
        
        # Upload equity_curve.parquet
        if equity_df is not None and not equity_df.empty:
            await ucs.upload_to_gcs(
                target=self.target,
                gcs_path=f'backtest_results/{run_id}/equity_curve.parquet',
                data=equity_df,
                format='parquet'
            )
        
        # Upload config
        if config:
            config_json = json.dumps(config, indent=2, default=str)
            await ucs.upload_to_gcs(
                target=self.target,
                gcs_path=f'config/{run_id}/backtest_config.json',
                data=config_json,
                format='json'
            )
        
        # Upload logs
        if log_content:
            await ucs.upload_to_gcs(
                target=self.target,
                gcs_path=f'logs/{run_id}/execution.log',
                data=log_content,
                format='text'  # or 'json' if structured
            )
    
    def upload_backtest_results_sync(
        self,
        run_id: str,
        summary: Dict[str, Any],
        orders_df: Optional[pd.DataFrame] = None,
        fills_df: Optional[pd.DataFrame] = None,
        positions_df: Optional[pd.DataFrame] = None,
        equity_df: Optional[pd.DataFrame] = None,
        config: Optional[Dict[str, Any]] = None,
        log_content: Optional[str] = None
    ):
        """Synchronous wrapper for upload_backtest_results."""
        return asyncio.run(self.upload_backtest_results(
            run_id=run_id,
            summary=summary,
            orders_df=orders_df,
            fills_df=fills_df,
            positions_df=positions_df,
            equity_df=equity_df,
            config=config,
            log_content=log_content
        ))
```

### 2. Extract Required Data from NautilusTrader

Need to extract:
- Orders DataFrame from `BacktestEngine` results
- Fills DataFrame from execution results
- Positions timeline DataFrame
- Equity curve DataFrame

### 3. Update Environment Variables

Add to `.env` and `docker-compose.yml`:

```bash
# Output bucket for backtest results
EXECUTION_STORE_GCS_BUCKET=execution-store-cefi-central-element-323112
```

### 4. Integrate Upload into Backtest Engine

Add upload step after backtest completes in `backend/backtest_engine.py` or `backend/api/server.py`.

## Alignment Checklist

- [ ] Create `GCSResultUploader` class
- [ ] Extract orders DataFrame from NautilusTrader results
- [ ] Extract fills DataFrame from NautilusTrader results
- [ ] Extract positions DataFrame from NautilusTrader results
- [ ] Extract equity curve DataFrame from NautilusTrader results
- [ ] Upload summary.json to correct bucket
- [ ] Upload orders.parquet
- [ ] Upload fills.parquet
- [ ] Upload positions.parquet
- [ ] Upload equity_curve.parquet
- [ ] Upload config to `config/{run_id}/backtest_config.json`
- [ ] Upload logs to `logs/{run_id}/execution.log`
- [ ] Use correct bucket: `execution-store-cefi-central-element-323112`
- [ ] Use async upload methods (or sync wrapper)
- [ ] Test end-to-end upload

## Summary

**Current Status**: ❌ **NOT ALIGNED**

- Results are saved locally only
- No GCS upload happening
- Missing required files (orders, fills, positions, equity_curve)
- Using wrong bucket in examples
- Not following spec file structure

**Action Required**: Implement complete GCS upload integration following spec structure.

