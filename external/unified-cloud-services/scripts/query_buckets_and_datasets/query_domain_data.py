#!/usr/bin/env python3
"""
Query Domain Data - High-Level Wrapper

Provides high-level wrappers for querying domain data across all services.
Useful for:
- Analytics platforms that need to access multiple domains
- Cross-service quality gates
- Ad-hoc data exploration

All queries use unified-cloud-services domain clients under the hood.

CLI Usage:
-----------
# Query all instruments for a date (CSV output)
python query_domain_data.py instruments --date 2024-01-01 --output ./instruments

# Query instruments for a specific venue (parquet output)
python query_domain_data.py instruments --date 2024-01-01 --venue UPBIT --format parquet --output ./upbit

# Query a specific instrument definition by ID
python query_domain_data.py instruments --date 2024-01-01 --instrument-id "UPBIT:SPOT_PAIR:BTC-KRW" --output ./btc_krw

# Query candles for an instrument
python query_domain_data.py candles --date 2024-01-01 --instrument-id "BINANCE-FUTURES:PERPETUAL:BTC-USDT" --timeframe 15s

# Query tick data for an instrument
python query_domain_data.py tick_data --date 2024-01-01 --instrument-id "COINBASE:SPOT_PAIR:SOL-USD" --data-type trades

# Query features for an instrument
python query_domain_data.py features --date 2024-01-01 --instrument-id "BINANCE-FUTURES:PERPETUAL:ETH-USDT" --feature-type delta_one

Output Formats:
---------------
--format csv      : Export as CSV (default)
--format parquet  : Export as Parquet (better compression for large datasets)

Supported Domains:
------------------
- instruments : Instrument definitions (venues, symbols, metadata)
- candles     : Aggregated OHLCV candles at various timeframes
- tick_data   : Raw tick-level trade/orderbook data
- features    : Derived features (delta_one, volatility, onchain, calendar)
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import pandas as pd

# Add unified-cloud-services to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "unified-cloud-services"))

from unified_cloud_services import (
    create_instruments_client,
    create_market_candle_data_client,
    create_market_tick_data_client,
    create_features_client,
)


def query_instruments(
    date: str,
    venue: Optional[str] = None,
    instrument_type: Optional[str] = None,
    base_currency: Optional[str] = None,
    quote_currency: Optional[str] = None,
    symbol_pattern: Optional[str] = None,
    instrument_ids: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Query instruments domain data.

    Args:
        date: Date to query (YYYY-MM-DD)
        venue: Optional venue filter
        instrument_type: Optional instrument type filter
        base_currency: Optional base currency filter
        quote_currency: Optional quote currency filter
        symbol_pattern: Optional symbol pattern (regex)
        instrument_ids: Optional list of specific instrument IDs

    Returns:
        DataFrame with instrument definitions
    """
    client = create_instruments_client()
    return client.get_instruments_for_date(
        date=date,
        venue=venue,
        instrument_type=instrument_type,
        base_currency=base_currency,
        quote_currency=quote_currency,
        symbol_pattern=symbol_pattern,
        instrument_ids=instrument_ids,
    )


def query_instrument_by_id(
    date: str,
    instrument_id: str,
) -> pd.DataFrame:
    """
    Query a specific instrument definition by its ID.

    Args:
        date: Date to query (YYYY-MM-DD)
        instrument_id: Full instrument ID (e.g., 'UPBIT:SPOT_PAIR:BTC-KRW')

    Returns:
        DataFrame with the instrument definition (single row if found)
    """
    client = create_instruments_client()
    return client.get_instruments_for_date(
        date=date,
        instrument_ids=[instrument_id],
    )


def query_candles(
    date: str,
    instrument_id: str,
    timeframe: str = "15s",
    data_type: str = "trades",
    venue: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Query market data domain candles.

    Args:
        date: Date to query (YYYY-MM-DD) - used if start_date/end_date not provided
        instrument_id: Instrument ID (e.g., 'BINANCE-FUTURES:PERPETUAL:BTC-USDT')
        timeframe: Candle timeframe (e.g., '15s', '1m', '5m', '1h')
        data_type: Data type (e.g., 'trades', 'book_snapshot_5')
        venue: Optional venue filter
        start_date: Optional start date (YYYY-MM-DD) for range query
        end_date: Optional end date (YYYY-MM-DD) for range query

    Returns:
        DataFrame with candles
    """
    client = create_market_candle_data_client()

    if start_date and end_date:
        # Range query
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        return client.get_candles_range(
            start_date=start_dt,
            end_date=end_dt,
            instrument_id=instrument_id,
            timeframe=timeframe,
            data_type=data_type,
            venue=venue,
        )
    else:
        # Single date query
        date_dt = datetime.strptime(date, "%Y-%m-%d")
        return client.get_candles(
            date=date_dt,
            instrument_id=instrument_id,
            timeframe=timeframe,
            data_type=data_type,
            venue=venue,
        )


def query_tick_data(
    date: str,
    instrument_id: str,
    data_type: str = "trades",
    hour: Optional[int] = None,
    venue: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Query market data domain raw tick data.

    Args:
        date: Date to query (YYYY-MM-DD) - used if start_date/end_date not provided
        instrument_id: Instrument ID (e.g., 'BINANCE-FUTURES:PERPETUAL:BTC-USDT')
        data_type: Data type (e.g., 'trades', 'book_snapshot_5', 'liquidations')
        hour: Optional hour filter (0-23)
        venue: Optional venue filter
        start_date: Optional start date (YYYY-MM-DD) for range query
        end_date: Optional end date (YYYY-MM-DD) for range query

    Returns:
        DataFrame with tick data
    """
    client = create_market_tick_data_client()

    if start_date and end_date:
        # Range query
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        return client.get_tick_data_range(
            start_date=start_dt,
            end_date=end_dt,
            instrument_id=instrument_id,
            data_type=data_type,
            venue=venue,
        )
    else:
        # Single date query
        date_dt = datetime.strptime(date, "%Y-%m-%d")
        return client.get_tick_data(
            date=date_dt,
            instrument_id=instrument_id,
            data_type=data_type,
            hour=hour,
            venue=venue,
        )


def query_features(
    date: str,
    instrument_id: str,
    feature_type: str = "delta_one",
    feature_set: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Query features domain data.

    Args:
        date: Date to query (YYYY-MM-DD) - used if start_date/end_date not provided
        instrument_id: Instrument ID
        feature_type: Feature type ('delta_one', 'volatility', 'onchain', 'calendar')
        feature_set: Optional feature set filter
        start_date: Optional start date (YYYY-MM-DD) for range query
        end_date: Optional end date (YYYY-MM-DD) for range query

    Returns:
        DataFrame with features
    """
    client = create_features_client(feature_type=feature_type)

    if start_date and end_date:
        # Range query - iterate over dates
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        all_features = []
        current_date = start_dt
        while current_date <= end_dt:
            features = client.get_features(
                date=current_date, instrument_id=instrument_id, feature_set=feature_set
            )
            if not features.empty:
                all_features.append(features)
            current_date += timedelta(days=1)

        if all_features:
            return pd.concat(all_features, ignore_index=True)
        else:
            return pd.DataFrame()
    else:
        # Single date query
        date_dt = datetime.strptime(date, "%Y-%m-%d")
        return client.get_features(
            date=date_dt, instrument_id=instrument_id, feature_set=feature_set
        )


def main():
    """Example usage of query functions."""
    import argparse

    parser = argparse.ArgumentParser(description="Query domain data")
    parser.add_argument(
        "domain",
        choices=["instruments", "candles", "tick_data", "features"],
        help="Domain to query",
    )
    parser.add_argument("--date", required=True, help="Date to query (YYYY-MM-DD)")
    parser.add_argument("--instrument-id", help="Instrument ID")
    parser.add_argument("--timeframe", default="15s", help="Candle timeframe (for candles)")
    parser.add_argument("--data-type", default="trades", help="Data type (for candles/tick_data)")
    parser.add_argument("--feature-type", default="delta_one", help="Feature type (for features)")
    parser.add_argument("--hour", type=int, help="Hour filter (0-23, for tick_data)")
    parser.add_argument("--venue", help="Venue filter (for instruments)")
    parser.add_argument("--instrument-type", help="Instrument type filter (for instruments, e.g., SPOT_PAIR, PERPETUAL)")
    parser.add_argument("--base-currency", help="Base currency filter (for instruments, e.g., BTC, ETH)")
    parser.add_argument("--quote-currency", help="Quote currency filter (for instruments, e.g., USD, KRW, USDT)")
    parser.add_argument("--output", help="Output file path (extension ignored, uses --format)")
    parser.add_argument(
        "--format",
        choices=["csv", "parquet"],
        default="csv",
        help="Output format: csv or parquet (default: csv)",
    )

    args = parser.parse_args()

    try:
        if args.domain == "instruments":
            if args.instrument_id:
                # Query specific instrument by ID
                df = query_instrument_by_id(date=args.date, instrument_id=args.instrument_id)
            else:
                # Query all instruments with optional filters
                df = query_instruments(
                    date=args.date,
                    venue=args.venue,
                    instrument_type=getattr(args, 'instrument_type', None),
                    base_currency=getattr(args, 'base_currency', None),
                    quote_currency=getattr(args, 'quote_currency', None),
                )
        elif args.domain == "candles":
            if not args.instrument_id:
                print("❌ Error: --instrument-id required for candles query")
                return
            df = query_candles(
                date=args.date,
                instrument_id=args.instrument_id,
                timeframe=args.timeframe,
                data_type=args.data_type,
                venue=args.venue,
            )
        elif args.domain == "tick_data":
            if not args.instrument_id:
                print("❌ Error: --instrument-id required for tick_data query")
                return
            df = query_tick_data(
                date=args.date,
                instrument_id=args.instrument_id,
                data_type=args.data_type,
                hour=args.hour,
                venue=args.venue,
            )
        elif args.domain == "features":
            if not args.instrument_id:
                print("❌ Error: --instrument-id required for features query")
                return
            df = query_features(
                date=args.date,
                instrument_id=args.instrument_id,
                feature_type=args.feature_type,
            )

        if df.empty:
            print(f"⚠️ No data found for {args.domain} on {args.date}")
        else:
            print(f"✅ Found {len(df)} rows")
            if args.output:
                # Ensure correct file extension based on format
                output_path = Path(args.output)
                if args.format == "parquet":
                    output_path = output_path.with_suffix(".parquet")
                    df.to_parquet(output_path, index=False)
                else:
                    output_path = output_path.with_suffix(".csv")
                    df.to_csv(output_path, index=False)
                print(f"💾 Saved {args.format.upper()} to {output_path}")
            else:
                print(df.head())

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
