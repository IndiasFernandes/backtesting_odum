# Live Execution Documentation

> **Source of Truth (SSOT)** for live execution system - 4 core documents

## Core Documents (SSOT - Single Source of Truth)

**Important**: These documents are SSOT. Always reference them for specific details. Update them as implementation progresses to keep them coherent. Always use Context7 for external documentation.

1. **ARCHITECTURE.md** ⭐ - Complete architecture design
   - High-level architecture and component design
   - Component specifications and interfaces
   - Data flow and integration patterns
   - Deployment architecture (local development)
   - Monitoring and observability
   - **SSOT for**: Architecture design, component specifications, system design

2. **ROADMAP.md** ⭐ - Complete implementation roadmap
   - Implementation phases, tasks, deliverables
   - Architecture decisions and guidelines
   - Success criteria and timelines
   - **SSOT for**: Implementation plan, architecture decisions, requirements

3. **FILE_ORGANIZATION.md** ⭐ - File organization strategy
   - Current and target file structure
   - Directory organization and boundaries
   - Migration strategy
   - **SSOT for**: File structure, code organization, import patterns

4. **DEVELOPMENT_PROMPT.md** - Development workflow guide
   - How to use SSOT documents
   - Development workflow
   - Context7 usage guidelines
   - **SSOT for**: Development approach and workflow

5. **AGENT_DEVELOPMENT_PROMPT.md** - AI agent development guide
   - Agent-specific development workflow
   - Document update guidelines
   - Context7 usage for agents
   - **SSOT for**: AI agent development approach

## Quick Start

1. **Read SSOT Documents**: Start with `ARCHITECTURE.md` for system design, then `ROADMAP.md` for implementation plan, and `FILE_ORGANIZATION.md` for file structure
2. **Follow Development Prompt**: Use `DEVELOPMENT_PROMPT.md` for workflow
3. **Use Context7**: Always use Context7 for external documentation (NautilusTrader, etc.)
4. **Update Documents**: Keep documents updated as you implement, keep them coherent

**Key Principle**: Documents are SSOT. Always check documents first, update them as you go, keep them coherent. Always use Context7 for external documentation.

## Status

**Phase 1 Complete** ✅ - Core Infrastructure & Docker Setup completed

**Phase 1 Achievements**:
- ✅ Database schema with 19 columns in `unified_orders` (supports OMS, Risk Engine, Smart Router)
- ✅ Performance indexes (8 indexes) for risk engine queries
- ✅ Configuration framework (`backend/live/config/loader.py`) with env var substitution
- ✅ 2 Alembic migrations applied
- ✅ All components tested and verified

**Current Phase**: Phase 2 - TradingNode Integration (ready to start)

**Documentation Status**: ✅ Complete - All relevant information in 4 core documents

**Deployment**: ✅ Docker Compose Profiles (`backtest`, `live`, `both`) - All working

## Documentation Organization

**SSOT Documents** (Core - Always Update):
- `ARCHITECTURE.md` - System architecture and design
- `ROADMAP.md` - Implementation roadmap and phases
- `FILE_ORGANIZATION.md` - File structure and organization
- `README.md` - Documentation overview (this file)

**Implementation Documentation** (Phase-specific):
- `implementation/phase1/` - Phase 1 implementation files
  - `PHASE1_IMPLEMENTATION_PLAN.md` - Phase 1 detailed plan
  - `PHASE1_COMPLETION_SUMMARY.md` - Phase 1 completion summary
  - `PRE_PUSH_CHECKLIST.md` - Pre-push verification checklist
- `implementation/testing/` - Testing documentation
  - `MANUAL_TESTING_GUIDE.md` - Manual testing procedures
  - `PHASE1_TEST_PLAN.md` - Phase 1 test plan
  - `TEST_RESULTS.md` - Test results and verification

**Note**: Implementation files are organized by phase and purpose. Only the 4 SSOT documents (`ARCHITECTURE.md`, `ROADMAP.md`, `FILE_ORGANIZATION.md`, `README.md`) are the single source of truth and must be kept updated as implementation progresses.

## Related Documentation

- `docs/backtesting/CURRENT_SYSTEM.md` - Reference implementation (backtest)
- `docs/FUSE_SETUP.md` - GCS FUSE setup guide

---

*Last updated: December 2025*

