# Live Execution Documentation

> **Source of Truth (SSOT)** for live execution system - 4 core documents

## Core Documents (4 Files)

1. **ROADMAP.md** ⭐ - Complete implementation roadmap
   - 6-phase implementation plan (12 weeks)
   - Detailed tasks and deliverables per phase
   - Success criteria and timelines
   - Critical implementation guidelines
   - Deployment architecture summary
   - Current backend structure reference
   - **START HERE**: Complete roadmap for implementation

2. **IMPLEMENTATION_GUIDE.md** - Detailed implementation instructions
   - Context and requirements
   - NautilusTrader documentation alignment
   - Current implementation reference (aligned with actual backend structure)
   - 6-phase implementation checklist
   - Critical implementation guidelines
   - Success criteria
   - **USE WITH**: ROADMAP.md for step-by-step implementation

3. **FILE_ORGANIZATION.md** - File organization strategy ⭐
   - Current backend structure (December 2025)
   - Target structure for live execution
   - Clear separation of live vs backtest code
   - Import patterns and boundaries
   - 6-phase migration strategy
   - **Key**: Documents actual current structure (`backend/core/engine.py` for BacktestEngine)

4. **DEVELOPMENT_PROMPT.md** - Concise development prompt (500 chars)
   - Quick reference for development
   - Use with other documents for context

## Quick Start

1. **Start Here**: Read `ROADMAP.md` for complete implementation roadmap
2. **Details**: Read `IMPLEMENTATION_GUIDE.md` for step-by-step instructions
3. **Structure**: Read `FILE_ORGANIZATION.md` for file organization
4. **Quick Ref**: Use `DEVELOPMENT_PROMPT.md` for quick reference

## Status

**Planning Phase** - Architecture complete, implementation pending

**Documentation Status**: ✅ Complete - All relevant information in 4 core documents

**Deployment Recommendation**: ✅ Separate Services (Docker Compose Profiles)

## Related Documentation

- `docs/backtesting/CURRENT_SYSTEM.md` - Reference implementation (backtest)
- `docs/FUSE_SETUP.md` - GCS FUSE setup guide

---

*Last updated: December 2025*

