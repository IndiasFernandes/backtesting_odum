"""Generate sample DeFi data for Nautilus Trader."""
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import pyarrow.parquet as pq
import secrets

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from defi_data_types import DeFiSwap, LiquidityPool


def generate_sample_defi_swaps(
    start_date: datetime,
    end_date: datetime,
    dex: str = "uniswap",
    pool_address: str = "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",  # USDC/ETH pool
    token_in: str = "USDC",
    token_out: str = "WETH",
    output_path: Path = Path("defi_sample.parquet")
) -> None:
    """
    Generate sample DeFi swap data.
    
    Args:
        start_date: Start date for data generation
        end_date: End date for data generation
        dex: DEX name
        pool_address: Pool contract address
        token_in: Input token symbol
        token_out: Output token symbol
        output_path: Output Parquet file path
    """
    swaps = []
    current_time = start_date
    
    # Generate swaps every 5 minutes
    interval = timedelta(minutes=5)
    block_number = 18000000  # Starting block number
    
    while current_time < end_date:
        # Generate realistic swap data
        # Random swap size (in token_in units)
        amount_in = np.random.uniform(1000, 100000)
        
        # Price varies slightly (simulate market movement)
        base_price = 2000.0 + np.random.normal(0, 50)  # ETH price in USDC
        amount_out = amount_in / base_price
        
        # Price impact increases with swap size
        price_impact = min(0.001 * (amount_in / 10000), 0.05)  # Max 5% impact
        
        # Fee (typically 0.3% for Uniswap V3)
        fee = amount_in * 0.003
        
        # Transaction hash (simulated)
        tx_hash = "0x" + secrets.token_hex(32)
        
        # Trader address (simulated)
        trader = "0x" + secrets.token_hex(20)
        
        ts_event_ns = int(current_time.timestamp() * 1_000_000_000)
        ts_init_ns = ts_event_ns
        
        swap = DeFiSwap(
            ts_event=ts_event_ns,
            ts_init=ts_init_ns,
            transaction_hash=tx_hash,
            block_number=block_number,
            dex=dex,
            pool_address=pool_address,
            token_in=token_in,
            token_out=token_out,
            amount_in=round(amount_in, 2),
            amount_out=round(amount_out, 6),
            price_impact=round(price_impact, 6),
            fee=round(fee, 2),
            trader=trader,
        )
        swaps.append(swap)
        
        current_time += interval
        block_number += np.random.randint(1, 5)  # Blocks advance randomly
    
    if swaps:
        table = DeFiSwap.to_catalog(swaps)
        pq.write_table(table, output_path, compression='zstd')
        
        print(f"Generated {len(swaps)} DeFi swaps")
        print(f"Saved to: {output_path}")
        print(f"DEX: {dex}, Pool: {pool_address}")


def generate_sample_liquidity_pools(
    start_date: datetime,
    end_date: datetime,
    output_path: Path = Path("defi_liquidity_pools_sample.parquet")
) -> None:
    """
    Generate sample liquidity pool data.
    
    Args:
        start_date: Start date for data generation
        end_date: End date for data generation
        output_path: Output Parquet file path
    """
    pools = []
    current_time = start_date
    
    # Sample pools
    pool_configs = [
        {
            "pool_address": "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",
            "dex": "uniswap",
            "token0": "USDC",
            "token1": "WETH",
            "base_reserve0": 10000000,  # USDC
            "base_reserve1": 5000,  # WETH
            "fee_tier": 0.003,
        },
        {
            "pool_address": "0x11b815efB8f581194ae79006d24E0d814B7697F6",
            "dex": "uniswap",
            "token0": "USDC",
            "token1": "USDT",
            "base_reserve0": 50000000,
            "base_reserve1": 50000000,
            "fee_tier": 0.0005,
        },
        {
            "pool_address": "0x8ad599c3A0ff1De082011EFDDc58f1908eb6e6D8",
            "dex": "uniswap",
            "token0": "USDC",
            "token1": "WBTC",
            "base_reserve0": 20000000,
            "base_reserve1": 300,
            "fee_tier": 0.003,
        },
    ]
    
    # Generate snapshots every hour
    interval = timedelta(hours=1)
    
    while current_time < end_date:
        for pool_config in pool_configs:
            # Simulate reserve changes (liquidity providers add/remove)
            reserve0_change = np.random.uniform(0.95, 1.05)
            reserve1_change = np.random.uniform(0.95, 1.05)
            
            reserve0 = pool_config["base_reserve0"] * reserve0_change
            reserve1 = pool_config["base_reserve1"] * reserve1_change
            
            # Calculate price (token1/token0)
            price = reserve1 / reserve0 if reserve0 > 0 else 0
            
            # Total liquidity (simplified)
            total_liquidity = reserve0 + (reserve1 * price)
            
            # TVL in USD (simplified - assume token0 is USD stablecoin)
            tvl = reserve0 + (reserve1 * price * reserve0 / reserve1) if reserve1 > 0 else reserve0
            
            ts_event_ns = int(current_time.timestamp() * 1_000_000_000)
            ts_init_ns = ts_event_ns
            
            pool = LiquidityPool(
                ts_event=ts_event_ns,
                ts_init=ts_init_ns,
                pool_address=pool_config["pool_address"],
                dex=pool_config["dex"],
                token0=pool_config["token0"],
                token1=pool_config["token1"],
                reserve0=round(reserve0, 2),
                reserve1=round(reserve1, 6),
                total_liquidity=round(total_liquidity, 2),
                price=round(price, 6),
                fee_tier=pool_config["fee_tier"],
                tvl=round(tvl, 2),
            )
            pools.append(pool)
        
        current_time += interval
    
    if pools:
        table = LiquidityPool.to_catalog(pools)
        pq.write_table(table, output_path, compression='zstd')
        
        print(f"Generated {len(pools)} liquidity pool snapshots")
        print(f"Saved to: {output_path}")


if __name__ == "__main__":
    # Generate sample data for the past 7 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    output_dir = Path(__file__).parent
    output_dir.mkdir(exist_ok=True)
    
    # Generate DeFi swaps
    generate_sample_defi_swaps(
        start_date=start_date,
        end_date=end_date,
        dex="uniswap",
        pool_address="0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",
        token_in="USDC",
        token_out="WETH",
        output_path=output_dir / "defi_sample.parquet"
    )
    
    # Generate liquidity pool snapshots
    generate_sample_liquidity_pools(
        start_date=start_date,
        end_date=end_date,
        output_path=output_dir / "defi_liquidity_pools_sample.parquet"
    )
    
    print("\n✅ DeFi sample data generation complete!")

