# UCS Installation Status

## Current Issue: Disk Space Full

**Problem:** Disk is 100% full (208GB used, only 124MB free)

**Error:**
```
ERROR: Could not install packages due to an OSError: [Errno 28] No space left on device
```

---

## Solutions

### Option 1: Free Up Disk Space (Recommended)

1. **Clean pip cache:**
   ```bash
   pip cache purge
   ```

2. **Clean temporary files:**
   ```bash
   rm -rf /tmp/pip-*
   rm -rf ~/.cache/pip
   ```

3. **Check large files:**
   ```bash
   # Find large files in current directory
   du -sh * | sort -hr | head -10
   ```

4. **Clean Docker (if applicable):**
   ```bash
   docker system prune -a
   ```

### Option 2: Install to Different Location

If you have another disk with space:

```bash
# Create venv on different disk
python3 -m venv /path/to/other/disk/venv
source /path/to/other/disk/venv/bin/activate
pip install git+https://github.com/IggyIkenna/unified-cloud-services.git
```

### Option 3: Use System Python with --break-system-packages

**⚠️ Not recommended, but works:**

```bash
python3 -m pip install --break-system-packages --user git+https://github.com/IggyIkenna/unified-cloud-services.git
```

---

## Test Script Status

The test script (`backend/scripts/test_ucs_connection.py`) is ready and will work once UCS is installed.

**To test after installation:**
```bash
source .venv/bin/activate  # or activate your venv
python backend/scripts/test_ucs_connection.py
```

---

## Next Steps

1. ✅ **Free up disk space** (at least 500MB recommended)
2. ✅ **Install UCS:** `pip install git+https://github.com/IggyIkenna/unified-cloud-services.git`
3. ✅ **Run test:** `python backend/scripts/test_ucs_connection.py`
4. ✅ **Verify credentials:** Check `.env` file has correct values
5. ✅ **Once tests pass:** Ready to integrate!

---

## Quick Disk Cleanup Commands

```bash
# Clean pip cache
pip cache purge

# Clean Python cache
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# Clean temporary files
rm -rf /tmp/pip-*
rm -rf ~/.cache/pip

# Check what's using space
du -sh ~/.cache ~/.local 2>/dev/null
```

---

**Status:** ⏸️ Waiting for disk space to be freed before installation can proceed.

