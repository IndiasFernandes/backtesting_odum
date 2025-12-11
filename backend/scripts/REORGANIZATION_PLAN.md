# Backend Scripts Reorganization Plan

## Analysis Summary

### Files Status

#### ✅ **Core Production Files** (Keep as-is)
- `start.sh` - Container startup script (used by Dockerfile)
- `mount_gcs.sh` - GCS FUSE mounting (used by start.sh)
- `setup_env.sh` - Environment setup
- `setup_ucs.sh` - UCS setup
- `verify_secrets.sh` - Secrets verification

#### ⚠️ **Unused/Redundant Scripts** (Candidates for removal or archiving)

**Debug/One-off Scripts:**
- `check_gcs_paths.py` - One-off debugging script (not imported)
- `download_may25_binance.py` - Specific date download (one-off)
- `download_may26_binance.py` - Specific date download (one-off)
- `download_one_day_verify.py` - One-off verification
- `download_and_verify_structure.py` - Verification script (redundant)

**Listing/Inspection Scripts:**
- `list_gcs_files.py` - Basic listing (redundant with list_gcs_dates_and_files.py)
- `list_gcs_dates_and_files.py` - More comprehensive listing
- `list_available_dates.py` - Date listing (functionality exists in ucs_data_loader.py)

**Test Scripts (should be in tests/):**
- `test_gcs_file_exists.py` - Should be in tests/
- `test_gcs_write.py` - Should be in tests/
- `verify_gcs_structure.py` - Should be in tests/

**Empty/Incomplete Files:**
- `gcs_write_examples.py` - Empty file (duplicate exists in utils/)

**Validation Scripts:**
- `strategy_validator.py` - Standalone validator (could be useful, but not integrated)

#### 📁 **Already Organized** (Keep structure)
- `tests/` - Test scripts (good organization)
- `utils/` - Utility scripts (good organization)

### Core Backend Files Analysis

#### ⚠️ **Potentially Unused Core Files**
- `smart_router.py` - Only mentioned in docs, never imported in codebase
  - Status: Planned for future use (live execution)
  - Recommendation: Keep but add TODO comment

## Proposed Reorganization

### Structure

```
backend/scripts/
├── README.md                          # Main documentation
├── start.sh                           # Production startup
├── mount_gcs.sh                       # Production FUSE mount
├── setup_env.sh                       # Production setup
├── setup_ucs.sh                       # Production setup
├── verify_secrets.sh                  # Production verification
│
├── tests/                             # All test scripts
│   ├── test_docker_infrastructure.sh
│   ├── test_running_services.sh
│   ├── test_cli_alignment.sh
│   ├── test_gcs_backtest.sh
│   ├── test_gcs_file_exists.py        # MOVED HERE
│   ├── test_gcs_write.py              # MOVED HERE
│   └── verify_gcs_structure.py        # MOVED HERE
│
├── utils/                             # Utility scripts
│   ├── compare_exec_algorithms.py
│   ├── upload_backtest_results_to_gcs.py
│   ├── gcs_write_examples.py          # Keep one (remove duplicate)
│   ├── list_available_dates.py        # MOVED HERE (if useful)
│   └── list_gcs_dates_and_files.py   # MOVED HERE (consolidate with list_gcs_files.py)
│
└── archive/                           # Archived one-off scripts
    ├── check_gcs_paths.py             # Debug script
    ├── download_may25_binance.py     # One-off download
    ├── download_may26_binance.py     # One-off download
    ├── download_one_day_verify.py    # One-off verification
    ├── download_and_verify_structure.py  # Redundant verification
    ├── list_gcs_files.py              # Redundant listing
    └── strategy_validator.py          # Standalone validator (not integrated)
```

## Action Items

### Phase 1: Archive Unused Scripts
1. Create `backend/scripts/archive/` directory
2. Move one-off/debug scripts to archive
3. Add README.md in archive explaining why scripts were archived

### Phase 2: Reorganize Test Scripts
1. Move test scripts from root to `tests/` directory
2. Update any references (if any)

### Phase 3: Consolidate Utilities
1. Remove duplicate `gcs_write_examples.py` (keep one in utils/)
2. Consolidate listing scripts (merge functionality)
3. Move useful utilities to `utils/`

### Phase 4: Clean Up Core Files
1. Add TODO comment to `smart_router.py` indicating future use
2. Document why it's not currently used

## Files to Remove (Empty/Duplicate)

- `backend/scripts/gcs_write_examples.py` (empty, duplicate exists in utils/)

## Files to Archive (One-off/Debug)

- `check_gcs_paths.py`
- `download_may25_binance.py`
- `download_may26_binance.py`
- `download_one_day_verify.py`
- `download_and_verify_structure.py`
- `list_gcs_files.py` (if redundant with list_gcs_dates_and_files.py)
- `strategy_validator.py` (if not integrated)

## Files to Move

**To tests/:**
- `test_gcs_file_exists.py`
- `test_gcs_write.py`
- `verify_gcs_structure.py`

**To utils/:**
- `list_available_dates.py` (if useful standalone)
- `list_gcs_dates_and_files.py` (consolidate listing functionality)

## Notes

- Scripts in `archive/` are kept for reference but not actively maintained
- All production scripts remain in root of `scripts/`
- Test scripts are consolidated in `tests/`
- Utility scripts are in `utils/`
- Consider creating a script index/registry for discoverability

