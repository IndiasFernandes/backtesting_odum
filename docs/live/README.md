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

**Planning Phase** - Architecture complete, implementation pending

**Documentation Status**: ✅ Complete - All relevant information in 4 core documents

**Deployment Recommendation**: ✅ Separate Services (Docker Compose Profiles)

## Related Documentation

- `docs/backtesting/CURRENT_SYSTEM.md` - Reference implementation (backtest)
- `docs/FUSE_SETUP.md` - GCS FUSE setup guide

---

*Last updated: December 2025*

