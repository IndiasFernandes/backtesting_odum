# Agent 2: UI Testing Agent

## Objective
Comprehensively test all UI components, buttons, functionalities, and result visualization to ensure production-ready user experience.

## System Context
- **Frontend URL**: `http://localhost:5173`
- **Backend API**: `http://localhost:8000`
- **Pages**: `/run`, `/compare`, `/definitions`
- **Tech Stack**: React + TypeScript + Vite + Tailwind CSS
- **API Client**: `frontend/src/services/api.ts`

## Key Files to Review
- `frontend/src/pages/BacktestRunnerPage.tsx` - Main runner page
- `frontend/src/pages/BacktestComparisonPage.tsx` - Comparison page
- `frontend/src/pages/DefinitionsPage.tsx` - Definitions page
- `frontend/src/services/api.ts` - API client
- `FRONTEND_UI_SPEC.md` - UI specification

## Testing Tasks

### 1. Backtest Runner Page (`/run`)

**Form Components:**
- ✅ Dataset selector: Verify it scans `data_downloads/raw_tick_data/by_date/` and lists available datasets (day-YYYY-MM-DD folders)
- ✅ Config selector: Verify it lists all JSON configs from `data_downloads/configs/` (preferred) or `external/data_downloads/configs/`
- ✅ Instrument input: Verify text input works, validation
- ✅ Time window pickers: Verify UTC datetime-local inputs, conversion to ISO8601
- ✅ Snapshot mode selector: Verify dropdown (trades/book/both) works
- ✅ Mode toggles: 
  - Fast mode checkbox
  - Report mode checkbox (mutually exclusive with fast)
  - Export ticks checkbox (only enabled when report=true)

**CLI Preview Panel:**
- ✅ Verify CLI command renders correctly with current form values
- ✅ Verify command format matches actual CLI syntax exactly
- ✅ Verify CLI preview updates when form values change
- ✅ Verify all form fields are reflected in CLI preview:
  - Instrument → `--instrument`
  - Dataset → `--dataset`
  - Config → `--config` (verify path format)
  - Start time → `--start` (verify ISO8601 UTC format)
  - End time → `--end` (verify ISO8601 UTC format)
  - Snapshot mode → `--snapshot_mode`
  - Fast mode → `--fast` flag
  - Report mode → `--report` flag
  - Export ticks → `--export_ticks` flag
- ✅ Test copy-to-clipboard functionality (if implemented)
- ✅ **CRITICAL**: Verify CLI preview command can be executed and produces same results as UI

**Run Button:**
- ✅ Verify button calls API correctly
- ✅ Verify button disabled during execution
- ✅ Verify status updates display during execution
- ✅ Verify error handling and display

**Results Display:**
- ✅ Verify summary cards display (PnL, orders, fills, commissions)
- ✅ Verify PnL color coding (green for positive, red for negative)
- ✅ Verify position statistics display
- ✅ Verify trade statistics display
- ✅ Verify run_id display

### 2. Comparison Page (`/compare`)

**Results List:**
- ✅ Verify all backtest results are listed
- ✅ Verify results load from `backend/backtest_results/`
- ✅ Verify summary information displays correctly
- ✅ Verify sorting/filtering (if implemented)
- ✅ Verify navigation to detailed views

**Result Details:**
- ✅ Verify detailed result view (if implemented)
- ✅ Verify timeline display (if implemented)
- ✅ Verify orders table (if implemented)
- ✅ Verify download links (if implemented)

### 3. Definitions Page (`/definitions`)

- ✅ Verify strategy definitions display
- ✅ Verify config editing (if implemented)
- ✅ Verify config saving (if implemented)

### 4. CLI-Frontend Alignment Testing

**CRITICAL REQUIREMENT:** UI must render exact CLI invocation preview, and CLI commands from UI must produce identical results.

**CLI Preview Accuracy:**
- ✅ Fill form with values, copy CLI preview command
- ✅ Execute copied CLI command in terminal
- ✅ Verify CLI command executes successfully
- ✅ Verify CLI produces same results as UI submission
- ✅ Compare result JSONs (should match except for run_id timestamp)
- ✅ Test with different form combinations:
  - Fast mode only
  - Report mode only
  - Report + export_ticks
  - Different snapshot modes
  - Different time windows

**CLI Command Format Verification:**
- ✅ Verify CLI command uses correct Python path: `python backend/run_backtest.py`
- ✅ Verify config path format (relative vs absolute)
- ✅ Verify time format is ISO8601 UTC (ends with Z)
- ✅ Verify boolean flags (`--fast`, `--report`, `--export_ticks`) appear correctly
- ✅ Verify enum values (`--snapshot_mode trades|book|both`) are correct

**End-to-End CLI-UI Alignment:**
- ✅ Run backtest via UI, note run_id and results
- ✅ Copy CLI preview command from UI
- ✅ Execute CLI command in container: `docker-compose exec backend <cli_command>`
- ✅ Verify CLI produces same results (compare JSON files)
- ✅ Verify both results appear in comparison page with same summary

### 5. API Integration

**API Calls:**
- ✅ Verify `GET /api/datasets` called correctly
- ✅ Verify `GET /api/configs` called correctly
- ✅ Verify `POST /api/backtest/run` called with correct payload
- ✅ Verify `GET /api/backtest/results` called correctly
- ✅ Verify error handling for API failures

**Loading States:**
- ✅ Verify loading spinners/skeletons display
- ✅ Verify loading states clear after completion
- ✅ Verify empty states display correctly

### 6. Error Handling

- ✅ Form validation errors display correctly
- ✅ API error messages display correctly
- ✅ Network errors handled gracefully
- ✅ Invalid config errors display correctly
- ✅ Missing data errors display correctly

### 7. Responsiveness

- ✅ Desktop layout (1920x1080)
- ✅ Tablet layout (768x1024)
- ✅ Mobile layout (375x667) - if applicable
- ✅ Verify components adapt to screen size

### 8. User Experience

- ✅ Form pre-fills with example values (as per spec)
- ✅ Status updates are clear and informative
- ✅ Results appear promptly after execution
- ✅ Navigation between pages works
- ✅ Browser back/forward works correctly

## Test Scenarios

### Scenario 1: Complete Backtest Flow with CLI Alignment
1. Navigate to `/run`
2. Select dataset: `day-2023-05-23`
3. Select config: `binance_futures_btcusdt_l2_trades_config.json`
4. Set instrument: `BTCUSDT`
5. Set time window: `2023-05-23T19:23:00Z` to `2023-05-23T19:28:00Z`
6. Select snapshot mode: `both`
7. Enable report mode
8. Enable export ticks
9. **Verify CLI preview renders correct command**
10. **Copy CLI preview command**
11. Click "Run Backtest"
12. Verify status updates appear
13. Verify results display after completion
14. Note run_id and results
15. **Execute copied CLI command in terminal**
16. **Verify CLI produces same results (compare JSON)**
17. Verify both results appear in comparison page

### Scenario 2: Fast Mode Quick Test
1. Navigate to `/run`
2. Fill form with minimal values
3. Enable fast mode only
4. Submit
5. Verify fast summary displays

### Scenario 3: Error Handling
1. Submit form with invalid time window
2. Submit form with missing dataset
3. Submit form with invalid config
4. Verify error messages display correctly

### Scenario 4: Comparison Page
1. Run multiple backtests
2. Navigate to `/compare`
3. Verify all results listed
4. Verify summary information correct

## Browser Testing
- ✅ Chrome/Chromium (latest)
- ✅ Firefox (latest)
- ✅ Safari (if on macOS)
- ✅ Edge (if available)

## Success Criteria
- ✅ All UI components function correctly
- ✅ All buttons trigger expected actions
- ✅ Form validation works
- ✅ **CLI preview renders exact CLI command**
- ✅ **CLI commands from UI produce identical results**
- ✅ **CLI-frontend alignment verified (same inputs = same results)**
- ✅ API integration works correctly
- ✅ Results display accurately
- ✅ Error handling works properly
- ✅ UI is responsive and accessible
- ✅ No console errors
- ✅ No visual glitches

## Deliverables
1. Test execution report with screenshots
2. **CLI-frontend alignment verification report**
3. **CLI command execution test results**
4. Bug reports with reproduction steps
5. UX improvement recommendations
6. Accessibility audit results
7. Performance metrics (load times, render times)

