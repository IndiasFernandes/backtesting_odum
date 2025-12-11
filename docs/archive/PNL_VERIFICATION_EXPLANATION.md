# PnL Calculation Verification - Explanation

## What Needs to Be Verified?

The **PnL Calculation Verification** checks that the mathematical relationships between different PnL values are correct according to accounting principles.

## The Problem Found

From the test results, we have:
- **Balance Change**: -7,918.30 USDT
- **Realized PnL**: -898.10 USDT  
- **Commissions**: 11,690.54 USDT
- **Unrealized PnL (before closing)**: 6,682.32 USDT

### Expected Formula
According to accounting principles:
```
Balance Change = Realized PnL - Commissions
```

### What We Calculated
```
Balance Change = -898.10 - 11,690.54 = -12,588.64 USDT
```

### What We Actually Got
```
Balance Change = -7,918.30 USDT
```

### The Mismatch
**Expected**: -12,588.64 USDT  
**Actual**: -7,918.30 USDT  
**Difference**: 4,670.34 USDT ❌

## Why This Matters

This verification ensures:
1. **Accounting Accuracy**: The balance change correctly reflects all trading activity
2. **Commission Tracking**: Commissions are properly deducted from account balance
3. **PnL Integrity**: Realized PnL calculations are correct
4. **Production Readiness**: Financial calculations must be 100% accurate

## Possible Causes

1. **Unrealized PnL Not Realized**: The unrealized PnL (6,682.32) might not have been properly converted to realized when positions were closed
2. **Commission Calculation**: Commissions might be calculated incorrectly or double-counted
3. **Balance Calculation**: The final balance might not account for all transactions
4. **Position Closing Logic**: The logic for closing positions and realizing PnL might have an issue

## What Needs to Be Done

1. **Trace the Calculation**: Follow the code path from `strategy_evaluator.py` to see how balance_change is calculated
2. **Verify Position Closing**: Check if unrealized PnL is properly added to realized PnL when positions close
3. **Check Commission Deduction**: Verify commissions are subtracted from balance correctly
4. **Compare with NautilusTrader**: Ensure our calculation matches NautilusTrader's internal accounting

## Current Status

- ✅ Net PnL = Realized PnL (after closing) - **CORRECT**
- ❌ Balance Change = Realized - Commissions - **MISMATCH FOUND**
- ⏳ Need to investigate why balance_change doesn't match expected formula

## Next Steps

1. Review `strategy_evaluator.py` line 274: `total_pnl = final_balance - starting_balance`
2. Check if `final_balance` includes unrealized PnL realization
3. Verify commission deduction logic
4. Compare with NautilusTrader documentation for correct formula

