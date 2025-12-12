# Testing Documentation

This directory contains testing guides, plans, and results for the live execution system.

## Files

- **`MANUAL_TESTING_GUIDE.md`** - Comprehensive manual testing guide for 3 deployment modes
- **`PHASE1_TEST_PLAN.md`** - Phase 1 test plan and checklist
- **`TEST_RESULTS.md`** - Phase 1 test results and verification

## Testing Scripts

- **`backend/scripts/tests/test_deployments.sh`** - Automated test script
  - Tests all 3 deployment modes automatically
  - Usage: `./backend/scripts/tests/test_deployments.sh`

## Deployment Modes

1. **Backtest Only** - `docker-compose up -d` (default, backward compatible)
2. **Live Only** - `docker-compose --profile live up -d`
3. **Both** - `docker-compose --profile both up -d`

See `MANUAL_TESTING_GUIDE.md` for detailed testing procedures.

---

*Last updated: December 2025*

