"""Result extraction utilities for backtest analysis."""
from typing import Dict, Any, List, Optional

from nautilus_trader.model.identifiers import InstrumentId, Venue
from nautilus_trader.model.objects import Currency

from backend.strategies.evaluator import StrategyEvaluator


class ResultExtractor:
    """Extracts results and performance metrics from backtest engine."""
    
    @staticmethod
    def extract_basic_counts(engine) -> Dict[str, int]:
        """
        Extract basic order and fill counts from engine.
        
        Uses NautilusTrader's fills report for accurate fill counting.
        
        Args:
            engine: BacktestEngine instance
        
        Returns:
            Dictionary with 'orders' and 'fills' counts
        """
        orders_count = 0
        fills_count = 0
        
        if engine and hasattr(engine, 'cache'):
            # Get all orders from engine cache
            orders = engine.cache.orders()
            orders_count = len(orders) if orders else 0
            
            # Use fills report for accurate fill counting (more reliable than checking filled_qty)
            try:
                if hasattr(engine, 'trader'):
                    fills_report = engine.trader.generate_order_fills_report()
                    if fills_report is not None and len(fills_report) > 0:
                        # Count unique orders that have fills
                        fills_count = len(fills_report)
                    else:
                        # Fallback: check orders with filled_qty > 0
                        fills = [
                            o for o in orders
                            if hasattr(o, 'filled_qty') and o.filled_qty
                            and float(o.filled_qty.as_decimal()) > 0
                        ] if orders else []
                        fills_count = len(fills) if fills else 0
                else:
                    # Fallback: check orders with filled_qty > 0
                    fills = [
                        o for o in orders
                        if hasattr(o, 'filled_qty') and o.filled_qty
                        and float(o.filled_qty.as_decimal()) > 0
                    ] if orders else []
                    fills_count = len(fills) if fills else 0
            except Exception as e:
                # Fallback: check orders with filled_qty > 0
                import sys
                print(f"Warning: Could not generate fills report, using fallback method: {e}", file=sys.stderr)
                fills = [
                    o for o in orders
                    if hasattr(o, 'filled_qty') and o.filled_qty
                    and float(o.filled_qty.as_decimal()) > 0
                ] if orders else []
                fills_count = len(fills) if fills else 0
        
        return {
            'orders': orders_count,
            'fills': fills_count
        }
    
    @staticmethod
    def extract_pnl_from_engine(
        engine,
        config: Dict[str, Any],
        venue_config_name: str
    ) -> float:
        """
        Extract PnL from engine's portfolio analyzer.
        
        Args:
            engine: BacktestEngine instance
            config: Configuration dictionary
            venue_config_name: Venue configuration name
        
        Returns:
            Total PnL value
        """
        pnl = 0.0
        
        try:
            if hasattr(engine, 'portfolio') and engine.portfolio:
                analyzer = engine.portfolio.analyzer
                stats_pnls = analyzer.get_performance_stats_pnls()
                
                base_currency_str = config["venue"]["base_currency"]
                
                # Direct lookup for 'PnL (total)' key
                if 'PnL (total)' in stats_pnls:
                    pnl_value = stats_pnls['PnL (total)']
                    if pnl_value is not None:
                        pnl = float(pnl_value)
                else:
                    # Fallback: search for any key with "total" and "pnl"
                    for key, value in stats_pnls.items():
                        if "total" in key.lower() and "pnl" in key.lower():
                            if isinstance(value, dict):
                                # Value is a dict with currency keys
                                for currency, pnl_val in value.items():
                                    if currency == base_currency_str or currency == "USDT":
                                        if pnl_val is not None:
                                            pnl += float(pnl_val)
                            elif value is not None:
                                # Value is a direct number
                                pnl += float(value)
                                break
                
                # Fallback: try account balance change if still 0
                if pnl == 0.0:
                    venue = Venue(venue_config_name)
                    account = engine.portfolio.account(venue)
                    if account:
                        base_currency_str = config["venue"]["base_currency"]
                        base_currency_obj = Currency.from_str(base_currency_str)
                        final_balance = float(account.balance_total(base_currency_obj).as_decimal())
                        starting_balance = config["venue"]["starting_balance"]
                        pnl = final_balance - starting_balance
        except Exception as e:
            print(f"Warning: Could not get PnL from engine portfolio analyzer: {e}")
            import traceback
            traceback.print_exc()
            pnl = 0.0
        
        return pnl
    
    @staticmethod
    def extract_pnl_from_portfolio(
        portfolio,
        config: Dict[str, Any],
        venue_config_name: str
    ) -> float:
        """
        Extract PnL from portfolio analyzer (fallback method).
        
        Args:
            portfolio: Portfolio instance
            config: Configuration dictionary
            venue_config_name: Venue configuration name
        
        Returns:
            Total PnL value
        """
        pnl = 0.0
        
        try:
            analyzer = portfolio.analyzer
            stats_pnls = analyzer.get_performance_stats_pnls()
            base_currency_str = config["venue"]["base_currency"]
            
            # Try to find total PnL in stats
            for key, value in stats_pnls.items():
                if "total" in key.lower() or "pnl" in key.lower():
                    if value is not None:
                        if isinstance(value, dict):
                            for currency, pnl_val in value.items():
                                if currency == base_currency_str or currency == "USDT":
                                    pnl += float(pnl_val) if pnl_val is not None else 0.0
                        else:
                            pnl += float(value) if value is not None else 0.0
            
            # If no total found, sum all PnL values
            if pnl == 0.0:
                for key, value in stats_pnls.items():
                    if isinstance(value, dict):
                        for currency, pnl_val in value.items():
                            if pnl_val is not None:
                                pnl += float(pnl_val)
                    elif value is not None:
                        pnl += float(value)
            
            # Fallback: calculate from realized + unrealized PnL
            if pnl == 0.0:
                venue = Venue(venue_config_name)
                realized_pnls = portfolio.realized_pnls(venue)
                unrealized_pnls = portfolio.unrealized_pnls(venue)
                
                for currency, money in realized_pnls.items():
                    if money:
                        pnl += float(money.as_decimal())
                
                for currency, money in unrealized_pnls.items():
                    if money:
                        pnl += float(money.as_decimal())
            
            # Final fallback: try account balance difference
            if pnl == 0.0:
                try:
                    venue = Venue(venue_config_name)
                    account = portfolio.account(venue)
                    if account:
                        base_currency_str = config["venue"]["base_currency"]
                        base_currency_obj = Currency.from_str(base_currency_str)
                        final_balance = float(account.balance_total(base_currency_obj).as_decimal())
                        starting_balance = config["venue"]["starting_balance"]
                        pnl = final_balance - starting_balance
                except Exception:
                    pass
        except Exception as e:
            print(f"Warning: Could not calculate PnL from portfolio analyzer: {e}")
            import traceback
            traceback.print_exc()
            pnl = 0.0
        
        return pnl
    
    @staticmethod
    def extract_returns_from_positions(
        engine,
        config: Dict[str, Any],
        fills: Optional[List] = None
    ) -> Dict[str, float]:
        """
        Extract average return and average loss from positions.
        
        Args:
            engine: BacktestEngine instance
            config: Configuration dictionary
            fills: Optional list of filled orders
        
        Returns:
            Dictionary with 'avg_return' and 'avg_loss' values
        """
        avg_return = 0.0
        avg_loss = 0.0
        
        try:
            instrument_id = InstrumentId.from_str(config["instrument"]["id"])
            realized_pnls = []
            
            # Method 1: Try trader's positions report
            try:
                if hasattr(engine, 'trader') and engine.trader:
                    positions_report = engine.trader.generate_positions_report()
                    if positions_report is not None and len(positions_report) > 0:
                        instrument_id_str = str(instrument_id)
                        for row in positions_report.itertuples():
                            row_instrument_id = str(row.instrument_id) if hasattr(row, 'instrument_id') else None
                            if row_instrument_id == instrument_id_str:
                                if hasattr(row, 'realized_pnl') and row.realized_pnl:
                                    try:
                                        pnl_val = float(row.realized_pnl)
                                        realized_pnls.append(pnl_val)
                                    except (ValueError, TypeError):
                                        pass
            except Exception:
                pass
            
            # Method 2: Get all positions (open + closed) for realized_pnl
            if not realized_pnls:
                try:
                    if hasattr(engine, 'cache'):
                        closed_positions = engine.cache.positions_closed(instrument_id=instrument_id)
                        if closed_positions and len(closed_positions) > 0:
                            for pos in closed_positions:
                                if pos.realized_pnl:
                                    pnl_val = float(pos.realized_pnl.as_decimal())
                                    realized_pnls.append(pnl_val)
                        
                        open_positions = engine.cache.positions_open(instrument_id=instrument_id)
                        if open_positions and len(open_positions) > 0:
                            for pos in open_positions:
                                if pos.realized_pnl:
                                    pnl_val = float(pos.realized_pnl.as_decimal())
                                    realized_pnls.append(pnl_val)
                except Exception:
                    pass
            
            # Method 3: Calculate from fills report (has execution prices)
            if fills and not realized_pnls:
                try:
                    if hasattr(engine, 'trader') and engine.trader:
                        fills_report = engine.trader.generate_order_fills_report()
                        
                        if fills_report is not None and len(fills_report) > 0:
                            instrument_id_str = str(instrument_id)
                            instrument_fills = fills_report[
                                fills_report['instrument_id'].astype(str) == instrument_id_str
                            ].copy()
                            
                            if 'ts_event' in instrument_fills.columns:
                                instrument_fills = instrument_fills.sort_values('ts_event')
                            
                            # Track position cycles from fills report
                            net_position_qty = 0.0
                            avg_entry_price = 0.0
                            position_cycles = []
                            
                            for idx, row in instrument_fills.iterrows():
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
                                        if (prev_position_qty > 0 and net_position_qty <= 0) or \
                                           (prev_position_qty < 0 and net_position_qty >= 0) or \
                                           (net_position_qty == 0):
                                            # Position closed or flipped
                                            closed_qty = abs(prev_position_qty)
                                            if closed_qty > 0 and avg_entry_price > 0:
                                                if prev_position_qty > 0:  # Was long
                                                    cycle_pnl = (fill_price - avg_entry_price) * closed_qty
                                                else:  # Was short
                                                    cycle_pnl = (avg_entry_price - fill_price) * closed_qty
                                                position_cycles.append(cycle_pnl)
                                                
                                                # Reset for new position
                                                if net_position_qty == 0:
                                                    avg_entry_price = 0.0
                                                else:
                                                    avg_entry_price = fill_price
                                        elif prev_position_qty * net_position_qty > 0:
                                            # Same direction, update average entry price
                                            total_cost = (abs(prev_position_qty) * avg_entry_price) + (fill_qty * fill_price)
                                            net_position_qty_abs = abs(net_position_qty)
                                            if net_position_qty_abs > 0:
                                                avg_entry_price = total_cost / net_position_qty_abs
                                    else:
                                        # Opening new position
                                        avg_entry_price = fill_price
                                except Exception:
                                    continue
                            
                            # Add cycles to realized_pnls (avoid duplicates)
                            for cycle_pnl in position_cycles:
                                if not any(abs(existing - cycle_pnl) < 0.01 for existing in realized_pnls):
                                    realized_pnls.append(cycle_pnl)
                except Exception:
                    pass
            
            # Calculate avg_return and avg_loss from realized PnLs
            if realized_pnls:
                wins = [p for p in realized_pnls if p > 0]
                losses = [p for p in realized_pnls if p < 0]
                
                starting_balance = config["venue"]["starting_balance"]
                if wins:
                    avg_return = (sum(wins) / len(wins)) / starting_balance
                if losses:
                    avg_loss = (sum(losses) / len(losses)) / starting_balance
        except Exception:
            pass
        
        return {
            'avg_return': avg_return,
            'avg_loss': avg_loss
        }
    
    @staticmethod
    def extract_returns_from_stats(
        engine,
        config: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Extract average return and loss from engine statistics (fallback).
        
        Args:
            engine: BacktestEngine instance
            config: Configuration dictionary
        
        Returns:
            Dictionary with 'avg_return' and 'avg_loss' values
        """
        avg_return = 0.0
        avg_loss = 0.0
        
        try:
            if hasattr(engine, 'portfolio') and engine.portfolio:
                analyzer = engine.portfolio.analyzer
                stats_returns = analyzer.get_performance_stats_returns()
                
                if stats_returns:
                    # Average Win (Return)
                    if 'Average Win (Return)' in stats_returns:
                        avg_win_val = stats_returns['Average Win (Return)']
                        if avg_win_val is not None and not (isinstance(avg_win_val, float) and (avg_win_val != avg_win_val)):
                            avg_return = float(avg_win_val)
                    
                    # Average Loss (Return)
                    if 'Average Loss (Return)' in stats_returns:
                        avg_loss_val = stats_returns['Average Loss (Return)']
                        if avg_loss_val is not None and not (isinstance(avg_loss_val, float) and (avg_loss_val != avg_loss_val)):
                            avg_loss = float(avg_loss_val)
                    
                    # Fallback: use overall average if no wins/losses separated
                    if avg_return == 0.0 and 'Average (Return)' in stats_returns:
                        avg_return_val = stats_returns['Average (Return)']
                        if avg_return_val is not None and not (isinstance(avg_return_val, float) and (avg_return_val != avg_return_val)):
                            avg_return = float(avg_return_val)
        except Exception:
            pass
        
        return {
            'avg_return': avg_return,
            'avg_loss': avg_loss
        }
    
    @staticmethod
    def extract_summary(
        engine,
        backtest_result,
        config: Dict[str, Any],
        venue_config_name: str,
        close_positions: bool = True
    ) -> Dict[str, Any]:
        """
        Extract comprehensive summary from backtest results.
        
        Args:
            engine: BacktestEngine instance
            backtest_result: BacktestResult instance
            config: Configuration dictionary
            venue_config_name: Venue configuration name
            close_positions: Whether positions were closed
        
        Returns:
            Summary dictionary with orders, fills, pnl, returns, etc.
        """
        # Extract basic counts
        counts = ResultExtractor.extract_basic_counts(engine)
        orders_count = counts['orders']
        fills_count = counts['fills']
        
        # Extract PnL
        pnl = ResultExtractor.extract_pnl_from_engine(engine, config, venue_config_name)
        
        # Fallback to portfolio if engine PnL is 0
        if pnl == 0.0:
            portfolio = backtest_result.get_portfolio() if hasattr(backtest_result, 'get_portfolio') else None
            if portfolio:
                pnl = ResultExtractor.extract_pnl_from_portfolio(portfolio, config, venue_config_name)
        
        # Extract returns
        fills = None
        if engine and hasattr(engine, 'cache'):
            orders = engine.cache.orders()
            # Use fills report for accurate fill extraction (more reliable)
            try:
                if hasattr(engine, 'trader'):
                    fills_report = engine.trader.generate_order_fills_report()
                    if fills_report is not None and len(fills_report) > 0:
                        # Convert fills report to list of orders with fills
                        fills = [
                            o for o in orders
                            if o.client_order_id.value in fills_report['client_order_id'].astype(str).values
                        ] if orders else []
                    else:
                        # Fallback: check orders with filled_qty > 0
                        fills = [
                            o for o in orders
                            if hasattr(o, 'filled_qty') and o.filled_qty
                            and float(o.filled_qty.as_decimal()) > 0
                        ] if orders else []
                else:
                    # Fallback: check orders with filled_qty > 0
                    fills = [
                        o for o in orders
                        if hasattr(o, 'filled_qty') and o.filled_qty
                        and float(o.filled_qty.as_decimal()) > 0
                    ] if orders else []
            except Exception as e:
                # Fallback: check orders with filled_qty > 0
                import sys
                print(f"Warning: Could not generate fills report for summary, using fallback: {e}", file=sys.stderr)
                fills = [
                    o for o in orders
                    if hasattr(o, 'filled_qty') and o.filled_qty
                    and float(o.filled_qty.as_decimal()) > 0
                ] if orders else []
        
        returns = ResultExtractor.extract_returns_from_positions(engine, config, fills)
        
        # Fallback to stats if position-based returns are 0
        if returns['avg_return'] == 0.0 and returns['avg_loss'] == 0.0:
            returns = ResultExtractor.extract_returns_from_stats(engine, config)
        
        # Use StrategyEvaluator for comprehensive performance analysis
        try:
            portfolio = backtest_result.get_portfolio() if hasattr(backtest_result, 'get_portfolio') else None
            performance = StrategyEvaluator.evaluate_performance(
                engine=engine,
                portfolio=portfolio,
                config=config,
                venue_config_name=venue_config_name,
                close_positions=close_positions
            )
            
            # Build comprehensive summary
            summary = {
                "orders": orders_count,
                "fills": fills_count,
                "pnl": performance["pnl"]["total"],
                "pnl_breakdown": {
                    "realized": performance["pnl"]["realized"],
                    "unrealized": performance["pnl"]["unrealized"],
                    "unrealized_before_closing": performance["pnl"].get("unrealized_before_closing", performance["pnl"]["unrealized"]),
                    "commissions": performance["pnl"]["commissions"],
                    "net": performance["pnl"]["net"],
                },
                "account": performance["account"],
                "returns": performance["returns"],
                "position": performance["position"],
                "position_stats": performance.get("position_stats", {}),
                "trades": performance["trades"],
                "drawdown": performance["drawdown"],
                # Legacy fields for backward compatibility
                "avg_return": performance["returns"].get("avg_return", returns['avg_return']),
                "avg_loss": performance["trades"].get("avg_loss_pct", returns['avg_loss']),
                "max_drawdown": performance["drawdown"]["max_drawdown"],
            }
        except Exception as e:
            print(f"Warning: Could not evaluate performance: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to basic summary
            summary = {
                "orders": orders_count,
                "fills": fills_count,
                "pnl": pnl,
                "avg_return": returns['avg_return'],
                "avg_loss": returns['avg_loss'],
                "max_drawdown": 0.0,
            }
        
        return summary

