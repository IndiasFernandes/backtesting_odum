# Live Execution Development Prompt

**Start Here**: Read `docs/live/ROADMAP.md` for complete 14-week implementation plan.

**Implementation**: Follow `docs/live/IMPLEMENTATION_GUIDE.md` for step-by-step instructions.

**File Structure**: See `docs/live/FILE_ORGANIZATION.md` for directory organization (`backend/live/` vs `backend/backtest/`).

**Quick Start**: 
1. Create `feature/live-execution` branch from `main` (see Git Workflow in ROADMAP.md)
2. Follow Phase 1: Core Infrastructure & Docker Setup (Weeks 1-2)
3. Add Docker profiles to existing `docker-compose.yml` (backward compatible)
4. Create `backend/live/` directory structure
5. Set up PostgreSQL schema for OMS/positions

**Key Requirements**: Use TradingNode for Binance/Bybit/OKX, external adapters for Deribit/IB. Implement Execution Orchestrator, Unified OMS, Position Tracker, Risk Engine, Smart Router. Use UCS for all GCS operations (PRIMARY interface). Follow 7-phase roadmap in ROADMAP.md.

