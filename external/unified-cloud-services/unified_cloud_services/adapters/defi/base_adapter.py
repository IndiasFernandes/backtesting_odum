"""
Base DeFi Adapter

Provides common functionality for DeFi protocol adapters.
Used by both instruments-service (metadata generation) and market-tick-data-handler (data acquisition).
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime

import pandas as pd

from unified_cloud_services import get_config

logger = logging.getLogger(__name__)


class BaseDefiAdapter(ABC):
    """
    Base class for DeFi protocol adapters.

    Provides common initialization, validation, and interface methods for:
    - instruments-service: Instrument metadata generation
    - market-tick-data-handler: Market data acquisition
    
    Subclasses should implement:
    - get_instrument_metadata(): For instruments-service
    - get_tick_data(): For market-tick-data-handler
    """

    def __init__(
        self,
        chain: str = "ETHEREUM",
        api_key: Optional[str] = None,
        project_id: Optional[str] = None,
    ):
        """
        Initialize base DeFi adapter.

        Args:
            chain: Chain identifier (e.g., 'ETHEREUM', 'ARBITRUM', 'BASE')
            api_key: Optional API key (uses Secret Manager if not provided)
            project_id: GCP project ID for Secret Manager (defaults to GCP_PROJECT_ID env var)
        """
        self.chain = chain.upper()
        self.api_key = api_key
        # Default to GCP_PROJECT_ID env var if not provided
        self.project_id = project_id or get_config("GCP_PROJECT_ID", "")

    def _validate_instrument_definition(self, inst_def: Dict[str, Any]) -> bool:
        """
        Validate instrument definition has required fields.

        Args:
            inst_def: Instrument definition dictionary

        Returns:
            True if valid, False otherwise
        """
        required_fields = [
            "instrument_key",
            "venue",
            "instrument_type",
            "base_asset",
            "quote_asset",
        ]

        for field in required_fields:
            if field not in inst_def or not inst_def[field]:
                logger.warning(f"Missing required field '{field}' in instrument definition")
                return False

        return True
    
    def _build_instrument_key(
        self, 
        venue: str, 
        instrument_type: str, 
        symbol: str
    ) -> str:
        """
        Build canonical instrument key.
        
        Args:
            venue: Venue identifier (e.g., 'AAVE_V3', 'UNISWAPV3-ETH')
            instrument_type: Instrument type (e.g., 'A_TOKEN', 'POOL')
            symbol: Symbol (e.g., 'WETH', 'ETH-USDC')
            
        Returns:
            Canonical instrument key in format VENUE:INSTRUMENT_TYPE:SYMBOL
        """
        return f"{venue}:{instrument_type}:{symbol}"

    # =========================================================================
    # Abstract methods - to be implemented by subclasses
    # =========================================================================

    @abstractmethod
    async def get_instrument_metadata(self) -> List[Dict[str, Any]]:
        """
        Get instrument metadata for this protocol.
        
        Used by instruments-service for instrument definition generation.
        
        Returns:
            List of instrument definition dictionaries
        """
        pass

    @abstractmethod
    async def download_market_data(
        self,
        instrument: Dict[str, Any],
        date: datetime,
        data_types: List[str],
    ) -> Dict[str, Any]:
        """
        Download market data for an instrument.
        
        Used by market-tick-data-handler for data acquisition.
        
        Args:
            instrument: Instrument definition dictionary
            date: Target date for data download
            data_types: List of data types to download
            
        Returns:
            Dictionary with download results and status
        """
        pass

