# Monetization Quick Reference

## 🎯 The Path to Consistent Profits

```
Backtesting → Validation → Paper Trading → Live Trading (Small) → Scale Gradually
```

## ✅ Minimum Requirements Before Going Live

| Metric | Minimum | Your System Output |
|--------|---------|-------------------|
| Profit Factor | > 1.5 | `trades.profit_factor` |
| Win Rate | > 45% | `trades.win_rate` |
| Max Drawdown | < 20% | `drawdown.max_drawdown_pct` |
| Expectancy | > 0 | `trades.expectancy` |
| Sharpe Ratio | > 1.5 | Calculate from returns |

**❌ Red Flags (DO NOT TRADE):**
- Profit factor < 1.2
- Max drawdown > 30%
- Win rate < 40% AND avg_loss > 2x avg_win
- Only profitable in 1-2 specific months

## 📊 Position Sizing (Kelly Criterion)

**Formula:**
```
f* = (p × b - q) / b

Where:
- p = win probability (win_rate / 100)
- q = loss probability (1 - p)
- b = win/loss ratio (avg_win / abs(avg_loss))
```

**Recommended Risk Per Trade:**
- **Conservative**: 0.25 × Kelly (or 1-2% max)
- **Moderate**: 0.5 × Kelly (or 2-4% max)
- **Aggressive**: 0.75 × Kelly (or 4-8% max)

**For Crypto (High Volatility):**
- Start with **1-2% risk per trade**
- Never risk > 2% initially
- Scale up only after 3+ months of consistent profits

## 🔍 Overfitting Detection

**Walk-Forward Analysis:**
```
Training Period: 70% of data
Testing Period: 30% of data

If test performance < 50% of training → OVERFITTED
```

**Red Flags:**
- Test return < 50% of training return
- Test Sharpe < 0.5 while training Sharpe > 1.5
- Strategy profitable in training but losing in test

## 📈 Realistic Expectations

**Conservative (Low Risk):**
- Annual return: 15-30%
- Max drawdown: 5-10%
- Example: $10,000 → $11,500-$13,000/year

**Moderate (Medium Risk):**
- Annual return: 30-60%
- Max drawdown: 10-20%
- Example: $10,000 → $13,000-$16,000/year

**Aggressive (High Risk):**
- Annual return: 60-100%+
- Max drawdown: 20-40%
- Example: $10,000 → $16,000-$20,000/year (or -$4,000)

**Key:** Consistency > High returns. 30% consistent beats 100% inconsistent.

## 🚦 Risk Management Rules

**1. Maximum Risk Per Trade:**
- Risk ≤ 1-2% of account balance (start conservative)
- Risk = Position Size × (Entry Price - Stop Loss)

**2. Maximum Drawdown Limits:**
- Drawdown > 10% → Reduce position size by 50%
- Drawdown > 15% → Stop trading, review strategy
- Drawdown > 20% → Halt trading, major review needed

**3. Daily Loss Limit:**
- Daily loss limit = 3-5% of account
- If hit → Stop trading for the day

**4. Correlation Limits:**
- Don't trade multiple correlated pairs simultaneously
- BTCUSDT + ETHUSDT = high correlation → risk doubles

## 📅 Action Plan

### Week 1-2: Validation
- [ ] Run walk-forward analysis
- [ ] Test out-of-sample periods
- [ ] Calculate risk metrics
- [ ] Check for overfitting

### Week 3-4: Paper Trading Setup
- [ ] Set up paper trading environment
- [ ] Connect to exchange testnet
- [ ] Run strategy in paper mode
- [ ] Compare to backtest results

### Month 2-3: Paper Trading
- [ ] Trade paper account daily
- [ ] Track all metrics
- [ ] Identify execution issues
- [ ] Refine strategy if needed

### Month 4: Go Live (Small Capital)
- [ ] Start with $1,000-$5,000
- [ ] Use 1% risk per trade
- [ ] Monitor closely
- [ ] Compare to paper trading

### Month 5-6: Scale Gradually
- [ ] If profitable → increase capital 2x
- [ ] Add second instrument (if validated)
- [ ] Monitor correlation and drawdown
- [ ] Continue scaling only if performance maintained

## 🛠️ Tools

**Validate Strategy:**
```bash
python backend/scripts/strategy_validator.py \
  --result backend/backtest_results/fast/BN_BTC_20230523_02000000_018dd7_5afd2c.json \
  --kelly_calc
```

**Run Walk-Forward Analysis:**
```bash
# Test multiple time windows
for start_date in "2023-01-01" "2023-02-01" "2023-03-01"; do
  docker-compose exec backend python backend/run_backtest.py \
    --instrument BTCUSDT \
    --dataset day-2023-05-23 \
    --config external/data_downloads/configs/binance_futures_btcusdt_l2_trades_config.json \
    --start "${start_date}T00:00:00Z" \
    --end "${start_date}T23:59:59Z" \
    --fast
done
```

## ⚠️ Common Pitfalls

1. **Overconfidence from Backtesting**
   - Live trading typically achieves 50-70% of backtest performance
   - Use conservative estimates

2. **Ignoring Transaction Costs**
   - Fees, slippage, spreads eat profits
   - Always include realistic fees in backtests

3. **Over-Trading**
   - More trades ≠ more profit
   - Focus on high-probability setups only

4. **Revenge Trading**
   - After a loss, don't increase position size
   - Set daily loss limits (hard stops)

5. **Not Adapting to Market Changes**
   - Markets evolve, strategies need maintenance
   - Monitor performance monthly

## 🎓 Key Principles

1. **Backtesting ≠ Live Trading**
   - Backtests are optimistic
   - Paper trade first, always

2. **Risk Management > Strategy**
   - Wrong position size → blow up account
   - Right position size → consistent profits

3. **Consistency > High Returns**
   - 30% consistent beats 100% inconsistent
   - Compounding works over time

4. **Start Small, Scale Gradually**
   - Validate with small capital first
   - Scale only if performance maintained

5. **Discipline is Everything**
   - Follow the system
   - Don't override decisions emotionally

## 📚 Resources

- **Full Guide**: See `MONETIZATION_GUIDE.md` for detailed explanations
- **Strategy Validator**: `backend/scripts/strategy_validator.py`
- **Backtest Results**: `backend/backtest_results/`

---

**Remember:** The best backtest in the world is worthless if you can't execute it live with proper risk management.

**Start small, validate thoroughly, scale gradually, and never risk more than you can afford to lose.**

