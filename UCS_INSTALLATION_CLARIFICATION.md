# UCS Installation - Do You Need to Clone the Repo?

## Answer: **NO, you don't need to clone the repo!**

---

## Installation Method

**Install directly from GitHub via pip:**

```bash
pip install git+https://github.com/IggyIkenna/unified-cloud-services.git
```

**That's it!** No cloning needed. The package is installable directly from GitHub.

---

## Why This Works

The `unified-cloud-services` repository is set up as a Python package that can be installed directly from GitHub:

1. **GitHub URL installation** - pip can install from GitHub URLs
2. **Already in requirements.txt** - Your `backend/requirements.txt` already has it:
   ```
   git+https://github.com/IggyIkenna/unified-cloud-services.git
   ```

---

## Quick Test Steps

### Step 1: Install UCS

```bash
cd /Users/indiasfernandes/New\ Ikenna\ Repo/execution-services/data_downloads

# Install UCS
pip install git+https://github.com/IggyIkenna/unified-cloud-services.git

# OR install all dependencies
pip install -r backend/requirements.txt
```

### Step 2: Verify Installation

```bash
python3 -c "from unified_cloud_services import UnifiedCloudService; print('✅ UCS installed')"
```

### Step 3: Run Test Script

```bash
# Quick test (uses helper script)
./QUICK_TEST_UCS.sh

# OR run directly
python3 backend/scripts/test_ucs_connection.py
```

---

## What Gets Installed

When you run `pip install git+https://github.com/IggyIkenna/unified-cloud-services.git`:

1. ✅ Downloads the package from GitHub
2. ✅ Installs it into your Python environment
3. ✅ Makes `unified_cloud_services` importable
4. ✅ No local clone needed

**Location:** Installed in your Python site-packages (e.g., `~/.local/lib/python3.x/site-packages/unified_cloud_services/`)

---

## When Would You Clone?

You would only clone the repo if:

- ❌ **You want to modify UCS source code** (not needed)
- ❌ **You want to develop UCS itself** (not needed)
- ❌ **You want to see the source code** (can browse on GitHub)

**For your use case:** Just install it via pip - no cloning needed!

---

## Test Before Integration

**Always test first:**

```bash
# 1. Install UCS
pip install git+https://github.com/IggyIkenna/unified-cloud-services.git

# 2. Run test script
python3 backend/scripts/test_ucs_connection.py

# 3. If tests pass → Ready to integrate!
# 4. If tests fail → Fix issues before integrating
```

---

## Summary

| Question | Answer |
|----------|--------|
| **Do I need to clone the repo?** | ❌ **NO** |
| **How do I install UCS?** | `pip install git+https://github.com/IggyIkenna/unified-cloud-services.git` |
| **Where is it installed?** | Python site-packages (automatic) |
| **Do I need the source code?** | ❌ **NO** - just import and use |
| **Can I test it first?** | ✅ **YES** - use `test_ucs_connection.py` |

---

## Next Steps

1. ✅ Install UCS: `pip install git+https://github.com/IggyIkenna/unified-cloud-services.git`
2. ✅ Test connection: `python3 backend/scripts/test_ucs_connection.py`
3. ✅ Verify credentials: Check `.env` and `.secrets/gcs/gcs-service-account.json`
4. ✅ Once tests pass → Integrate into `backtest_engine.py` and `results.py`

---

**TL;DR:** Just install via pip - no cloning needed! 🚀

