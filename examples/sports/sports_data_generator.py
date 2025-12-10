"""Generate sample Sports data for Nautilus Trader."""
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import pyarrow.parquet as pq
import uuid

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sports_data_types import SportsEvent, BettingOdds


def generate_sample_sports_events(
    start_date: datetime,
    end_date: datetime,
    sport: str = "football",
    league: str = "NFL",
    output_path: Path = Path("sports_sample.parquet")
) -> None:
    """
    Generate sample sports event data.
    
    Args:
        start_date: Start date for data generation
        end_date: End date for data generation
        sport: Sport type
        league: League name
        output_path: Output Parquet file path
    """
    events = []
    current_date = start_date
    
    # Sample teams
    teams = [
        ("Patriots", "Bills"),
        ("Chiefs", "Broncos"),
        ("Packers", "Vikings"),
        ("Cowboys", "Giants"),
        ("49ers", "Rams"),
    ]
    
    team_idx = 0
    
    # Generate events every 3 days
    while current_date < end_date:
        home_team, away_team = teams[team_idx % len(teams)]
        event_id = f"{sport}_{league}_{current_date.strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"
        
        # Event scheduled for evening (7 PM)
        event_datetime = current_date.replace(hour=19, minute=0, second=0)
        event_date_ns = int(event_datetime.timestamp() * 1_000_000_000)
        
        # Status depends on whether event has happened
        if current_date < datetime.now():
            status = "finished"
            # Generate final scores
            home_score = np.random.randint(10, 35)
            away_score = np.random.randint(10, 35)
        elif current_date.date() == datetime.now().date():
            status = "live"
            # Generate current scores
            home_score = np.random.randint(0, 21)
            away_score = np.random.randint(0, 21)
        else:
            status = "scheduled"
            home_score = None
            away_score = None
        
        ts_event_ns = int(current_date.timestamp() * 1_000_000_000)
        ts_init_ns = ts_event_ns
        
        event = SportsEvent(
            ts_event=ts_event_ns,
            ts_init=ts_init_ns,
            event_id=event_id,
            sport=sport,
            league=league,
            home_team=home_team,
            away_team=away_team,
            home_score=home_score,
            away_score=away_score,
            status=status,
            venue=f"{home_team} Stadium",
            event_date=event_date_ns,
        )
        events.append(event)
        
        current_date += timedelta(days=3)
        team_idx += 1
    
    if events:
        table = SportsEvent.to_catalog(events)
        pq.write_table(table, output_path, compression='zstd')
        
        print(f"Generated {len(events)} sports events")
        print(f"Saved to: {output_path}")
        print(f"Sport: {sport}, League: {league}")


def generate_sample_betting_odds(
    event_ids: list[str],
    output_path: Path = Path("sports_betting_odds_sample.parquet")
) -> None:
    """
    Generate sample betting odds data.
    
    Args:
        event_ids: List of event IDs to generate odds for
        output_path: Output Parquet file path
    """
    odds_list = []
    bookmakers = ["DraftKings", "FanDuel", "BetMGM", "Caesars", "Bet365"]
    
    for event_id in event_ids:
        # Generate odds at different times (opening, mid, closing)
        for hour_offset in [0, 12, 24]:
            ts_event_ns = int((datetime.now() - timedelta(hours=hour_offset)).timestamp() * 1_000_000_000)
            ts_init_ns = ts_event_ns
            
            for bookmaker in bookmakers:
                # Generate moneyline odds
                home_odds = np.random.uniform(1.5, 3.5)
                away_odds = np.random.uniform(1.5, 3.5)
                draw_odds = np.random.uniform(2.5, 4.0)
                
                # Calculate implied probabilities
                total_prob = (1/home_odds) + (1/away_odds) + (1/draw_odds)
                implied_prob_home = (1/home_odds) / total_prob
                implied_prob_away = (1/away_odds) / total_prob
                implied_prob_draw = (1/draw_odds) / total_prob
                
                odds = BettingOdds(
                    ts_event=ts_event_ns,
                    ts_init=ts_init_ns,
                    event_id=event_id,
                    market_type="moneyline",
                    bookmaker=bookmaker,
                    home_odds=round(home_odds, 2),
                    away_odds=round(away_odds, 2),
                    draw_odds=round(draw_odds, 2),
                    implied_probability_home=round(implied_prob_home, 4),
                    implied_probability_away=round(implied_prob_away, 4),
                    implied_probability_draw=round(implied_prob_draw, 4),
                )
                odds_list.append(odds)
    
    if odds_list:
        table = BettingOdds.to_catalog(odds_list)
        pq.write_table(table, output_path, compression='zstd')
        
        print(f"Generated {len(odds_list)} betting odds records")
        print(f"Saved to: {output_path}")


if __name__ == "__main__":
    # Generate sample data for the past 30 days
    end_date = datetime.now() + timedelta(days=7)  # Include future events
    start_date = end_date - timedelta(days=30)
    
    output_dir = Path(__file__).parent
    output_dir.mkdir(exist_ok=True)
    
    # Generate sports events
    generate_sample_sports_events(
        start_date=start_date,
        end_date=end_date,
        sport="football",
        league="NFL",
        output_path=output_dir / "sports_sample.parquet"
    )
    
    # Generate betting odds for those events
    # Read event IDs from the generated file
    import pandas as pd
    df = pd.read_parquet(output_dir / "sports_sample.parquet")
    event_ids = df["event_id"].unique().tolist()
    
    generate_sample_betting_odds(
        event_ids=event_ids,
        output_path=output_dir / "sports_betting_odds_sample.parquet"
    )
    
    print("\n✅ Sports sample data generation complete!")

