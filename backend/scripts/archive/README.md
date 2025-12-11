# Archived Scripts

This directory contains scripts that were archived as part of the reorganization.

## Why Archived?

These scripts are one-off debugging, testing, or verification scripts that:
- Are not imported or used by the main codebase
- Were created for specific debugging sessions
- Have functionality that may be useful for reference but not actively maintained

## Scripts

- `check_gcs_paths.py` - One-off debugging script for checking GCS path structure
- `download_may25_binance.py` - Specific date download script (May 25, 2023)
- `download_may26_binance.py` - Specific date download script (May 26, 2023)
- `download_one_day_verify.py` - One-off verification script
- `download_and_verify_structure.py` - Verification script (redundant with other tools)
- `list_gcs_files.py` - Basic listing script (redundant with list_gcs_dates_and_files.py)
- `strategy_validator.py` - Standalone validator (not integrated into main system)

## Usage

These scripts can still be run directly if needed for debugging or reference:

```bash
python backend/scripts/archive/check_gcs_paths.py
```

However, they are not actively maintained and may require updates to work with current codebase.

## Last Updated

Archived: December 2025
