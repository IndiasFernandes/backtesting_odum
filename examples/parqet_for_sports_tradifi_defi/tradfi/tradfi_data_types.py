"""TradFi (Traditional Finance) custom data types for Nautilus Trader."""
from dataclasses import dataclass
from typing import Optional
import pyarrow as pa
from nautilus_trader.model.data import Data
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.persistence.catalog import register_arrow


@dataclass
class TradFiOHLCV(Data):
    """Traditional Finance OHLCV bar data."""
    ts_event: int
    ts_init: int
    instrument_id: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    bar_type: str  # "1min", "5min", "1hour", "1day"
    exchange: str  # "NYSE", "NASDAQ", "LSE", etc.
    
    @staticmethod
    def schema() -> pa.Schema:
        """Define Arrow schema for Parquet storage."""
        return pa.schema([
            pa.field("ts_event", pa.int64()),
            pa.field("ts_init", pa.int64()),
            pa.field("instrument_id", pa.string()),
            pa.field("open", pa.float64()),
            pa.field("high", pa.float64()),
            pa.field("low", pa.float64()),
            pa.field("close", pa.float64()),
            pa.field("volume", pa.float64()),
            pa.field("bar_type", pa.string()),
            pa.field("exchange", pa.string()),
        ])
    
    @staticmethod
    def to_catalog(data: list["TradFiOHLCV"]) -> pa.Table:
        """Convert data objects to Arrow table."""
        return pa.Table.from_pylist([
            {
                "ts_event": d.ts_event,
                "ts_init": d.ts_init,
                "instrument_id": d.instrument_id,
                "open": d.open,
                "high": d.high,
                "low": d.low,
                "close": d.close,
                "volume": d.volume,
                "bar_type": d.bar_type,
                "exchange": d.exchange,
            }
            for d in data
        ], schema=TradFiOHLCV.schema())
    
    @staticmethod
    def from_catalog(table: pa.Table) -> list["TradFiOHLCV"]:
        """Convert Arrow table to data objects."""
        return [
            TradFiOHLCV(
                ts_event=row["ts_event"],
                ts_init=row["ts_init"],
                instrument_id=row["instrument_id"],
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["volume"],
                bar_type=row["bar_type"],
                exchange=row["exchange"],
            )
            for row in table.to_pylist()
        ]


@dataclass
class TradFiCorporateAction(Data):
    """Corporate action data (dividends, splits, etc.)."""
    ts_event: int
    ts_init: int
    instrument_id: str
    action_type: str  # "dividend", "split", "merger", etc.
    value: float
    ex_date: int  # Ex-dividend/split date in nanoseconds
    record_date: Optional[int]  # Record date in nanoseconds
    payment_date: Optional[int]  # Payment date in nanoseconds
    
    @staticmethod
    def schema() -> pa.Schema:
        """Define Arrow schema for Parquet storage."""
        return pa.schema([
            pa.field("ts_event", pa.int64()),
            pa.field("ts_init", pa.int64()),
            pa.field("instrument_id", pa.string()),
            pa.field("action_type", pa.string()),
            pa.field("value", pa.float64()),
            pa.field("ex_date", pa.int64()),
            pa.field("record_date", pa.int64()),
            pa.field("payment_date", pa.int64()),
        ])
    
    @staticmethod
    def to_catalog(data: list["TradFiCorporateAction"]) -> pa.Table:
        """Convert data objects to Arrow table."""
        return pa.Table.from_pylist([
            {
                "ts_event": d.ts_event,
                "ts_init": d.ts_init,
                "instrument_id": d.instrument_id,
                "action_type": d.action_type,
                "value": d.value,
                "ex_date": d.ex_date,
                "record_date": d.record_date if d.record_date else 0,
                "payment_date": d.payment_date if d.payment_date else 0,
            }
            for d in data
        ], schema=TradFiCorporateAction.schema())
    
    @staticmethod
    def from_catalog(table: pa.Table) -> list["TradFiCorporateAction"]:
        """Convert Arrow table to data objects."""
        return [
            TradFiCorporateAction(
                ts_event=row["ts_event"],
                ts_init=row["ts_init"],
                instrument_id=row["instrument_id"],
                action_type=row["action_type"],
                value=row["value"],
                ex_date=row["ex_date"],
                record_date=row["record_date"] if row["record_date"] > 0 else None,
                payment_date=row["payment_date"] if row["payment_date"] > 0 else None,
            )
            for row in table.to_pylist()
        ]


# Register both data types with catalog
register_arrow(TradFiOHLCV, TradFiOHLCV.schema(), TradFiOHLCV.to_catalog, TradFiOHLCV.from_catalog)
register_arrow(TradFiCorporateAction, TradFiCorporateAction.schema(), TradFiCorporateAction.to_catalog, TradFiCorporateAction.from_catalog)

