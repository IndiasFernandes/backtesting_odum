"""Example: Integrating Sports data into Nautilus Trader backtest."""
from pathlib import Path
from nautilus_trader.persistence.catalog import ParquetDataCatalog
from nautilus_trader.config import BacktestDataConfig
from nautilus_trader.model.data import DataType
from nautilus_trader.trading.strategy import Strategy, StrategyConfig

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sports_data_types import SportsEvent, BettingOdds


class SportsStrategyConfig(StrategyConfig):
    """Configuration for Sports strategy."""
    sport: str = "football"
    league: str = "NFL"


class SportsStrategy(Strategy):
    """Example strategy using Sports data."""
    
    def __init__(self, config: SportsStrategyConfig):
        super().__init__(config)
        self._sport = config.sport
        self._league = config.league
        self._events = {}
        self._odds_history = {}
    
    def on_start(self):
        """Called when strategy starts."""
        self.log.info(f"SportsStrategy started for {self._sport} - {self._league}")
        
        # Subscribe to sports events
        self.subscribe_data(
            DataType(SportsEvent, metadata={"sport": self._sport, "league": self._league}),
        )
        
        # Subscribe to betting odds
        self.subscribe_data(
            DataType(BettingOdds, metadata={"market_type": "moneyline"}),
        )
    
    def on_data(self, data):
        """Handle custom data updates."""
        if isinstance(data, SportsEvent):
            if data.sport == self._sport and data.league == self._league:
                self._events[data.event_id] = data
                self.log.info(
                    f"Event: {data.home_team} vs {data.away_team} - "
                    f"Status: {data.status}"
                )
                
                if data.status == "finished":
                    self.log.info(
                        f"Final Score: {data.home_team} {data.home_score} - "
                        f"{data.away_team} {data.away_score}"
                    )
        
        elif isinstance(data, BettingOdds):
            event_id = data.event_id
            
            # Track odds movements
            if event_id not in self._odds_history:
                self._odds_history[event_id] = []
            
            self._odds_history[event_id].append(data)
            
            self.log.info(
                f"Odds update for {event_id}: "
                f"Home: {data.home_odds} ({data.implied_probability_home:.2%}), "
                f"Away: {data.away_odds} ({data.implied_probability_away:.2%})"
            )
            
            # Simple strategy: bet on underdog if odds shift significantly
            if len(self._odds_history[event_id]) > 1:
                prev_odds = self._odds_history[event_id][-2]
                odds_shift = abs(data.home_odds - prev_odds.home_odds)
                
                if odds_shift > 0.2:  # Significant odds movement
                    self.log.info(f"Significant odds shift detected: {odds_shift}")


def example_load_sports_data():
    """Example: Load Sports data into catalog."""
    # Initialize catalog
    catalog_path = Path("./data/parquet")
    catalog_path.mkdir(parents=True, exist_ok=True)
    catalog = ParquetDataCatalog(str(catalog_path))
    
    # Load sports events from Parquet file
    import pyarrow.parquet as pq
    
    sports_file = Path(__file__).parent / "sports_sample.parquet"
    if sports_file.exists():
        table = pq.read_table(sports_file)
        data_objects = SportsEvent.from_catalog(table)
        
        # Write to catalog
        catalog.write_data(data_objects)
        print(f"Loaded {len(data_objects)} sports events to catalog")
    
    # Load betting odds
    odds_file = Path(__file__).parent / "sports_betting_odds_sample.parquet"
    if odds_file.exists():
        table = pq.read_table(odds_file)
        data_objects = BettingOdds.from_catalog(table)
        
        catalog.write_data(data_objects)
        print(f"Loaded {len(data_objects)} betting odds records to catalog")
    
    return catalog


def example_query_sports_data(catalog: ParquetDataCatalog):
    """Example: Query Sports data from catalog."""
    # Query sports events
    events = catalog.query(
        data_cls=SportsEvent,
        start="2024-01-01",
        end="2024-12-31",
        where="sport == 'football' AND league == 'NFL'",
    )
    
    print(f"Queried {len(events)} sports events")
    
    # Query betting odds
    odds = catalog.query(
        data_cls=BettingOdds,
        start="2024-01-01",
        end="2024-12-31",
        where="market_type == 'moneyline'",
    )
    
    print(f"Queried {len(odds)} betting odds records")


if __name__ == "__main__":
    print("Sports Integration Example")
    print("=" * 50)
    
    # Load data
    catalog = example_load_sports_data()
    
    # Query data
    example_query_sports_data(catalog)
    
    print("\n✅ Sports integration example complete!")
    print("\nTo use in a backtest:")
    print("1. Generate sample data: python sports_data_generator.py")
    print("2. Load data into catalog (see example_load_sports_data)")
    print("3. Configure BacktestDataConfig with Sports data types")
    print("4. Use SportsStrategy in your backtest")

