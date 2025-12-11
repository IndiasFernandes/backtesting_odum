# Backend Scripts

## Structure

```
backend/scripts/
├── start.sh                    # Container startup script (handles FUSE mounting)
├── mount_gcs.sh                # GCS FUSE mounting script
├── setup_env.sh                # Environment setup script
├── setup_ucs.sh                # UCS setup script
├── verify_secrets.sh           # Secrets verification script
│
├── tests/                      # Test scripts
│   ├── test_docker_infrastructure.sh
│   ├── test_running_services.sh
│   ├── test_cli_alignment.sh
│   └── test_gcs_backtest.sh
│
└── utils/                      # Utility scripts
    ├── compare_exec_algorithms.py
    ├── upload_backtest_results_to_gcs.py
    └── gcs_write_examples.py
```

## Script Categories

### Startup Scripts
- `start.sh` - Main container startup (called by Dockerfile)
- `mount_gcs.sh` - GCS FUSE mounting (called by start.sh)

### Setup Scripts
- `setup_env.sh` - Environment variable setup
- `setup_ucs.sh` - Unified Cloud Services setup
- `verify_secrets.sh` - GCS credentials verification

### Test Scripts (`tests/`)
- `test_docker_infrastructure.sh` - Docker infrastructure tests
- `test_running_services.sh` - Service health tests
- `test_cli_alignment.sh` - CLI alignment tests
- `test_gcs_backtest.sh` - GCS backtest tests

### Utility Scripts (`utils/`)
- `compare_exec_algorithms.py` - Compare execution algorithm performance
- `upload_backtest_results_to_gcs.py` - Upload results to GCS
- `gcs_write_examples.py` - GCS write examples

## Usage

### Running Tests
```bash
# Run all infrastructure tests
./backend/scripts/tests/test_docker_infrastructure.sh

# Run service health tests
./backend/scripts/tests/test_running_services.sh
```

### Running Utilities
```bash
# Compare execution algorithms
python backend/scripts/utils/compare_exec_algorithms.py

# Upload backtest results to GCS
python backend/scripts/utils/upload_backtest_results_to_gcs.py
```

## Notes

- Scripts in `utils/` are optional utilities, not required for core functionality
- Test scripts are used for CI/CD and manual validation
- Startup scripts are automatically called by Docker containers

---

*Last updated: December 2025*

