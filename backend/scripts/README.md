# Backend Scripts

## Structure

```
backend/scripts/
├── start.sh                    # Container startup script (handles FUSE mounting)
├── mount_gcs.sh                # GCS FUSE mounting script
├── setup_env.sh                # Environment setup script
├── setup_ucs.sh                # UCS setup script
├── verify_secrets.sh           # Secrets verification script
├── README.md                   # This file
│
├── tests/                      # Test scripts
│   ├── test_docker_infrastructure.sh
│   ├── test_running_services.sh
│   ├── test_cli_alignment.sh
│   ├── test_gcs_backtest.sh
│   ├── test_gcs_file_exists.py    # GCS file existence tests
│   ├── test_gcs_write.py          # GCS write tests
│   └── verify_gcs_structure.py    # GCS structure verification
│
├── utils/                      # Utility scripts
│   ├── compare_exec_algorithms.py
│   ├── upload_backtest_results_to_gcs.py
│   ├── gcs_write_examples.py
│   ├── list_available_dates.py    # List available dates for instruments
│   └── list_gcs_dates_and_files.py  # List GCS structure
│
└── archive/                    # Archived one-off/debug scripts
    ├── README.md               # Archive documentation
    ├── check_gcs_paths.py      # One-off debugging script
    ├── download_may25_binance.py
    ├── download_may26_binance.py
    ├── download_one_day_verify.py
    ├── download_and_verify_structure.py
    ├── list_gcs_files.py       # Redundant listing script
    └── strategy_validator.py   # Standalone validator
```

## Script Categories

### Startup Scripts
- `start.sh` - Main container startup (called by Dockerfile)
- `mount_gcs.sh` - GCS FUSE mounting (called by start.sh)

### Setup Scripts
- `setup_env.sh` - Environment variable setup
- `setup_ucs.sh` - Unified Cloud Services setup
- `setup_local_dev.sh` - Local development environment setup (installs packages)
- `verify_secrets.sh` - GCS credentials verification

### Test Scripts (`tests/`)
- `test_docker_infrastructure.sh` - Docker infrastructure tests
- `test_deployments.sh` - Tests all 3 deployment modes (backtest, live, both)
- `test_running_services.sh` - Service health tests
- `test_cli_alignment.sh` - CLI alignment tests
- `test_gcs_backtest.sh` - GCS backtest tests
- `test_gcs_file_exists.py` - Test GCS file existence checks
- `test_gcs_write.py` - Test GCS write operations
- `verify_gcs_structure.py` - Verify GCS bucket structure

### Utility Scripts (`utils/`)
- `compare_exec_algorithms.py` - Compare execution algorithm performance
- `upload_backtest_results_to_gcs.py` - Upload results to GCS
- `gcs_write_examples.py` - GCS write examples
- `list_available_dates.py` - List available dates for instruments
- `list_gcs_dates_and_files.py` - List GCS bucket structure

### Archived Scripts (`archive/`)
- One-off debugging, testing, and verification scripts
- Not actively maintained but kept for reference
- See `archive/README.md` for details

## Usage

### Running Tests
```bash
# Run all infrastructure tests
./backend/scripts/tests/test_docker_infrastructure.sh

# Test deployment modes (backtest, live, both)
./backend/scripts/tests/test_deployments.sh

# Run service health tests
./backend/scripts/tests/test_running_services.sh
```

### Running Setup Scripts
```bash
# Setup local development environment
./backend/scripts/setup_local_dev.sh
```

### Running Utilities
```bash
# Compare execution algorithms
python backend/scripts/utils/compare_exec_algorithms.py

# Upload backtest results to GCS
python backend/scripts/utils/upload_backtest_results_to_gcs.py
```

## Reorganization

This directory was reorganized in December 2025 to better organize scripts:
- Production scripts remain in root
- Test scripts consolidated in `tests/`
- Utility scripts in `utils/`
- One-off/debug scripts archived in `archive/`

See `REORGANIZATION_PLAN.md` for detailed analysis and rationale.

## Notes

- Scripts in `utils/` are optional utilities, not required for core functionality
- Test scripts are used for CI/CD and manual validation
- Startup scripts are automatically called by Docker containers
- Archived scripts are kept for reference but not actively maintained

---

*Last updated: December 2025*

