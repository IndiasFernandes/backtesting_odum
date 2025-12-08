# Report Mode Enhancements - Fills & Rejected Orders

## Overview
Enhanced the backtest results UI to differentiate between fast and report modes, and added comprehensive fills and rejected orders analysis for report mode results.

## Features Implemented

### 1. Mode Differentiation
- **Visual Badges**: Fast mode results show a blue "⚡ Fast" badge, report mode shows a purple "📊 Report" badge
- **Comparison Table**: Added a "Mode" column to clearly distinguish between fast and report results
- **Detail Modal**: Mode badge displayed in the result detail modal

### 2. Fills Information (Report Mode Only)
- **Fills Endpoint**: `/api/backtest/results/{run_id}/fills`
  - Returns all fill events from the timeline
  - Each fill includes: `order_id`, `price`, `quantity`
- **UI Display**:
  - Fills table showing order ID, price, and quantity
  - Shows first 100 fills with pagination indicator
  - Fill count and statistics
  - Download button for fills JSON

### 3. Rejected Orders Analysis (Report Mode Only)
- **Rejected Orders Endpoint**: `/api/backtest/results/{run_id}/rejected-orders`
  - Returns all denied/rejected orders from orders.json
  - Includes analysis:
    - Total rejected count
    - Breakdown by side (buy/sell)
    - Price range analysis (min, max, avg)
- **UI Display**:
  - Rejected orders table with order details
  - Analysis summary showing patterns
  - Shows first 50 rejected orders
  - Explanatory note about common rejection reasons
  - Download button for rejected orders JSON

### 4. Enhanced Comparison Table
- **New Columns**:
  - Mode badge column
  - Rejected orders count (report mode only)
  - Fill rate percentage shown under fills count
- **Improved Data Display**:
  - Fill count with percentage
  - Rejected count highlighted in red for report mode
  - "-" placeholder for fast mode (no rejected order data)

### 5. Performance Optimizations
- **Async Loading**: Fills and rejected orders load asynchronously when detail modal opens
- **Lazy Loading**: Only loads detailed data when viewing report mode results
- **Efficient Data Access**: Uses existing timeline.json and orders.json files

## API Endpoints

### GET `/api/backtest/results/{run_id}/fills`
Returns all fill events for a report mode result.

**Response:**
```json
[
  {
    "order_id": "O-20230523-020000-001-000-1",
    "price": 26982.2,
    "quantity": 0.042
  }
]
```

### GET `/api/backtest/results/{run_id}/rejected-orders`
Returns rejected orders with analysis.

**Response:**
```json
{
  "rejected_orders": [
    {
      "id": "O-20230523-020000-001-000-101",
      "side": "sell",
      "price": 26982.2,
      "amount": 0.148,
      "status": "denied"
    }
  ],
  "analysis": {
    "total_rejected": 775,
    "by_side": {
      "buy": 200,
      "sell": 575
    },
    "price_range": {
      "min": 26950.0,
      "max": 27000.0,
      "avg": 26975.0
    }
  }
}
```

## UI Components Updated

### `BacktestComparisonPage.tsx`
- Added Mode column with badges
- Added Rejected column
- Enhanced fills display with percentage
- Updated loading skeleton

### `ResultDetailModal.tsx`
- Added fills section (report mode only)
- Added rejected orders section (report mode only)
- Added download buttons for fills and rejected orders
- Mode badge display
- Async data loading with loading states

### `api.ts`
- Added `getFills()` method
- Added `getRejectedOrders()` method

## Backend Changes

### `server.py`
- Added `/api/backtest/results/{run_id}/fills` endpoint
- Added `/api/backtest/results/{run_id}/rejected-orders` endpoint
- Analysis logic for rejected orders patterns

## Usage

1. **View Comparison**: Navigate to `/compare` to see all results with mode badges
2. **View Details**: Click "View" on any report mode result to see fills and rejected orders
3. **Download Data**: Use download buttons to export fills or rejected orders as JSON

## Notes

- **Fast Mode**: Shows summary metrics only, no fills/rejected orders data
- **Report Mode**: Full detailed analysis including fills and rejected orders
- **Rejection Reasons**: Currently orders show status "denied" but specific rejection reasons are not captured in the current implementation. This could be enhanced by capturing `OrderDenied` events with reason codes from NautilusTrader.

## Future Enhancements

1. **Rejection Reason Capture**: Enhance backend to capture specific rejection reasons from NautilusTrader events
2. **Fill Analysis**: Add fill analysis (average fill price, slippage, etc.)
3. **Order Flow Visualization**: Add charts/graphs for order flow and fill patterns
4. **Filtering**: Add filters to comparison table (by mode, instrument, date range)
5. **Export Options**: Add CSV export for fills and rejected orders

