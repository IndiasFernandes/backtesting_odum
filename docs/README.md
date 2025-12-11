# Documentation Structure

This directory contains all documentation organized by system component.

## Structure

```
docs/
├── live/                    # Live Execution System Documentation (SSOT)
│   ├── ARCHITECTURE.md      # Complete architecture and design
│   ├── IMPLEMENTATION_GUIDE.md  # Step-by-step implementation instructions
│   └── SUMMARY.md          # Executive summary and overview
│
├── backtesting/            # Backtesting System Documentation (SSOT)
│   ├── CURRENT_SYSTEM.md   # Current system architecture and spec
│   ├── COMPLETION_ROADMAP.md  # What's needed to finish CeFi + TradFi
│   └── EXECUTION_ALGORITHMS.md  # Execution algorithms guide
│
└── README.md               # This file
```

## Live Execution (`docs/live/`)

**Source of Truth** for live execution system development.

1. **ARCHITECTURE.md** - Complete architecture, design decisions, component details, implementation phases
2. **IMPLEMENTATION_GUIDE.md** - Comprehensive implementation prompt with all requirements, references, and checklists
3. **SUMMARY.md** - Executive summary, key objectives, highlights, and quick reference

**Status**: Planning phase - not yet implemented

## Backtesting (`docs/backtesting/`)

**Source of Truth** for backtesting system.

1. **CURRENT_SYSTEM.md** - Current architecture, specification, CLI reference, configuration schema
2. **COMPLETION_ROADMAP.md** - What's needed to complete CeFi + TradFi support
3. **EXECUTION_ALGORITHMS.md** - TWAP, VWAP, Iceberg algorithms guide

**Status**: CeFi complete ✅, TradFi in progress ⏳

## Archive (`docs/archive/`)

Historical documentation and archived files (not SSOT).

## Other Documentation

- **Root level**: `README.md` - Quick start and overview
- **Root level**: `FRONTEND_SERVICE_DETECTION.md` - Frontend service detection implementation
- **Root level**: `FRONTEND_UI_SPEC.md` - Frontend UI specification
- **Root level**: `FUSE_SETUP.md` - GCS FUSE setup guide

---

*Last updated: December 2025*

