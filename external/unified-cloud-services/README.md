# Unified Cloud Services - Local Copy

## Setup Instructions

1. **Extract the zip file here:**
   - If you have `unified-cloud-services.zip`, extract it to this directory
   - The directory structure should be:
     ```
     external/unified-cloud-services/
     ├── setup.py (or pyproject.toml)
     ├── unified_cloud_services/
     │   ├── __init__.py
     │   └── ...
     └── ...
     ```

2. **Verify the package structure:**
   ```bash
   ls -la external/unified-cloud-services/
   # Should see setup.py or pyproject.toml
   ```

3. **Build Docker:**
   ```bash
   docker-compose build backend
   ```

The Dockerfile will automatically detect the local copy and use it instead of cloning from GitHub.

## What to Extract

If your zip file is named something like:
- `unified-cloud-services.zip` → Extract here
- `unified-cloud-services-master.zip` → Extract and rename the inner folder to `unified-cloud-services`

## Verification

After extracting, verify:
```bash
# Check if setup.py or pyproject.toml exists
ls external/unified-cloud-services/setup.py external/unified-cloud-services/pyproject.toml

# Check package structure
ls external/unified-cloud-services/unified_cloud_services/
```

