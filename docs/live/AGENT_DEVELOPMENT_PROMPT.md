# Live Execution Component - Agent Development Prompt

> **Use this prompt for AI agent development. Always reference SSOT documents and use Context7.**

## Mission

Develop the **live execution system** for Odum Execution Services following the SSOT documentation and maintaining consistency with the existing backtesting infrastructure.

---

## Development Approach

### 1. Always Use SSOT Documents

**Primary Documents** (SSOT):
- `docs/live/ARCHITECTURE.md` - Complete architecture design, component specifications, system design
- `docs/live/ROADMAP.md` - Complete implementation roadmap, phases, architecture decisions
- `docs/live/FILE_ORGANIZATION.md` - File structure, organization, migration strategy
- `docs/live/README.md` - Documentation overview and quick start

**Reference Documents**:
- `docs/backtesting/CURRENT_SYSTEM.md` - Reference implementation (backtest system)
- `docs/FUSE_SETUP.md` - GCS FUSE setup guide

**Key Principle**: Documents are SSOT. Always check documents first before making assumptions.

### 2. Always Use Context7

- Use Context7 to get latest NautilusTrader documentation
- Use Context7 for external library documentation (Deribit API, Interactive Brokers, etc.)
- Verify implementation patterns against Context7 best practices
- Check Context7 for any technical questions about libraries or frameworks

### 3. Keep Documents Updated

- Update SSOT documents as implementation progresses
- Keep documents coherent and aligned with actual implementation
- Document any deviations or new decisions in appropriate documents
- Ensure documents reflect current state, not just planned state

---

## Development Workflow

### Step 1: Understand Current State
1. Read `docs/live/ARCHITECTURE.md` to understand system design and component specifications
2. Read `docs/live/ROADMAP.md` to understand current phase and requirements
3. Read `docs/live/FILE_ORGANIZATION.md` to understand file structure
4. Review `docs/backtesting/CURRENT_SYSTEM.md` for reference patterns
5. Check existing codebase structure
6. Use Context7 for NautilusTrader documentation and patterns

### Step 2: Plan Implementation
1. Review architecture requirements (from ARCHITECTURE.md component specifications)
2. Identify what needs to be built (from ROADMAP.md current phase)
3. Check file organization requirements (from FILE_ORGANIZATION.md)
4. Use Context7 to research NautilusTrader patterns and any needed libraries
5. Plan implementation following existing patterns where applicable

### Step 3: Implement
1. Follow file structure from FILE_ORGANIZATION.md
2. Implement according to phase requirements from ROADMAP.md
3. Use Context7 for technical documentation as needed
4. Maintain consistency with backtest system patterns

### Step 4: Update Documents
1. Update ARCHITECTURE.md if component design changes or new patterns emerge
2. Update ROADMAP.md if implementation deviates or new decisions are made
3. Update FILE_ORGANIZATION.md if file structure changes
4. Keep all SSOT documents coherent and aligned with actual code
5. Document any new patterns or approaches discovered
6. Ensure all documents reference each other properly

### Step 5: Verify
1. Verify implementation aligns with SSOT documents
2. Check consistency with backtest system
3. Ensure documents are up to date
4. Test according to phase success criteria

---

## Key Principles

### Document-Driven Development
- **SSOT First**: Always check documents before making decisions
- **Update as You Go**: Keep documents updated during implementation
- **Coherence**: Ensure documents remain coherent and aligned
- **Single Source**: Documents are the source of truth, not code comments or prompts

### Technical Approach
- **Use Context7**: Always use Context7 for external documentation
- **Consistency**: Maintain consistency with backtest system where applicable
- **Modularity**: Follow existing modular design patterns
- **Best Practices**: Follow Context7 best practices for libraries and frameworks

### Implementation Guidelines
- Follow phase requirements from ROADMAP.md
- Use file structure from FILE_ORGANIZATION.md
- Reference backtest system patterns from CURRENT_SYSTEM.md
- Use Context7 for technical questions

---

## When to Update Documents

Update SSOT documents when:
- Implementation deviates from planned approach
- New decisions are made during development
- File structure changes
- New patterns or approaches are discovered
- Phase requirements change
- Architecture decisions are refined

**Always**: Keep documents coherent and aligned with actual implementation state.

---

## Context7 Usage

Use Context7 for:
- NautilusTrader documentation (TradingNode, BacktestNode, etc.)
- External API documentation (Deribit, Interactive Brokers, etc.)
- Library documentation (protobuf, gRPC, PostgreSQL, etc.)
- Best practices and patterns
- Technical implementation questions

**Always**: Verify patterns and approaches against Context7 documentation.

---

## Remember

- **Documents are SSOT**: All specific details are in the documents
- **Use Context7**: Always use Context7 for external documentation
- **Keep Updated**: Update documents as you implement
- **Stay Coherent**: Ensure documents remain aligned and coherent
- **Check First**: Check documents before making assumptions

---

**This prompt is a guide. All specific requirements, decisions, and details are in the SSOT documents.**
