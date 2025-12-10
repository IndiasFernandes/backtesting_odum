"""DeFi (Decentralized Finance) custom data types for Nautilus Trader."""
from dataclasses import dataclass
from typing import Optional
import pyarrow as pa
from nautilus_trader.model.data import Data
from nautilus_trader.persistence.catalog import register_arrow


@dataclass
class DeFiSwap(Data):
    """DeFi DEX swap transaction."""
    ts_event: int
    ts_init: int
    transaction_hash: str
    block_number: int
    dex: str  # "uniswap", "sushiswap", "pancakeswap"
    pool_address: str
    token_in: str
    token_out: str
    amount_in: float
    amount_out: float
    price_impact: float
    fee: float
    trader: str
    
    @staticmethod
    def schema() -> pa.Schema:
        """Define Arrow schema for Parquet storage."""
        return pa.schema([
            pa.field("ts_event", pa.int64()),
            pa.field("ts_init", pa.int64()),
            pa.field("transaction_hash", pa.string()),
            pa.field("block_number", pa.int64()),
            pa.field("dex", pa.string()),
            pa.field("pool_address", pa.string()),
            pa.field("token_in", pa.string()),
            pa.field("token_out", pa.string()),
            pa.field("amount_in", pa.float64()),
            pa.field("amount_out", pa.float64()),
            pa.field("price_impact", pa.float64()),
            pa.field("fee", pa.float64()),
            pa.field("trader", pa.string()),
        ])
    
    @staticmethod
    def to_catalog(data: list["DeFiSwap"]) -> pa.Table:
        """Convert data objects to Arrow table."""
        return pa.Table.from_pylist([
            {
                "ts_event": d.ts_event,
                "ts_init": d.ts_init,
                "transaction_hash": d.transaction_hash,
                "block_number": d.block_number,
                "dex": d.dex,
                "pool_address": d.pool_address,
                "token_in": d.token_in,
                "token_out": d.token_out,
                "amount_in": d.amount_in,
                "amount_out": d.amount_out,
                "price_impact": d.price_impact,
                "fee": d.fee,
                "trader": d.trader,
            }
            for d in data
        ], schema=DeFiSwap.schema())
    
    @staticmethod
    def from_catalog(table: pa.Table) -> list["DeFiSwap"]:
        """Convert Arrow table to data objects."""
        return [
            DeFiSwap(
                ts_event=row["ts_event"],
                ts_init=row["ts_init"],
                transaction_hash=row["transaction_hash"],
                block_number=row["block_number"],
                dex=row["dex"],
                pool_address=row["pool_address"],
                token_in=row["token_in"],
                token_out=row["token_out"],
                amount_in=row["amount_in"],
                amount_out=row["amount_out"],
                price_impact=row["price_impact"],
                fee=row["fee"],
                trader=row["trader"],
            )
            for row in table.to_pylist()
        ]


@dataclass
class LiquidityPool(Data):
    """Liquidity pool state snapshot."""
    ts_event: int
    ts_init: int
    pool_address: str
    dex: str
    token0: str
    token1: str
    reserve0: float
    reserve1: float
    total_liquidity: float
    price: float  # token1/token0
    fee_tier: float  # e.g., 0.003 for 0.3%
    tvl: float  # Total Value Locked in USD
    
    @staticmethod
    def schema() -> pa.Schema:
        """Define Arrow schema for Parquet storage."""
        return pa.schema([
            pa.field("ts_event", pa.int64()),
            pa.field("ts_init", pa.int64()),
            pa.field("pool_address", pa.string()),
            pa.field("dex", pa.string()),
            pa.field("token0", pa.string()),
            pa.field("token1", pa.string()),
            pa.field("reserve0", pa.float64()),
            pa.field("reserve1", pa.float64()),
            pa.field("total_liquidity", pa.float64()),
            pa.field("price", pa.float64()),
            pa.field("fee_tier", pa.float64()),
            pa.field("tvl", pa.float64()),
        ])
    
    @staticmethod
    def to_catalog(data: list["LiquidityPool"]) -> pa.Table:
        """Convert data objects to Arrow table."""
        return pa.Table.from_pylist([
            {
                "ts_event": d.ts_event,
                "ts_init": d.ts_init,
                "pool_address": d.pool_address,
                "dex": d.dex,
                "token0": d.token0,
                "token1": d.token1,
                "reserve0": d.reserve0,
                "reserve1": d.reserve1,
                "total_liquidity": d.total_liquidity,
                "price": d.price,
                "fee_tier": d.fee_tier,
                "tvl": d.tvl,
            }
            for d in data
        ], schema=LiquidityPool.schema())
    
    @staticmethod
    def from_catalog(table: pa.Table) -> list["LiquidityPool"]:
        """Convert Arrow table to data objects."""
        return [
            LiquidityPool(
                ts_event=row["ts_event"],
                ts_init=row["ts_init"],
                pool_address=row["pool_address"],
                dex=row["dex"],
                token0=row["token0"],
                token1=row["token1"],
                reserve0=row["reserve0"],
                reserve1=row["reserve1"],
                total_liquidity=row["total_liquidity"],
                price=row["price"],
                fee_tier=row["fee_tier"],
                tvl=row["tvl"],
            )
            for row in table.to_pylist()
        ]


# Register both data types with catalog
register_arrow(DeFiSwap, DeFiSwap.schema(), DeFiSwap.to_catalog, DeFiSwap.from_catalog)
register_arrow(LiquidityPool, LiquidityPool.schema(), LiquidityPool.to_catalog, LiquidityPool.from_catalog)

