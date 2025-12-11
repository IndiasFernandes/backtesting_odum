"""Timeline builder for backtest results."""
from datetime import datetime, timezone
from typing import Dict, Any, List


class TimelineBuilder:
    """Builds chronological timeline of backtest events."""
    
    @staticmethod
    def ns_to_datetime(ns: int) -> datetime:
        """Convert nanoseconds timestamp to datetime."""
        return datetime.fromtimestamp(ns / 1_000_000_000, tz=timezone.utc)
    
    @staticmethod
    def build_timeline(engine) -> List[Dict[str, Any]]:
        """
        Build chronological timeline from engine events.
        
        Args:
            engine: BacktestEngine instance from node
        
        Returns:
            List of timeline events (sorted chronologically)
        """
        timeline = []
        orders_by_id = {}
        
        # Get orders from cache
        all_orders = engine.cache.orders() if hasattr(engine, 'cache') else []
        
        if not all_orders:
            print("Warning: No orders found in cache for timeline")
            return timeline
        
        # First pass: collect all orders
        for order in all_orders:
            try:
                order_id = str(order.client_order_id)
                order_dict = {
                    "id": order_id,
                    "side": order.side.name.lower() if hasattr(order.side, 'name') else str(order.side),
                    "price": float(order.price) if hasattr(order, 'price') and order.price else 0.0,
                    "amount": float(order.quantity) if hasattr(order, 'quantity') and order.quantity else 0.0,
                    "status": order.status.name.lower() if hasattr(order.status, 'name') else str(order.status),
                }
                orders_by_id[order_id] = order_dict
                
                # Add order event to timeline
                order_ts_ns = None
                if hasattr(order, 'ts_init') and order.ts_init:
                    order_ts_ns = order.ts_init
                elif hasattr(order, 'ts_event') and order.ts_event:
                    order_ts_ns = order.ts_event
                elif hasattr(order, 'ts_accepted') and order.ts_accepted:
                    order_ts_ns = order.ts_accepted
                
                if order_ts_ns:
                    try:
                        order_ts = TimelineBuilder.ns_to_datetime(order_ts_ns)
                        timeline.append({
                            "ts": order_ts.isoformat().replace('+00:00', 'Z'),
                            "event": "Order",
                            "data": order_dict
                        })
                    except Exception:
                        pass
            except Exception as e:
                print(f"Warning: Could not serialize order {order.client_order_id}: {e}")
                continue
        
        # Second pass: Add fill and rejection events from strategy
        fill_count = 0
        rejection_count = 0
        
        try:
            strategy_fills = []
            strategy_rejections = []
            
            # Access strategy from engine
            if hasattr(engine, 'trader') and engine.trader:
                strategies = []
                if hasattr(engine.trader, 'strategies'):
                    try:
                        strategies = engine.trader.strategies()
                    except Exception:
                        pass
                elif hasattr(engine.trader, 'cache') and hasattr(engine.trader.cache, 'strategies'):
                    try:
                        strategies = engine.trader.cache.strategies()
                    except Exception:
                        pass
                
                # Also try accessing via engine cache
                if not strategies and hasattr(engine, 'cache'):
                    try:
                        if hasattr(engine.cache, 'strategies'):
                            strategies = engine.cache.strategies()
                    except Exception:
                        pass
                
                # Extract fill and rejection events from strategies
                for strategy in strategies:
                    try:
                        if hasattr(strategy, 'get_fill_events'):
                            fills = strategy.get_fill_events()
                            if fills:
                                strategy_fills.extend(fills)
                        if hasattr(strategy, 'get_rejection_events'):
                            rejections = strategy.get_rejection_events()
                            if rejections:
                                strategy_rejections.extend(rejections)
                    except Exception:
                        continue
            
            # Add fill events from strategy
            fill_events_by_order_id = {}
            for fill_event in strategy_fills:
                try:
                    order_id = fill_event.get('order_id')
                    fill_ts_ns = fill_event.get('ts_event') or fill_event.get('ts_init')
                    
                    if order_id and fill_ts_ns:
                        fill_ts = TimelineBuilder.ns_to_datetime(fill_ts_ns)
                        fill_data = {
                            "order_id": order_id,
                            "price": fill_event.get('price', 0.0),
                            "quantity": fill_event.get('quantity', 0.0),
                            "side": fill_event.get('side', 'unknown'),
                        }
                        
                        fill_events_by_order_id[order_id] = {
                            "ts": fill_ts.isoformat().replace('+00:00', 'Z'),
                            "event": "Fill",
                            "data": fill_data
                        }
                except Exception:
                    continue
            
            # Add fill events to timeline
            for fill_event_entry in fill_events_by_order_id.values():
                timeline.append(fill_event_entry)
            fill_count = len(fill_events_by_order_id)
            
            # Add rejection events to timeline
            for rejection_event in strategy_rejections:
                try:
                    order_id = rejection_event.get('order_id')
                    rejection_ts_ns = rejection_event.get('ts_event') or rejection_event.get('ts_init')
                    
                    if order_id and rejection_ts_ns:
                        rejection_ts = TimelineBuilder.ns_to_datetime(rejection_ts_ns)
                        
                        # Find corresponding order to get full details
                        order_details = orders_by_id.get(order_id, {})
                        
                        rejection_data = {
                            "order_id": order_id,
                            "reason": rejection_event.get('reason', 'Unknown'),
                            "side": order_details.get('side', 'unknown'),
                            "price": order_details.get('price', 0.0),
                            "amount": order_details.get('amount', 0.0),
                        }
                        
                        timeline.append({
                            "ts": rejection_ts.isoformat().replace('+00:00', 'Z'),
                            "event": "OrderRejected",
                            "data": rejection_data
                        })
                        rejection_count += 1
                except Exception:
                    continue
            
            print(f"Debug: Added {fill_count} fill events and {rejection_count} rejection events from strategy")
        
        except Exception as e:
            print(f"Warning: Could not get fill/rejection events from strategy: {e}")
            # Fallback: Add fill events based on order status
            fill_count = TimelineBuilder._add_fills_from_orders(timeline, all_orders, orders_by_id)
        
        # Sort timeline by timestamp
        if timeline:
            timeline.sort(key=lambda x: x["ts"])
        
        print(f"Debug: Built timeline with {len(timeline)} events")
        return timeline
    
    @staticmethod
    def _add_fills_from_orders(
        timeline: List[Dict[str, Any]],
        all_orders: List,
        orders_by_id: Dict[str, Dict[str, Any]]
    ) -> int:
        """
        Fallback method to add fills based on order status.
        
        Args:
            timeline: Timeline list to append to
            all_orders: List of order objects
            orders_by_id: Dictionary mapping order IDs to order dicts
        
        Returns:
            Number of fills added
        """
        fill_count = 0
        
        for order in all_orders:
            try:
                order_id = str(order.client_order_id)
                if order_id not in orders_by_id:
                    continue
                
                # Check if order was filled
                is_filled = False
                filled_qty = 0.0
                fill_price = orders_by_id[order_id]['price']
                
                if hasattr(order, 'filled_qty') and order.filled_qty:
                    filled_qty = float(order.filled_qty.as_decimal())
                    if filled_qty > 0:
                        is_filled = True
                
                # Also check status
                if hasattr(order, 'status'):
                    status_str = order.status.name.lower() if hasattr(order.status, 'name') else str(order.status)
                    if 'filled' in status_str or 'partially_filled' in status_str:
                        is_filled = True
                
                if is_filled:
                    # Use order timestamp for fill
                    fill_ts_ns = None
                    if hasattr(order, 'ts_event') and order.ts_event:
                        fill_ts_ns = order.ts_event
                    elif hasattr(order, 'ts_last') and order.ts_last:
                        fill_ts_ns = order.ts_last
                    elif hasattr(order, 'ts_init') and order.ts_init:
                        fill_ts_ns = order.ts_init
                    
                    if fill_ts_ns:
                        try:
                            fill_ts = TimelineBuilder.ns_to_datetime(fill_ts_ns)
                            fill_data = {
                                "order_id": order_id,
                                "price": fill_price,
                                "quantity": filled_qty if filled_qty > 0 else orders_by_id[order_id]['amount'],
                            }
                            
                            timeline.append({
                                "ts": fill_ts.isoformat().replace('+00:00', 'Z'),
                                "event": "Fill",
                                "data": fill_data
                            })
                            fill_count += 1
                        except Exception:
                            pass
            except Exception:
                continue
        
        print(f"Debug: Added {fill_count} fill events to timeline (fallback method)")
        return fill_count

