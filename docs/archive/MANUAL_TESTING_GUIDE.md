# Manual Testing Guide - Step by Step

## Step 1: CLI-Frontend Alignment Test

### Part A: Run Backtest via UI

1. **Open the UI in your browser:**
   - Navigate to: http://localhost:5173/run
   - You should see the "Run Backtest" page

2. **Verify form is pre-filled with example values:**
   - Instrument: `BTCUSDT`
   - Dataset: `day-2023-05-23`
   - Config: `binance_futures_btcusdt_l2_trades_config.json`
   - Start Time: `2023-05-23T02:00`
   - End Time: `2023-05-23T02:05`
   - Snapshot Mode: `both`
   - Report Mode: ✓ checked
   - Export Ticks: (can be checked if you want)

3. **Check the CLI Preview panel:**
   - Look at the CLI command shown in the preview
   - Click "Copy" button to copy the command
   - **Save this command** - you'll need it later
   - Verify the command format looks correct:
     ```
     python backend/run_backtest.py \
       --instrument BTCUSDT \
       --dataset day-2023-05-23 \
       --config external/data_downloads/configs/binance_futures_btcusdt_l2_trades_config.json \
       --start 2023-05-23T02:00:00Z \
       --end 2023-05-23T02:05:00Z \
       --snapshot_mode both \
       --report
     ```

4. **Click "Run Backtest" button:**
   - Watch for status updates ("Initializing...", "Loading...", "Running...")
   - Wait for completion
   - Note the **Run ID** displayed in the results panel
   - **Write down the Run ID** - you'll need it for comparison

5. **Check the results:**
   - Verify summary cards show:
     - Orders count
     - Fills count
     - PnL (with color coding)
     - Commissions
   - Note the values for later comparison

### Part B: Execute CLI Command

Now we'll run the same backtest using the CLI command you copied.

**Option 1: Using the test script (Recommended)**

Run this command in your terminal:

```bash
cd /Users/indiasfernandes/New\ Ikenna\ Repo/execution-services/data_downloads
./test_cli_alignment.sh report
```

The script will:
- Generate the CLI command
- Execute it in Docker
- Show you the Run ID
- Provide comparison instructions

**Option 2: Manual CLI execution**

If you prefer to run manually:

1. Copy the CLI command from the UI preview
2. Run it in Docker:
   ```bash
   docker-compose exec backend bash -c "cd /app && <paste_your_cli_command>"
   ```
3. Note the Run ID from the output

### Part C: Compare Results

After both runs complete, compare the results:

1. **Find the result files:**
   - UI result: `backend/backtest_results/report/<ui_run_id>/summary.json`
   - CLI result: `backend/backtest_results/report/<cli_run_id>/summary.json`

2. **Compare the JSON files** (excluding run_id and timestamps):

```bash
# Extract run_ids from the files
UI_RUN_ID="<paste_ui_run_id_here>"
CLI_RUN_ID="<paste_cli_run_id_here>"

# Compare results (excluding run_id and timestamps)
docker-compose exec backend bash -c "cd /app && \
  jq -S 'del(.run_id, .metadata.timestamp)' backend/backtest_results/report/${UI_RUN_ID}/summary.json > /tmp/ui_result.json && \
  jq -S 'del(.run_id, .metadata.timestamp)' backend/backtest_results/report/${CLI_RUN_ID}/summary.json > /tmp/cli_result.json && \
  diff /tmp/ui_result.json /tmp/cli_result.json"
```

3. **Expected result:**
   - If results match: No output (files are identical)
   - If results differ: You'll see the differences

4. **Verify in UI:**
   - Navigate to http://localhost:5173/ (comparison page)
   - Both run_ids should appear in the table
   - Compare the summary metrics (PnL, orders, fills, commissions)
   - They should match exactly

## Step 2: Responsiveness Testing

### Desktop (1920x1080) - Already Verified ✅

### Tablet (768x1024)

1. Open browser DevTools (F12 or Cmd+Option+I)
2. Click device toolbar icon (or Cmd+Shift+M)
3. Select "iPad" or set custom: 768x1024
4. Test each page:
   - `/run` - Check form layout
   - `/` (comparison) - Check table scrolling
   - `/definitions` - Check editor layout

### Mobile (375x667)

1. In DevTools, select "iPhone SE" or set custom: 375x667
2. Test each page:
   - `/run` - Check form usability
   - `/` (comparison) - Check horizontal scroll
   - `/definitions` - Check editor usability

**What to check:**
- No horizontal scrolling (except comparison table - expected)
- Buttons are clickable
- Text is readable
- Forms are usable

## Step 3: Feature Verification

### ResultDetailModal

1. Navigate to http://localhost:5173/
2. Click "View" button on any report mode result
3. Verify:
   - Modal opens correctly
   - Summary section displays
   - Performance metrics show
   - Charts render (PnL, OHLC, tick price)
   - Fills table displays data
   - Rejected orders table displays (if any)
   - Download buttons work

### Download Functionality

1. In ResultDetailModal, click download buttons:
   - "Download Full Result JSON"
   - "Download Summary JSON"
   - "Download Fills JSON" (if available)
   - "Download Rejected Orders JSON" (if available)
2. Verify files download correctly
3. Open JSON files and verify content

### Sorting

1. On comparison page, click column headers:
   - "Executed At" - Should sort by execution time
   - "Time Window" - Should sort by time window start
2. Verify results reorder correctly
3. Verify sort indicator (↓) appears

### Toast Notifications

1. Trigger actions that show toasts:
   - Save config in Definitions page
   - Run backtest (success/error)
   - Copy CLI command
2. Verify toasts appear and disappear correctly

## Success Criteria

✅ **CLI Alignment:**
- CLI command executes successfully
- Results match exactly (except run_id and timestamps)
- Both results appear in comparison page with matching metrics

✅ **Responsiveness:**
- Tablet layout works (may have horizontal scroll on comparison table)
- Mobile layout works (may have horizontal scroll on comparison table)

✅ **Features:**
- All features work as expected
- No console errors
- No visual glitches

