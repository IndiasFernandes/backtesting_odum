"""Strategy evaluation and performance analysis module."""
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime
import math
import re

import pandas as pd

from nautilus_trader.model.identifiers import InstrumentId, Venue
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.objects import Money, Currency


class StrategyEvaluator:
    """Evaluates strategy performance with detailed PnL and trade analysis."""
    
    @staticmethod
    def evaluate_performance(
        engine,
        portfolio,
        config: Dict[str, Any],
        venue_config_name: str,
        close_positions: bool = True
    ) -> Dict[str, Any]:
        """
        Evaluate strategy performance with comprehensive metrics.
        
        Args:
            engine: BacktestEngine instance
            portfolio: Portfolio instance from backtest result
            config: Configuration dictionary
            venue_config_name: Venue name
            
        Returns:
            Dictionary with performance metrics
        """
        venue = Venue(venue_config_name)
        starting_balance = config["venue"]["starting_balance"]
        base_currency = config["venue"]["base_currency"]
        instrument_id = InstrumentId.from_str(config["instrument"]["id"])
        
        # Get account and balances
        account = portfolio.account(venue) if portfolio else None
        if not account:
            # Try from engine
            if engine and hasattr(engine, 'portfolio'):
                account = engine.portfolio.account(venue)
        
        if not account:
            return StrategyEvaluator._empty_metrics()
        
        base_currency_obj = Currency.from_str(base_currency)
        final_balance = float(account.balance_total(base_currency_obj).as_decimal())
        
        # PRIMARY METHOD: Position Snapshots (CRITICAL for NETTING OMS)
        # This is the recommended approach for NETTING OMS where positions flip rather than fully close
        # Position snapshots preserve realized PnL from all closed cycles
        realized_pnl = 0.0
        unrealized_pnl = 0.0
        
        if engine and hasattr(engine, 'cache'):
            try:
                # Step 1: Aggregate realized PnL from CURRENT positions
                # This captures realized PnL from partial closes and position flips
                current_positions = engine.cache.positions(instrument_id=instrument_id)
                for position in current_positions:
                    if position.realized_pnl:
                        currency = position.realized_pnl.currency
                        # Compare Currency objects properly
                        if currency == base_currency_obj or str(currency) == "USDT":
                            pnl_val = float(position.realized_pnl.as_decimal())
                            realized_pnl += pnl_val
                
                # Step 2: Aggregate realized PnL from HISTORICAL SNAPSHOTS
                # This is CRITICAL for NETTING OMS - captures PnL from closed cycles
                # When a position flips direction, a snapshot is taken preserving realized PnL
                try:
                    # Get all position IDs for this instrument (both open and closed)
                    all_positions = engine.cache.positions(instrument_id=instrument_id)
                    position_ids = [pos.id for pos in all_positions] if all_positions else []
                    
                    # Get snapshots for each position ID
                    # Position snapshots preserve realized PnL from closed cycles
                    for position_id in position_ids:
                        try:
                            snapshots = engine.cache.position_snapshots(position_id=position_id)
                            if snapshots:
                                for snapshot in snapshots:
                                    if snapshot.realized_pnl:
                                        currency = snapshot.realized_pnl.currency if hasattr(snapshot.realized_pnl, 'currency') else base_currency_obj
                                        # Compare Currency objects properly
                                        if currency == base_currency_obj or str(currency) == "USDT":
                                            try:
                                                pnl_val = float(snapshot.realized_pnl.as_double())
                                            except AttributeError:
                                                pnl_val = float(snapshot.realized_pnl.as_decimal())
                                            realized_pnl += pnl_val
                        except Exception:
                            # If position_snapshots() fails for a specific position, continue
                            continue
                except Exception as snapshot_error:
                    # If position_snapshots() fails entirely, try positions_closed() as fallback
                    try:
                        closed_positions = engine.cache.positions_closed(instrument_id=instrument_id)
                        for pos in closed_positions:
                            if pos.realized_pnl:
                                currency = pos.realized_pnl.currency if hasattr(pos.realized_pnl, 'currency') else base_currency_obj
                                # Compare Currency objects properly
                                if currency == base_currency_obj or str(currency) == "USDT":
                                    pnl_val = float(pos.realized_pnl.as_decimal())
                                    realized_pnl += pnl_val
                    except Exception as closed_error:
                        print(f"Warning: Could not get snapshots or closed positions: {snapshot_error}, {closed_error}")
                
                # Step 3: Calculate unrealized PnL from open positions
                open_positions = engine.cache.positions_open(instrument_id=instrument_id)
                
                # Get unrealized PnL from open positions using current price
                # Try to get last price from cache, fallback to avg_px_close
                for pos in open_positions:
                    if pos.quantity and pos.avg_px_open:
                        try:
                            # Try to get current price from cache (most accurate)
                            current_price = None
                            if engine and hasattr(engine, 'cache'):
                                try:
                                    from nautilus_trader.model.enums import PriceType
                                    current_price = engine.cache.price(instrument_id=instrument_id, price_type=PriceType.LAST)
                                except Exception:
                                    pass
                            
                            # Fallback to avg_px_close if cache price not available
                            if current_price is None and pos.avg_px_close:
                                current_price = pos.avg_px_close
                            
                            # Calculate unrealized PnL if we have a current price
                            if current_price:
                                unrealized_money = pos.unrealized_pnl(current_price)
                                if unrealized_money:
                                    unrealized_pnl += float(unrealized_money.as_decimal())
                            else:
                                # Manual calculation as last resort
                                if pos.avg_px_open and pos.avg_px_close:
                                    entry_price = float(pos.avg_px_open.as_decimal())
                                    current_price_val = float(pos.avg_px_close.as_decimal())
                                    quantity = float(pos.quantity.as_decimal())
                                    if pos.side.name == "LONG":
                                        unrealized_pnl += (current_price_val - entry_price) * quantity
                                    else:
                                        unrealized_pnl += (entry_price - current_price_val) * quantity
                        except Exception as e:
                            # Fallback: Manual calculation if method fails
                            try:
                                if pos.avg_px_open and pos.avg_px_close:
                                    entry_price = float(pos.avg_px_open.as_decimal())
                                    current_price_val = float(pos.avg_px_close.as_decimal())
                                    quantity = float(pos.quantity.as_decimal())
                                    if pos.side.name == "LONG":
                                        unrealized_pnl += (current_price_val - entry_price) * quantity
                                    else:
                                        unrealized_pnl += (entry_price - current_price_val) * quantity
                            except Exception as calc_error:
                                print(f"Warning: Could not calculate unrealized PnL for position: {calc_error}")
            except Exception as e:
                print(f"Warning: Could not get PnL from engine cache: {e}")
        
        # FALLBACK METHOD: Use portfolio-level methods if cache method failed
        if (realized_pnl == 0.0 and unrealized_pnl == 0.0) and portfolio:
            try:
                # Try per-instrument methods first (more accurate)
                try:
                    realized_money = portfolio.realized_pnl(instrument_id)
                    if realized_money:
                        realized_pnl = float(realized_money.as_decimal())
                    
                    unrealized_money = portfolio.unrealized_pnl(instrument_id)
                    if unrealized_money:
                        unrealized_pnl = float(unrealized_money.as_decimal())
                except Exception:
                    # Fallback to venue-level aggregation
                    realized_pnls_dict = portfolio.realized_pnls(venue)
                    unrealized_pnls_dict = portfolio.unrealized_pnls(venue)
                    
                    for currency, money in realized_pnls_dict.items():
                        if money and (currency == base_currency or currency == "USDT"):
                            realized_pnl += float(money.as_decimal())
                    
                    for currency, money in unrealized_pnls_dict.items():
                        if money and (currency == base_currency or currency == "USDT"):
                            unrealized_pnl += float(money.as_decimal())
            except Exception as e:
                print(f"Warning: Could not get PnL from portfolio methods: {e}")
        
        # Store unrealized PnL BEFORE closing positions (for display purposes)
        unrealized_pnl_before_closing = unrealized_pnl
        
        # If close_positions=True, realize all unrealized PnL (treat as if positions were closed at end)
        if close_positions and unrealized_pnl != 0.0:
            print(f"  Realizing {unrealized_pnl:.2f} unrealized PnL (positions closed at end of backtest)")
            realized_pnl += unrealized_pnl  # Add unrealized to realized
            unrealized_pnl = 0.0  # Reset unrealized since it's now realized
        
        # Calculate commissions using BEST PRACTICE: position.commissions() method
        # According to NautilusTrader docs: position.commissions() returns list[Money] with aggregated totals per currency
        # This is more reliable than parsing fills report
        commissions = 0.0
        try:
            if engine and hasattr(engine, 'cache'):
                # Method 1: Get commissions from positions (RECOMMENDED by NautilusTrader docs)
                # position.commissions() returns list[Money] with aggregated commission totals per currency
                all_positions = engine.cache.positions(instrument_id=instrument_id)
                for position in all_positions:
                    try:
                        position_commissions = position.commissions()  # Returns list[Money]
                        if position_commissions:
                            for comm_money in position_commissions:
                                if comm_money:
                                    currency = comm_money.currency if hasattr(comm_money, 'currency') else base_currency_obj
                                    if currency == base_currency_obj or str(currency) == "USDT":
                                        commissions += float(comm_money.as_decimal())
                    except Exception as pos_comm_error:
                        # If position.commissions() fails, continue to next position
                        continue
                
                if commissions > 0.0:
                    print(f"Debug: Calculated commissions from positions: {commissions:.2f}")
        except Exception as e:
            print(f"Warning: Could not calculate commissions from positions: {e}")
        
        # Method 2: Fallback to fills report if position.commissions() didn't work
        if commissions == 0.0:
            try:
                if engine and hasattr(engine, 'trader') and engine.trader:
                    fills_report = engine.trader.generate_order_fills_report()
                    if fills_report is not None and not fills_report.empty and 'commissions' in fills_report.columns:
                        instrument_id_str = str(instrument_id)
                        if 'instrument_id' in fills_report.columns:
                            instrument_fills = fills_report[
                                fills_report['instrument_id'].astype(str) == instrument_id_str
                            ]
                        else:
                            instrument_fills = fills_report
                        
                        # Parse commissions column (can be list, Money object, or string)
                        for idx, row in instrument_fills.iterrows():
                            comms = row['commissions']
                            if pd.isna(comms) or comms is None:
                                continue
                            
                            if isinstance(comms, (list, tuple)):
                                for comm in comms:
                                    if comm and hasattr(comm, 'as_decimal'):
                                        currency = comm.currency if hasattr(comm, 'currency') else base_currency_obj
                                        if currency == base_currency_obj or str(currency) == "USDT":
                                            commissions += float(comm.as_decimal())
                            elif hasattr(comms, 'as_decimal'):
                                currency = comms.currency if hasattr(comms, 'currency') else base_currency_obj
                                if currency == base_currency_obj or str(currency) == "USDT":
                                    commissions += float(comms.as_decimal())
                            elif isinstance(comms, str):
                                # Parse string representation
                                numbers = re.findall(r'\d+\.?\d*', comms)
                                base_currency_str = str(base_currency_obj)
                                if numbers and (base_currency_str in comms.upper() or "USDT" in comms.upper()):
                                    commissions += sum(float(n) for n in numbers)
                        
                        if commissions > 0.0:
                            print(f"Debug: Calculated commissions from fills report: {commissions:.2f}")
            except Exception as e:
                print(f"Warning: Could not calculate commissions from fills report: {e}")
        
        # Calculate total PnL from account balance change
        total_pnl = final_balance - starting_balance
        
        # Method 3: Fallback to balance difference calculation (VALIDATION METHOD)
        # According to docs: commissions = (realized + unrealized) - total_pnl
        # This is mathematically correct and serves as validation
        if commissions == 0.0:
            # Total PnL = Realized + Unrealized - Commissions
            # Therefore: Commissions = (Realized + Unrealized) - Total PnL
            calculated_commissions = (realized_pnl + unrealized_pnl) - total_pnl
            # Commissions are always positive (costs), so take absolute value
            commissions = abs(calculated_commissions) if calculated_commissions < 0 else calculated_commissions
            print(f"Debug: Calculated commissions from balance difference (validation fallback): {commissions:.2f}")
        
        # Get position information
        position_info = StrategyEvaluator._get_position_info(
            engine, portfolio, instrument_id, venue
        )
        
        # Calculate position statistics (long/short counts and quantities)
        position_stats = StrategyEvaluator._calculate_position_statistics(
            engine, instrument_id
        )
        
        # Calculate trade statistics
        trade_stats = StrategyEvaluator._calculate_trade_statistics(
            engine, portfolio, instrument_id, venue, starting_balance
        )
        
        # Calculate drawdown
        drawdown_info = StrategyEvaluator._calculate_drawdown(
            engine, portfolio, venue, starting_balance
        )
        
        # Calculate returns
        returns_info = StrategyEvaluator._calculate_returns(
            portfolio, venue, starting_balance, realized_pnl, unrealized_pnl
        )
        
        return {
            "account": {
                "starting_balance": starting_balance,
                "final_balance": final_balance,
                "balance_change": total_pnl,
            },
            "pnl": {
                "total": total_pnl,
                "realized": realized_pnl,
                "unrealized": unrealized_pnl,
                "unrealized_before_closing": unrealized_pnl_before_closing if close_positions else unrealized_pnl,
                "commissions": commissions,
                "net": realized_pnl + unrealized_pnl,
            },
            "returns": returns_info,
            "position": position_info,
            "position_stats": position_stats,
            "trades": trade_stats,
            "drawdown": drawdown_info,
        }
    
    @staticmethod
    def _calculate_position_statistics(engine, instrument_id: InstrumentId) -> Dict[str, Any]:
        """Calculate order statistics: buy/sell order counts and total quantities."""
        try:
            if not engine or not hasattr(engine, 'cache'):
                return {
                    "buy_orders": 0,
                    "buy_quantity": 0.0,
                    "sell_orders": 0,
                    "sell_quantity": 0.0,
                    "market_orders": 0,
                    "limit_orders": 0,
                }
            
            buy_orders = 0
            buy_quantity = 0.0
            sell_orders = 0
            sell_quantity = 0.0
            market_orders = 0
            limit_orders = 0
            
            # Get all orders from cache to analyze order types and quantities
            all_orders = engine.cache.orders()
            orders_by_id = {}
            
            # Build a map of order IDs to order types and quantities
            for order in all_orders:
                try:
                    order_id = str(order.client_order_id)
                    order_side = order.side.name.upper() if hasattr(order.side, 'name') else str(order.side).upper()
                    
                    # Get order quantity
                    order_qty = 0.0
                    if hasattr(order, 'quantity') and order.quantity:
                        order_qty = float(order.quantity.as_decimal())
                    
                    # Try to get order type from order object
                    order_type = None
                    if hasattr(order, 'order_type'):
                        order_type = order.order_type.name if hasattr(order.order_type, 'name') else str(order.order_type)
                    elif hasattr(order, 'type'):
                        order_type = order.type.name if hasattr(order.type, 'name') else str(order.type)
                    
                    # If order type not available, infer from order characteristics
                    if order_type is None:
                        # Limit orders typically have a price, market orders might not
                        if hasattr(order, 'price') and order.price:
                            order_type = 'LIMIT'
                        else:
                            # Default to limit if we can't determine (most orders are limit)
                            order_type = 'LIMIT'
                    
                    orders_by_id[order_id] = {
                        'side': order_side,
                        'type': order_type.upper(),
                        'quantity': order_qty
                    }
                except Exception:
                    continue
            
            # Get all fills to count buy/sell orders and calculate quantities
            fills_report = None
            if hasattr(engine, 'trader') and engine.trader:
                fills_report = engine.trader.generate_order_fills_report()
            
            # Analyze from fills report to count buy/sell orders and sum quantities
            if fills_report is not None and not fills_report.empty:
                instrument_id_str = str(instrument_id)
                if 'instrument_id' in fills_report.columns:
                    instrument_fills = fills_report[
                        fills_report['instrument_id'].astype(str) == instrument_id_str
                    ].copy()
                else:
                    instrument_fills = fills_report.copy()
                
                if len(instrument_fills) > 0:
                    # Track unique orders to avoid double counting
                    processed_orders = set()
                    
                    for idx, row in instrument_fills.iterrows():
                        if 'order_side' in row:
                            order_side = str(row['order_side']).upper()
                            
                            # Get order ID to track order type
                            order_id = None
                            if 'client_order_id' in row:
                                order_id = str(row['client_order_id'])
                            
                            # Get fill quantity
                            fill_qty = 0.0
                            if 'last_qty' in row:
                                try:
                                    fill_qty = float(row['last_qty'])
                                except (ValueError, TypeError):
                                    pass
                            
                            # Count buy/sell orders (count each unique order once) and sum quantities
                            if order_id and order_id not in processed_orders:
                                processed_orders.add(order_id)
                                
                                if order_side == 'BUY':
                                    buy_orders += 1
                                    buy_quantity += fill_qty if fill_qty > 0 else (orders_by_id.get(order_id, {}).get('quantity', 0.0))
                                elif order_side == 'SELL':
                                    sell_orders += 1
                                    sell_quantity += fill_qty if fill_qty > 0 else (orders_by_id.get(order_id, {}).get('quantity', 0.0))
                                
                                # Count market/limit orders
                                if order_id in orders_by_id:
                                    order_info = orders_by_id[order_id]
                                    if order_info['type'] == 'MARKET':
                                        market_orders += 1
                                    elif order_info['type'] == 'LIMIT':
                                        limit_orders += 1
                                else:
                                    # If order not in cache, default to limit (most common)
                                    limit_orders += 1
            
            # Fallback: If no fills report, count from orders cache directly
            if buy_orders == 0 and sell_orders == 0:
                for order_id, order_info in orders_by_id.items():
                    qty = order_info.get('quantity', 0.0)
                    if order_info['side'] == 'BUY':
                        buy_orders += 1
                        buy_quantity += qty
                    elif order_info['side'] == 'SELL':
                        sell_orders += 1
                        sell_quantity += qty
                    
                    if order_info['type'] == 'MARKET':
                        market_orders += 1
                    elif order_info['type'] == 'LIMIT':
                        limit_orders += 1
            
            return {
                "buy_orders": buy_orders,
                "buy_quantity": buy_quantity,
                "sell_orders": sell_orders,
                "sell_quantity": sell_quantity,
                "market_orders": market_orders,
                "limit_orders": limit_orders,
            }
        except Exception as e:
            print(f"Warning: Could not calculate order statistics: {e}")
            import traceback
            traceback.print_exc()
            return {
                "buy_orders": 0,
                "buy_quantity": 0.0,
                "sell_orders": 0,
                "sell_quantity": 0.0,
                "market_orders": 0,
                "limit_orders": 0,
            }
    
    @staticmethod
    def _get_position_info(engine, portfolio, instrument_id: InstrumentId, venue: Venue) -> Dict[str, Any]:
        """Get current position information."""
        try:
            if engine and hasattr(engine, 'cache'):
                open_positions = engine.cache.positions_open(instrument_id=instrument_id)
                if open_positions and len(open_positions) > 0:
                    pos = open_positions[0]  # NETTING OMS has one position
                    unrealized_pnl_val = 0.0
                    try:
                        # Use position's unrealized_pnl method - requires Price object
                        if pos.avg_px_close:
                            current_price = pos.avg_px_close  # Price object
                            unrealized_money = pos.unrealized_pnl(current_price)
                            if unrealized_money:
                                unrealized_pnl_val = float(unrealized_money.as_decimal())
                    except Exception:
                        # Fallback: Calculate manually
                        try:
                            if pos.avg_px_open and pos.avg_px_close and pos.quantity:
                                entry_price = float(pos.avg_px_open.as_decimal())
                                current_price = float(pos.avg_px_close.as_decimal())
                                quantity = float(pos.quantity.as_decimal())
                                if pos.side.name == "LONG":
                                    unrealized_pnl_val = (current_price - entry_price) * quantity
                                else:
                                    unrealized_pnl_val = (entry_price - current_price) * quantity
                        except Exception:
                            pass
                    
                    # Safely convert position attributes to float
                    def safe_float(value, default=0.0):
                        """Safely convert Money/Price/Quantity to float."""
                        if value is None:
                            return default
                        if isinstance(value, (int, float)):
                            return float(value)
                        if hasattr(value, 'as_decimal'):
                            return float(value.as_decimal())
                        return default
                    
                    return {
                        "quantity": safe_float(pos.quantity),
                        "side": pos.side.name if hasattr(pos.side, 'name') else str(pos.side),
                        "entry_price": safe_float(pos.avg_px_open),
                        "current_price": safe_float(pos.avg_px_close),
                        "realized_pnl": safe_float(pos.realized_pnl),
                        "unrealized_pnl": unrealized_pnl_val,
                    }
        except Exception as e:
            # Only log warning if it's not a common expected case (e.g., no position)
            if "position" not in str(e).lower() and "none" not in str(e).lower():
                print(f"Warning: Could not get position info: {e}")
        
        return {
            "quantity": 0.0,
            "side": "FLAT",
            "entry_price": 0.0,
            "current_price": 0.0,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
        }
    
    @staticmethod
    def _calculate_trade_statistics(
        engine,
        portfolio,
        instrument_id: InstrumentId,
        venue: Venue,
        starting_balance: float
    ) -> Dict[str, Any]:
        """Calculate trade statistics from fills."""
        try:
            if not engine or not hasattr(engine, 'trader') or not engine.trader:
                return StrategyEvaluator._empty_trade_stats()
            
            fills_report = engine.trader.generate_order_fills_report()
            if fills_report is None or len(fills_report) == 0:
                return StrategyEvaluator._empty_trade_stats()
            
            # Filter by instrument
            instrument_id_str = str(instrument_id)
            instrument_fills = fills_report[
                fills_report['instrument_id'].astype(str) == instrument_id_str
            ].copy()
            
            if len(instrument_fills) == 0:
                return StrategyEvaluator._empty_trade_stats()
            
            # Sort by timestamp
            if 'ts_init' in instrument_fills.columns:
                instrument_fills = instrument_fills.sort_values('ts_init')
            
            # FAST APPROACH: Count direction changes (position flips) + fills
            # This is faster and more appropriate for trade-driven strategies
            direction_changes = StrategyEvaluator._detect_direction_changes(instrument_fills)
            total_fills = len(instrument_fills)
            
            # Calculate statistics from direction changes (faster than full cycles)
            if direction_changes:
                wins = [c for c in direction_changes if c > 0]
                losses = [c for c in direction_changes if c < 0]
                
                # Total trades = direction changes (position flips)
                # This counts each time position changes direction (long->short or short->long)
                total_trades = len(direction_changes)
                winning_trades = len(wins)
                losing_trades = len(losses)
                
                win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
                avg_win = (sum(wins) / len(wins)) if wins else 0.0
                avg_loss = (sum(losses) / len(losses)) if losses else 0.0
                largest_win = max(wins) if wins else 0.0
                largest_loss = min(losses) if losses else 0.0
                
                # Profit factor
                total_wins = sum(wins) if wins else 0.0
                total_losses = abs(sum(losses)) if losses else 0.0
                profit_factor = (total_wins / total_losses) if total_losses > 0 else (float('inf') if total_wins > 0 else 0.0)
                
                # Expectancy
                expectancy = (total_wins + total_losses) / total_trades if total_trades > 0 else 0.0
                
                # Returns as percentage
                avg_win_pct = (avg_win / starting_balance * 100) if avg_win > 0 else 0.0
                avg_loss_pct = (avg_loss / starting_balance * 100) if avg_loss < 0 else 0.0
                
                return {
                    "total_trades": total_trades,
                    "winning_trades": winning_trades,
                    "losing_trades": losing_trades,
                    "win_rate": win_rate,
                    "avg_win": avg_win,
                    "avg_loss": avg_loss,
                    "avg_win_pct": avg_win_pct,
                    "avg_loss_pct": avg_loss_pct,
                    "largest_win": largest_win,
                    "largest_loss": largest_loss,
                    "profit_factor": profit_factor,
                    "expectancy": expectancy,
                    "total_wins": total_wins,
                    "total_losses": total_losses,
                }
            else:
                # No direction changes detected - count fills as trades (fallback)
                # This ensures we always have trade statistics even if positions don't flip
                total_fills = len(instrument_fills)
                if total_fills > 0:
                    # Calculate PnL per fill for statistics
                    # Use realized PnL from position if available, otherwise estimate
                    try:
                        # Calculate PnL per fill using position snapshots approach
                        # This is more accurate for NETTING OMS
                        fill_pnls = []
                        cumulative_position = 0.0
                        avg_entry_price = 0.0
                        
                        for idx, row in instrument_fills.iterrows():
                            fill_price = float(row['last_px']) if 'last_px' in row else 0.0
                            fill_qty = float(row['last_qty']) if 'last_qty' in row else 0.0
                            order_side = str(row['order_side']).upper() if 'order_side' in row else 'BUY'
                            
                            is_buy = 'BUY' in order_side
                            prev_position = cumulative_position
                            prev_side = 'LONG' if prev_position > 0 else ('SHORT' if prev_position < 0 else None)
                            
                            if is_buy:
                                cumulative_position += fill_qty
                            else:
                                cumulative_position -= fill_qty
                            
                            current_side = 'LONG' if cumulative_position > 0 else ('SHORT' if cumulative_position < 0 else None)
                            
                            # Calculate PnL: only when position changes direction or closes
                            fill_pnl = 0.0
                            if prev_side is not None and current_side is not None:
                                if prev_side != current_side:
                                    # Position flipped - calculate realized PnL
                                    closed_qty = abs(prev_position)
                                    if closed_qty > 0 and avg_entry_price > 0:
                                        if prev_side == 'LONG':
                                            fill_pnl = (fill_price - avg_entry_price) * closed_qty
                                        else:  # prev_side == 'SHORT'
                                            fill_pnl = (avg_entry_price - fill_price) * closed_qty
                                        
                                        # Reset avg_entry_price for new direction
                                        avg_entry_price = fill_price
                                    else:
                                        # Opening new position after flat
                                        avg_entry_price = fill_price
                                elif prev_side == current_side:
                                    # Same direction - update avg entry price, no PnL realized yet
                                    if cumulative_position != 0:
                                        if prev_position == 0:
                                            avg_entry_price = fill_price
                                        else:
                                            total_cost = abs(prev_position) * avg_entry_price + fill_qty * fill_price
                                            avg_entry_price = total_cost / abs(cumulative_position)
                            else:
                                # Opening new position from flat
                                avg_entry_price = fill_price
                            
                            fill_pnls.append(fill_pnl)
                        
                        wins = [p for p in fill_pnls if p > 0]
                        losses = [p for p in fill_pnls if p < 0]
                        
                        winning_trades = len(wins)
                        losing_trades = len(losses)
                        win_rate = (winning_trades / total_fills * 100) if total_fills > 0 else 0.0
                        avg_win = (sum(wins) / len(wins)) if wins else 0.0
                        avg_loss = (sum(losses) / len(losses)) if losses else 0.0
                        largest_win = max(wins) if wins else 0.0
                        largest_loss = min(losses) if losses else 0.0
                        total_wins = sum(wins) if wins else 0.0
                        total_losses = abs(sum(losses)) if losses else 0.0
                        profit_factor = (total_wins / total_losses) if total_losses > 0 else (float('inf') if total_wins > 0 else 0.0)
                        expectancy = (total_wins + total_losses) / total_fills if total_fills > 0 else 0.0
                        avg_win_pct = (avg_win / starting_balance * 100) if avg_win > 0 else 0.0
                        avg_loss_pct = (avg_loss / starting_balance * 100) if avg_loss < 0 else 0.0
                        
                        return {
                            "total_trades": total_fills,
                            "winning_trades": winning_trades,
                            "losing_trades": losing_trades,
                            "win_rate": win_rate,
                            "avg_win": avg_win,
                            "avg_loss": avg_loss,
                            "avg_win_pct": avg_win_pct,
                            "avg_loss_pct": avg_loss_pct,
                            "largest_win": largest_win,
                            "largest_loss": largest_loss,
                            "profit_factor": profit_factor,
                            "expectancy": expectancy,
                            "total_wins": total_wins,
                            "total_losses": total_losses,
                            "note": f"Counted {total_fills} fills as trades (no position direction changes detected)",
                        }
                    except Exception as fill_error:
                        print(f"Warning: Could not calculate fill-based statistics: {fill_error}")
                
                # Fallback: return empty stats
                return {
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "win_rate": 0.0,
                    "avg_win": 0.0,
                    "avg_loss": 0.0,
                    "avg_win_pct": 0.0,
                    "avg_loss_pct": 0.0,
                    "largest_win": 0.0,
                    "largest_loss": 0.0,
                    "profit_factor": 0.0,
                    "expectancy": 0.0,
                    "total_wins": 0.0,
                    "total_losses": 0.0,
                    "note": "No fills or direction changes detected",
                }
        except Exception as e:
            print(f"Warning: Could not calculate trade statistics: {e}")
            import traceback
            traceback.print_exc()
            return StrategyEvaluator._empty_trade_stats()
    
    @staticmethod
    def _detect_direction_changes(fills_df) -> List[float]:
        """
        Detect position direction changes (faster than full cycles).
        
        Returns list of realized PnL for each direction change (position flip).
        This is optimized for trade-driven strategies that may not fully close positions.
        """
        cycles = []
        net_position_qty = 0.0
        avg_entry_price = 0.0
        previous_side = None  # 'LONG', 'SHORT', or None
        
        for idx, row in fills_df.iterrows():
            try:
                fill_price = float(row['last_px']) if 'last_px' in row else None
                fill_qty = float(row['last_qty']) if 'last_qty' in row else None
                fill_side_str = str(row['order_side']) if 'order_side' in row else None
                
                if fill_price is None or fill_qty is None or fill_side_str is None:
                    continue
                
                is_buy = 'BUY' in fill_side_str.upper()
                prev_position_qty = net_position_qty
                current_side = None
                
                # Update position quantity
                if is_buy:
                    net_position_qty += fill_qty
                else:
                    net_position_qty -= fill_qty
                
                # Determine current side
                if net_position_qty > 0:
                    current_side = 'LONG'
                elif net_position_qty < 0:
                    current_side = 'SHORT'
                else:
                    current_side = None
                
                # Detect direction change (position flip)
                if previous_side is not None and current_side is not None:
                    if previous_side != current_side:
                        # Position flipped direction - calculate realized PnL
                        closed_qty = abs(prev_position_qty)
                        if closed_qty > 0 and avg_entry_price > 0:
                            if previous_side == 'LONG':  # Was long, now short
                                cycle_pnl = (fill_price - avg_entry_price) * closed_qty
                            else:  # Was short, now long
                                cycle_pnl = (avg_entry_price - fill_price) * closed_qty
                            cycles.append(cycle_pnl)
                            
                            # Reset average entry price for new direction
                            avg_entry_price = fill_price
                        else:
                            # Opening new position after flat
                            avg_entry_price = fill_price
                    elif previous_side == current_side:
                        # Same direction, increasing position - update average entry price
                        total_cost = (abs(prev_position_qty) * avg_entry_price) + (fill_qty * fill_price)
                        net_position_qty_abs = abs(net_position_qty)
                        if net_position_qty_abs > 0:
                            avg_entry_price = total_cost / net_position_qty_abs
                else:
                    # Opening new position (from flat)
                    avg_entry_price = fill_price
                
                previous_side = current_side
            except Exception as e:
                continue
        
        return cycles
    
    @staticmethod
    def _detect_position_cycles(fills_df) -> List[float]:
        """
        Detect position cycles from fills for NETTING OMS.
        
        Returns list of realized PnL for each closed cycle.
        """
        cycles = []
        net_position_qty = 0.0
        avg_entry_price = 0.0
        
        for idx, row in fills_df.iterrows():
            try:
                fill_price = float(row['last_px']) if 'last_px' in row else None
                fill_qty = float(row['last_qty']) if 'last_qty' in row else None
                fill_side_str = str(row['order_side']) if 'order_side' in row else None
                
                if fill_price is None or fill_qty is None or fill_side_str is None:
                    continue
                
                is_buy = 'BUY' in fill_side_str.upper()
                prev_position_qty = net_position_qty
                
                # Update position quantity
                if is_buy:
                    net_position_qty += fill_qty
                else:
                    net_position_qty -= fill_qty
                
                # Detect closed cycles
                if prev_position_qty != 0:
                    # Position closed or flipped
                    if (prev_position_qty > 0 and net_position_qty <= 0) or \
                       (prev_position_qty < 0 and net_position_qty >= 0) or \
                       (net_position_qty == 0):
                        # Calculate realized PnL for closed portion
                        closed_qty = abs(prev_position_qty)
                        if closed_qty > 0 and avg_entry_price > 0:
                            if prev_position_qty > 0:  # Was long
                                cycle_pnl = (fill_price - avg_entry_price) * closed_qty
                            else:  # Was short
                                cycle_pnl = (avg_entry_price - fill_price) * closed_qty
                            cycles.append(cycle_pnl)
                            
                            # Reset for new position
                            if net_position_qty == 0:
                                avg_entry_price = 0.0
                            else:
                                avg_entry_price = fill_price
                    elif prev_position_qty * net_position_qty > 0:
                        # Same direction, increasing position - update average entry price
                        total_cost = (abs(prev_position_qty) * avg_entry_price) + (fill_qty * fill_price)
                        net_position_qty_abs = abs(net_position_qty)
                        if net_position_qty_abs > 0:
                            avg_entry_price = total_cost / net_position_qty_abs
                else:
                    # Opening new position
                    avg_entry_price = fill_price
            except Exception as e:
                continue
        
        return cycles
    
    @staticmethod
    def _calculate_drawdown(
        engine,
        portfolio,
        venue: Venue,
        starting_balance: float
    ) -> Dict[str, Any]:
        """Calculate maximum drawdown."""
        try:
            if not portfolio:
                return {"max_drawdown": 0.0, "max_drawdown_pct": 0.0}
            
            # Try to get equity curve from portfolio analyzer
            analyzer = portfolio.analyzer
            if hasattr(analyzer, 'get_equity_curve'):
                equity_curve = analyzer.get_equity_curve()
                if equity_curve and len(equity_curve) > 0:
                    peak = starting_balance
                    max_dd = 0.0
                    
                    for value in equity_curve:
                        if value > peak:
                            peak = value
                        drawdown = peak - value
                        if drawdown > max_dd:
                            max_dd = drawdown
                    
                    return {
                        "max_drawdown": max_dd,
                        "max_drawdown_pct": (max_dd / starting_balance * 100) if starting_balance > 0 else 0.0,
                    }
        except Exception as e:
            pass
        
        # Fallback: simple calculation from final balance
        account = portfolio.account(venue) if portfolio else None
        if account:
            base_currency_obj = Currency.from_str("USDT")  # Default to USDT
            final_balance = float(account.balance_total(base_currency_obj).as_decimal())
            if final_balance < starting_balance:
                dd = starting_balance - final_balance
                return {
                    "max_drawdown": dd,
                    "max_drawdown_pct": (dd / starting_balance * 100) if starting_balance > 0 else 0.0,
                }
        
        return {"max_drawdown": 0.0, "max_drawdown_pct": 0.0}
    
    @staticmethod
    def _calculate_returns(
        portfolio,
        venue: Venue,
        starting_balance: float,
        realized_pnl: float,
        unrealized_pnl: float
    ) -> Dict[str, Any]:
        """Calculate return metrics."""
        try:
            analyzer = portfolio.analyzer
            stats_returns = analyzer.get_performance_stats_returns()
            
            total_return = (realized_pnl + unrealized_pnl) / starting_balance * 100 if starting_balance > 0 else 0.0
            realized_return = realized_pnl / starting_balance * 100 if starting_balance > 0 else 0.0
            unrealized_return = unrealized_pnl / starting_balance * 100 if starting_balance > 0 else 0.0
            
            avg_return = float(stats_returns.get('Average (Return)', 0.0)) if stats_returns else 0.0
            avg_win_return = float(stats_returns.get('Average Win (Return)', 0.0)) if stats_returns else 0.0
            avg_loss_return = float(stats_returns.get('Average Loss (Return)', 0.0)) if stats_returns else 0.0
            
            return {
                "total_return_pct": total_return,
                "realized_return_pct": realized_return,
                "unrealized_return_pct": unrealized_return,
                "avg_return": avg_return,
                "avg_win_return": avg_win_return,
                "avg_loss_return": avg_loss_return,
            }
        except Exception as e:
            return {
                "total_return_pct": 0.0,
                "realized_return_pct": 0.0,
                "unrealized_return_pct": 0.0,
                "avg_return": 0.0,
                "avg_win_return": 0.0,
                "avg_loss_return": 0.0,
            }
    
    @staticmethod
    def _empty_metrics() -> Dict[str, Any]:
        """Return empty metrics structure."""
        return {
            "account": {"starting_balance": 0.0, "final_balance": 0.0, "balance_change": 0.0},
            "pnl": {"total": 0.0, "realized": 0.0, "unrealized": 0.0, "commissions": 0.0, "net": 0.0},
            "returns": {},
            "position": {},
            "trades": StrategyEvaluator._empty_trade_stats(),
            "drawdown": {"max_drawdown": 0.0, "max_drawdown_pct": 0.0},
        }
    
    @staticmethod
    def _empty_trade_stats() -> Dict[str, Any]:
        """Return empty trade statistics."""
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "avg_win_pct": 0.0,
            "avg_loss_pct": 0.0,
            "largest_win": 0.0,
            "largest_loss": 0.0,
            "profit_factor": 0.0,
            "expectancy": 0.0,
            "total_wins": 0.0,
            "total_losses": 0.0,
        }

