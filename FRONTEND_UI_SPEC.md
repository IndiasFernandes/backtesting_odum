# Frontend UI Specification

## Goals
- Production-grade trading/backtesting dashboard built on Vite + React + TypeScript + Tailwind (no starter boilerplate).
- Must handle large JSON/tick datasets with performant rendering (virtualization, chunked fetch, worker parsing).
- Zero hardcoded params: all selections map to the external JSON config and CLI flags.

## Layout (desktop-first, responsive)
- Left rail: dataset selector (scans `data_downloads/`), config selector (external JSON), time window pickers (UTC), snapshot mode selector, toggles for full mode and tick export, risk throttling display.
- Main header: instrument + venue display from selected config; env status badges (PARQUET vs GCS FUSE).
- Center grid:
  - CLI preview panel (renders exact `python run_backtest.py ...` command).
  - Parameter form cards (instrument info, venue/account, strategy mode).
  - Run controls: Run button (debounced), mode toggle (fast/full), snapshot mode dropdown, validation errors.
  - Results viewer: fast summary card (pnl, drawdown, fills), full-mode tabs (timeline list, orders table, tick chart with order markers, metadata panel).
  - Charts: tick graph with order markers; timeline chart for events; book depth snapshot overlay when available.
- Right rail (optional): run history (lists `backend/backtest_results/`), run metadata, download links for summary/ticks.

## Data Sources & Scanning
- Datasets: scan `data_downloads/` (FUSE-emulated) to list available datasets and discovered `trades.parquet` / `book_snapshot_5.parquet`.
- Configs: browse selectable JSON config files; UI never embeds defaults.
- Results: read summaries from `backend/backtest_results/`; full-mode tick JSON from `frontend/public/tickdata/`.

## Controls & Toggles
- Full mode toggle (switch): when on, auto-enables tick export.
- Tick export toggle: only active when full mode is selected.
- Snapshot mode dropdown: `trades | book | both`.
- Time window inputs: ISO UTC with validation against catalog bounds.
- Dataset selector: list datasets by folder; show validation if required files absent.
- Config selector: file picker; show parsed summary (instrument, venue, precision).
- Run button: executes via backend API; disabled if validation fails or run in flight.

## CLI Preview
- Render exact CLI line with current selections:
```
python run_backtest.py --instrument <instrument> --dataset <dataset> --config <config> --start <start> --end <end> --full <true|false> --export_ticks <true|false> --snapshot_mode <mode>
```
- Copy-to-clipboard and “open in terminal” hints.

## Performance & Architecture (React/Vite)
- Data loading: stream and chunk large JSON; parse in Web Workers to keep UI responsive.
- Rendering: virtualized tables/lists (e.g., orders, timeline); canvas/SVG for tick chart; lazy-load heavy panels.
- State: colocate state per feature, use React Query (or similar) for fetch caching; stale-while-revalidate for result polling.
- Bundling: Vite code-splitting, route-level and component-level dynamic imports; avoid shipping dev-only libs.
- Tailwind: build reusable primitives (cards, tabs, badges, form controls) and compose financial widgets (P&L card, drawdown meter, liquidity heatmap).
- Accessibility: keyboard nav for selectors, high-contrast theme for dark mode, ARIA labels on controls.

## Component Checklist
- DatasetSelector: scans `data_downloads/`, shows missing-file warnings.
- ConfigSelector: file picker + parsed summary view.
- TimeWindowPicker: UTC inputs with validation.
- SnapshotModeSelect: enumerated dropdown.
- ModeToggles: fast/full + tick export.
- CLICommandPreview: renders command string; copy button.
- RunButton: disabled while executing; shows status.
- SummaryCards: pnl, orders, fills, drawdown.
- TimelineList: virtualized events with filters.
- OrdersTable: virtualized, sortable.
- TickChart: plot ticks with order markers; downsample for large ranges; supports range brush.
- DepthSnapshotPanel: optional book view when `book_snapshot_5` exists.
- MetadataPanel: show env vars (`UNIFIED_CLOUD_LOCAL_PATH`, `UNIFIED_CLOUD_SERVICES_USE_PARQUET`, `UNIFIED_CLOUD_SERVICES_USE_DIRECT_GCS`, `DATA_CATALOG_PATH`), run_id, config hash.
- RunHistory: lists prior runs from `backend/backtest_results/` with links.
- DownloadLinks: summary/timeline/orders/ticks exports.

## UX & Validation
- Before run: validate dataset presence, config completeness, time window bounds, snapshot mode compatibility with available files.
- Errors: inline + toast; never auto-fall back to defaults.
- Loading: skeletons for cards, spinners for charts, progress for tick parsing.
- Empty states: clear instructions for missing datasets/configs.
- Tooltips: describe fast vs full, tick export cost, snapshot modes.

## Integration Expectations
- Backend API endpoints should mirror CLI flags; UI passes all parameters (no backend defaults).
- All paths remain relative to mounted volumes; ready for future GCS FUSE mount without UI change.
- Fast mode displays summary immediately; full mode fetches charts/ticks once available.

## Security & Reliability
- Do not execute arbitrary config contents; validate schema on load.
- Enforce size limits and streaming for large tick files; warn when files exceed thresholds.
- Use ETags or hashes for result caching; avoid caching tick blobs in Redis (if enabled).

## Visual Patterns (financial UI best practice)
- Grid-based layout, fixed header with context, dense tables with row hover, clear buy/sell color coding, persistent filters.
- Dark theme default; high-contrast palette for clarity; consistent spacing via Tailwind tokens.

