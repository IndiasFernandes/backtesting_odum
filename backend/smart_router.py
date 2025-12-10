"""
Smart Order Router for multi-venue order routing.

Routes orders to optimal venues based on fees, liquidity, latency, and historical performance.
"""
from typing import List, Dict, Optional
from decimal import Decimal
from nautilus_trader.model.identifiers import InstrumentId, Venue
from nautilus_trader.model.objects import Quantity, Price
from nautilus_trader.model.enums import OrderSide


class SmartOrderRouter:
    """
    Smart Order Router that selects optimal venue for each order.
    
    Routes orders based on:
    - Fee costs (maker/taker fees)
    - Historical fill rates
    - Liquidity depth
    - Latency
    - Price improvement opportunities
    """
    
    def __init__(self, venues: List[Dict]):
        """
        Initialize router with venue configurations.
        
        Args:
            venues: List of venue configs with fees, latency, etc.
                    Example: [
                        {
                            "name": "BINANCE-FUTURES",
                            "maker_fee": 0.0002,
                            "taker_fee": 0.0004,
                            "latency_ms": 50,
                            "min_order_size": 0.001,
                            "max_order_size": 1000.0
                        },
                        ...
                    ]
        """
        self.venues = venues
        self.venue_stats = {}  # Track fill rates, latency, etc.
        self._initialize_stats()
    
    def _initialize_stats(self):
        """Initialize statistics for each venue."""
        for venue_config in self.venues:
            venue_name = venue_config["name"]
            self.venue_stats[venue_name] = {
                "fill_rate": 0.95,  # Default fill rate (will be updated from history)
                "avg_latency_ms": venue_config.get("latency_ms", 100),
                "total_orders": 0,
                "filled_orders": 0,
                "total_volume": Decimal("0"),
            }
    
    def select_venue(
        self,
        instrument_id: InstrumentId,
        side: OrderSide,
        quantity: Quantity,
        price: Optional[Price] = None
    ) -> Venue:
        """
        Select best venue for order execution.
        
        Args:
            instrument_id: Instrument to trade
            side: Buy or sell
            quantity: Order quantity
            price: Optional limit price
            
        Returns:
            Best venue for this order
        """
        best_venue = None
        best_score = -float('inf')
        
        for venue_config in self.venues:
            venue_name = venue_config["name"]
            
            # Check if venue supports this order size
            min_size = venue_config.get("min_order_size", 0.0)
            max_size = venue_config.get("max_order_size", float('inf'))
            qty_decimal = float(quantity.as_decimal())
            
            if qty_decimal < min_size or qty_decimal > max_size:
                continue  # Skip venues that don't support this order size
            
            # Calculate venue score
            score = self._calculate_venue_score(
                venue_name=venue_name,
                instrument_id=instrument_id,
                side=side,
                quantity=quantity,
                price=price,
                venue_config=venue_config
            )
            
            if score > best_score:
                best_score = score
                best_venue = Venue(venue_name)
        
        if best_venue is None:
            # Fallback: use first venue
            best_venue = Venue(self.venues[0]["name"])
        
        return best_venue
    
    def _calculate_venue_score(
        self,
        venue_name: str,
        instrument_id: InstrumentId,
        side: OrderSide,
        quantity: Quantity,
        price: Optional[Price],
        venue_config: Dict
    ) -> float:
        """
        Calculate score for venue (higher = better).
        
        Scoring factors:
        - Fee cost (lower fees = higher score)
        - Historical fill rate (higher fill rate = higher score)
        - Latency (lower latency = higher score)
        - Price improvement (if limit order)
        
        Returns:
            Score (higher is better)
        """
        score = 0.0
        
        # 1. Fee cost (lower fees = higher score)
        maker_fee = venue_config.get("maker_fee", 0.0)
        taker_fee = venue_config.get("taker_fee", 0.0)
        avg_fee = (maker_fee + taker_fee) / 2
        score -= avg_fee * 10000  # Penalize fees (scale for visibility)
        
        # 2. Historical fill rate (if available)
        if venue_name in self.venue_stats:
            fill_rate = self.venue_stats[venue_name]["fill_rate"]
            score += fill_rate * 1000  # Reward high fill rates
        
        # 3. Latency (lower latency = higher score)
        latency_ms = venue_config.get("latency_ms", 100)
        score -= latency_ms * 0.1  # Penalize latency
        
        # 4. Price improvement (for limit orders)
        # This would require order book data
        # For now, we assume all venues have similar prices
        
        return score
    
    def route_order(
        self,
        instrument_id: InstrumentId,
        side: OrderSide,
        total_quantity: Quantity,
        price: Optional[Price] = None,
        max_venues: int = 3
    ) -> List[Dict]:
        """
        Route large order across multiple venues.
        
        Splits order across top venues based on scores.
        
        Args:
            instrument_id: Instrument to trade
            side: Buy or sell
            total_quantity: Total order size
            price: Optional limit price
            max_venues: Maximum venues to use
            
        Returns:
            List of venue/quantity allocations
            Example: [
                {
                    "venue": Venue("BINANCE-FUTURES"),
                    "quantity": Quantity.from_str("0.5"),
                    "price": Price.from_str("50000.0")
                },
                ...
            ]
        """
        allocations = []
        remaining = total_quantity
        
        # Sort venues by score
        venue_scores = []
        for venue_config in self.venues:
            # Check if venue supports order size
            min_size = venue_config.get("min_order_size", 0.0)
            max_size = venue_config.get("max_order_size", float('inf'))
            qty_decimal = float(total_quantity.as_decimal())
            
            if qty_decimal < min_size or qty_decimal > max_size:
                continue
            
            score = self._calculate_venue_score(
                venue_name=venue_config["name"],
                instrument_id=instrument_id,
                side=side,
                quantity=total_quantity,
                price=price,
                venue_config=venue_config
            )
            venue_scores.append((venue_config, score))
        
        if not venue_scores:
            # No venues support this order size - use first venue
            allocations.append({
                "venue": Venue(self.venues[0]["name"]),
                "quantity": total_quantity,
                "price": price,
            })
            return allocations
        
        venue_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Allocate quantity across top venues
        top_venues = venue_scores[:max_venues]
        total_score = sum(score for _, score in top_venues)
        
        for i, (venue_config, score) in enumerate(top_venues):
            if remaining <= 0:
                break
            
            # Allocate proportional to score
            if i == len(top_venues) - 1:
                # Last venue gets remainder
                allocation = remaining
            else:
                # Allocate proportional to score
                allocation_pct = score / total_score if total_score > 0 else 1.0 / len(top_venues)
                allocation = total_quantity * Decimal(str(allocation_pct))
            
            # Ensure allocation doesn't exceed remaining
            allocation = min(allocation, remaining)
            
            allocations.append({
                "venue": Venue(venue_config["name"]),
                "quantity": allocation,
                "price": price,
            })
            
            remaining -= allocation
        
        return allocations
    
    def update_stats(
        self,
        venue_name: str,
        order_filled: bool,
        quantity: Optional[Quantity] = None
    ):
        """
        Update venue statistics after order execution.
        
        Args:
            venue_name: Venue name
            order_filled: Whether order was filled
            quantity: Order quantity (optional)
        """
        if venue_name not in self.venue_stats:
            return
        
        stats = self.venue_stats[venue_name]
        stats["total_orders"] += 1
        
        if order_filled:
            stats["filled_orders"] += 1
            if quantity:
                stats["total_volume"] += quantity.as_decimal()
        
        # Update fill rate
        if stats["total_orders"] > 0:
            stats["fill_rate"] = stats["filled_orders"] / stats["total_orders"]
    
    def get_best_venue_for_instrument(
        self,
        instrument_id: InstrumentId
    ) -> Optional[Venue]:
        """
        Get best venue for instrument based on historical performance.
        
        Args:
            instrument_id: Instrument ID
            
        Returns:
            Best venue or None
        """
        best_venue = None
        best_fill_rate = 0.0
        
        for venue_config in self.venues:
            venue_name = venue_config["name"]
            if venue_name in self.venue_stats:
                fill_rate = self.venue_stats[venue_name]["fill_rate"]
                if fill_rate > best_fill_rate:
                    best_fill_rate = fill_rate
                    best_venue = Venue(venue_name)
        
        return best_venue

