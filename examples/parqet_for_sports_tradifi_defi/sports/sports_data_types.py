"""Sports custom data types for Nautilus Trader."""
from dataclasses import dataclass
from typing import Optional
import pyarrow as pa
from nautilus_trader.model.data import Data
from nautilus_trader.persistence.catalog import register_arrow


@dataclass
class SportsEvent(Data):
    """Sports event data."""
    ts_event: int
    ts_init: int
    event_id: str
    sport: str  # "football", "basketball", "soccer", etc.
    league: str
    home_team: str
    away_team: str
    home_score: Optional[int]
    away_score: Optional[int]
    status: str  # "scheduled", "live", "finished"
    venue: str
    event_date: int  # Event start date in nanoseconds
    
    @staticmethod
    def schema() -> pa.Schema:
        """Define Arrow schema for Parquet storage."""
        return pa.schema([
            pa.field("ts_event", pa.int64()),
            pa.field("ts_init", pa.int64()),
            pa.field("event_id", pa.string()),
            pa.field("sport", pa.string()),
            pa.field("league", pa.string()),
            pa.field("home_team", pa.string()),
            pa.field("away_team", pa.string()),
            pa.field("home_score", pa.int64()),
            pa.field("away_score", pa.int64()),
            pa.field("status", pa.string()),
            pa.field("venue", pa.string()),
            pa.field("event_date", pa.int64()),
        ])
    
    @staticmethod
    def to_catalog(data: list["SportsEvent"]) -> pa.Table:
        """Convert data objects to Arrow table."""
        return pa.Table.from_pylist([
            {
                "ts_event": d.ts_event,
                "ts_init": d.ts_init,
                "event_id": d.event_id,
                "sport": d.sport,
                "league": d.league,
                "home_team": d.home_team,
                "away_team": d.away_team,
                "home_score": d.home_score if d.home_score is not None else 0,
                "away_score": d.away_score if d.away_score is not None else 0,
                "status": d.status,
                "venue": d.venue,
                "event_date": d.event_date,
            }
            for d in data
        ], schema=SportsEvent.schema())
    
    @staticmethod
    def from_catalog(table: pa.Table) -> list["SportsEvent"]:
        """Convert Arrow table to data objects."""
        return [
            SportsEvent(
                ts_event=row["ts_event"],
                ts_init=row["ts_init"],
                event_id=row["event_id"],
                sport=row["sport"],
                league=row["league"],
                home_team=row["home_team"],
                away_team=row["away_team"],
                home_score=row["home_score"] if row["home_score"] > 0 else None,
                away_score=row["away_score"] if row["away_score"] > 0 else None,
                status=row["status"],
                venue=row["venue"],
                event_date=row["event_date"],
            )
            for row in table.to_pylist()
        ]


@dataclass
class BettingOdds(Data):
    """Betting odds data."""
    ts_event: int
    ts_init: int
    event_id: str
    market_type: str  # "moneyline", "spread", "total"
    bookmaker: str
    home_odds: float
    away_odds: float
    draw_odds: Optional[float]
    implied_probability_home: float
    implied_probability_away: float
    implied_probability_draw: Optional[float]
    
    @staticmethod
    def schema() -> pa.Schema:
        """Define Arrow schema for Parquet storage."""
        return pa.schema([
            pa.field("ts_event", pa.int64()),
            pa.field("ts_init", pa.int64()),
            pa.field("event_id", pa.string()),
            pa.field("market_type", pa.string()),
            pa.field("bookmaker", pa.string()),
            pa.field("home_odds", pa.float64()),
            pa.field("away_odds", pa.float64()),
            pa.field("draw_odds", pa.float64()),
            pa.field("implied_probability_home", pa.float64()),
            pa.field("implied_probability_away", pa.float64()),
            pa.field("implied_probability_draw", pa.float64()),
        ])
    
    @staticmethod
    def to_catalog(data: list["BettingOdds"]) -> pa.Table:
        """Convert data objects to Arrow table."""
        return pa.Table.from_pylist([
            {
                "ts_event": d.ts_event,
                "ts_init": d.ts_init,
                "event_id": d.event_id,
                "market_type": d.market_type,
                "bookmaker": d.bookmaker,
                "home_odds": d.home_odds,
                "away_odds": d.away_odds,
                "draw_odds": d.draw_odds if d.draw_odds is not None else 0.0,
                "implied_probability_home": d.implied_probability_home,
                "implied_probability_away": d.implied_probability_away,
                "implied_probability_draw": d.implied_probability_draw if d.implied_probability_draw is not None else 0.0,
            }
            for d in data
        ], schema=BettingOdds.schema())
    
    @staticmethod
    def from_catalog(table: pa.Table) -> list["BettingOdds"]:
        """Convert Arrow table to data objects."""
        return [
            BettingOdds(
                ts_event=row["ts_event"],
                ts_init=row["ts_init"],
                event_id=row["event_id"],
                market_type=row["market_type"],
                bookmaker=row["bookmaker"],
                home_odds=row["home_odds"],
                away_odds=row["away_odds"],
                draw_odds=row["draw_odds"] if row["draw_odds"] > 0 else None,
                implied_probability_home=row["implied_probability_home"],
                implied_probability_away=row["implied_probability_away"],
                implied_probability_draw=row["implied_probability_draw"] if row["implied_probability_draw"] > 0 else None,
            )
            for row in table.to_pylist()
        ]


# Register both data types with catalog
register_arrow(SportsEvent, SportsEvent.schema(), SportsEvent.to_catalog, SportsEvent.from_catalog)
register_arrow(BettingOdds, BettingOdds.schema(), BettingOdds.to_catalog, BettingOdds.from_catalog)

