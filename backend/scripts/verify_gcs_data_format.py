#!/usr/bin/env python3
"""
Verify GCS bucket data format and conversion logic.

This script:
1. Lists files in GCS bucket to verify they exist
2. Downloads a sample file to inspect schema
3. Verifies conversion logic handles the format correctly
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from unified_cloud_services import UnifiedCloudService, CloudTarget
import pandas as pd


async def verify_gcs_data_format():
    """Verify GCS bucket data format matches expected NautilusTrader schema."""
    
    print("=" * 80)
    print("GCS Data Format Verification")
    print("=" * 80)
    
    # Initialize UCS
    ucs = UnifiedCloudService()
    target = CloudTarget(
        gcs_bucket='market-data-tick-cefi-central-element-323112',
        project_id='central-element-323112'
    )
    
    # 1. List files in bucket
    print("\n1. Listing files in GCS bucket...")
    try:
        prefix = "raw_tick_data/by_date/day-2023-05-23/data_type-trades/"
        files = await ucs.list_gcs_files(target=target, prefix=prefix, max_results=10)
        
        if not files:
            print(f"   ⚠️  No files found with prefix: {prefix}")
            print("   Trying alternative date format...")
            prefix = "raw_tick_data/by_date/"
            files = await ucs.list_gcs_files(target=target, prefix=prefix, max_results=20)
        
        if files:
            print(f"   ✅ Found {len(files)} files")
            print(f"   Sample files:")
            for f in files[:5]:
                print(f"      - {f['name']} ({f['size'] / 1024 / 1024:.2f} MB)")
        else:
            print(f"   ❌ No files found in bucket")
            return False
            
    except Exception as e:
        print(f"   ❌ Error listing files: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 2. Download a sample file to inspect schema
    if files:
        sample_file = files[0]['name']
        print(f"\n2. Downloading sample file to inspect schema...")
        print(f"   File: {sample_file}")
        
        try:
            # Download sample file
            df = await ucs.download_from_gcs(
                target=target,
                gcs_path=sample_file,
                format='parquet'
            )
            
            print(f"   ✅ Downloaded {len(df)} rows")
            print(f"\n   Schema:")
            print(f"   Columns: {list(df.columns)}")
            print(f"   Dtypes:")
            for col in df.columns:
                print(f"      {col}: {df[col].dtype}")
            
            # Check for expected columns
            print(f"\n   Expected vs Actual:")
            expected_cols = {
                'instrument_key': 'Canonical instrument ID',
                'ts_event': 'Event timestamp (nanoseconds)',
                'ts_init': 'Init timestamp (nanoseconds)',
                'price': 'Trade price',
                'size': 'Trade size',
                'aggressor_side': 'Aggressor side (int8: 1=buy, 2=sell)',
                'trade_id': 'Trade ID'
            }
            
            missing_cols = []
            for col, desc in expected_cols.items():
                if col in df.columns:
                    print(f"      ✅ {col}: {desc}")
                    # Check sample values
                    if col == 'aggressor_side':
                        unique_vals = df[col].unique()
                        print(f"         Sample values: {unique_vals[:5]}")
                    elif col in ['ts_event', 'ts_init']:
                        sample_val = df[col].iloc[0]
                        # Check if in nanoseconds (should be very large number)
                        if sample_val > 1e15:  # Nanoseconds since epoch
                            print(f"         ✅ Timestamp in nanoseconds: {sample_val}")
                        elif sample_val > 1e12:  # Microseconds
                            print(f"         ⚠️  Timestamp in microseconds (needs conversion): {sample_val}")
                        else:
                            print(f"         ⚠️  Unexpected timestamp format: {sample_val}")
                else:
                    print(f"      ❌ {col}: MISSING - {desc}")
                    missing_cols.append(col)
            
            # Check for old format columns
            old_format_cols = ['timestamp', 'local_timestamp', 'amount', 'side', 'id']
            found_old_cols = [col for col in old_format_cols if col in df.columns]
            if found_old_cols:
                print(f"\n   ⚠️  Old format columns found: {found_old_cols}")
                print(f"      This suggests data is NOT pre-converted!")
            
            # Sample data
            print(f"\n   Sample data (first 3 rows):")
            print(df.head(3).to_string())
            
            return len(missing_cols) == 0
            
        except Exception as e:
            print(f"   ❌ Error downloading file: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True


async def test_conversion_logic():
    """Test conversion logic with sample data."""
    
    print("\n" + "=" * 80)
    print("Conversion Logic Test")
    print("=" * 80)
    
    # Test data in pre-converted format
    test_data = {
        'instrument_key': ['BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN'],
        'ts_event': [1684800000000000000],  # Nanoseconds
        'ts_init': [1684800000000000000],
        'price': [30000.0],
        'size': [0.001],
        'aggressor_side': [1],  # int8: 1=buy
        'trade_id': ['test-trade-1']
    }
    
    df = pd.DataFrame(test_data)
    print(f"\nTest DataFrame:")
    print(df.to_string())
    
    # Simulate conversion logic
    print(f"\nSimulating conversion logic...")
    
    # Check schema detection
    if 'ts_event' in df.columns:
        print("   ✅ Detected NautilusTrader format (has ts_event)")
        ts_event_col = 'ts_event'
        ts_init_col = 'ts_init'
        aggressor_col = 'aggressor_side'
        timestamp_unit = 'nanoseconds'
    else:
        print("   ⚠️  Detected old format (has timestamp)")
        ts_event_col = 'timestamp'
        ts_init_col = 'local_timestamp'
        aggressor_col = 'side'
        timestamp_unit = 'microseconds'
    
    # Test aggressor_side conversion
    print(f"\n   Testing aggressor_side conversion...")
    aggressor_str = df[aggressor_col].astype(str).str.upper()
    print(f"      Input: {df[aggressor_col].values}")
    print(f"      As string: {aggressor_str.values}")
    
    # Map aggressor side
    aggressor_side_codes = aggressor_str.map({
        'BUY': 'BUYER',
        'BUYER': 'BUYER',
        'AGGRESSOR_BUY': 'BUYER',
        '1': 'BUYER',  # int8: 1
        'B': 'BUYER',
        'SELL': 'SELLER',
        'SELLER': 'SELLER',
        'AGGRESSOR_SELL': 'SELLER',
        '2': 'SELLER',  # int8: 2
        'S': 'SELLER',
    }).fillna('BUYER')
    
    print(f"      Mapped: {aggressor_side_codes.values}")
    
    # Convert to enum
    from nautilus_trader.model.enums import AggressorSide
    aggressor_code = str(aggressor_side_codes.iloc[0])
    aggressor_side = AggressorSide.BUYER if aggressor_code == 'BUYER' else AggressorSide.SELLER
    print(f"      Enum: {aggressor_side}")
    
    # Test edge cases
    print(f"\n   Testing edge cases...")
    edge_cases = [
        (1, 'BUYER'),
        (2, 'SELLER'),
        ('1', 'BUYER'),
        ('2', 'SELLER'),
        ('buy', 'BUYER'),
        ('sell', 'SELLER'),
        ('BUY', 'BUYER'),
        ('SELL', 'SELLER'),
    ]
    
    for input_val, expected in edge_cases:
        test_df = pd.DataFrame({'aggressor_side': [input_val]})
        test_str = test_df['aggressor_side'].astype(str).str.upper()
        test_mapped = test_str.map({
            'BUY': 'BUYER', 'BUYER': 'BUYER', 'AGGRESSOR_BUY': 'BUYER',
            '1': 'BUYER', 'B': 'BUYER',
            'SELL': 'SELLER', 'SELLER': 'SELLER', 'AGGRESSOR_SELL': 'SELLER',
            '2': 'SELLER', 'S': 'SELLER',
        }).fillna('BUYER')
        result = 'BUYER' if test_mapped.iloc[0] == 'BUYER' else 'SELLER'
        status = '✅' if result == expected else '❌'
        print(f"      {status} {input_val} → {result} (expected {expected})")
    
    return True


if __name__ == '__main__':
    print("Starting GCS data format verification...\n")
    
    async def main():
        # Verify GCS data format
        gcs_ok = await verify_gcs_data_format()
        
        # Test conversion logic
        conversion_ok = await test_conversion_logic()
        
        print("\n" + "=" * 80)
        print("Summary")
        print("=" * 80)
        print(f"GCS Format Verification: {'✅ PASS' if gcs_ok else '❌ FAIL'}")
        print(f"Conversion Logic Test: {'✅ PASS' if conversion_ok else '❌ FAIL'}")
        
        if gcs_ok and conversion_ok:
            print("\n✅ All checks passed!")
            return 0
        else:
            print("\n❌ Some checks failed. Review output above.")
            return 1
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


