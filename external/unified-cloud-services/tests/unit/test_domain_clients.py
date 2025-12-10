"""
Unit tests for domain clients (InstrumentsDomainClient and MarketTickDataDomainClient).

Tests factory functions and basic client functionality using test buckets.
"""

import pytest
import pandas as pd
from datetime import datetime
from unified_cloud_services.domain.clients import (
    InstrumentsDomainClient,
    MarketTickDataDomainClient,
    create_instruments_client,
    create_market_tick_data_client,
)
from unified_cloud_services import CloudTarget


class TestFactoryFunctions:
    """Test factory functions for creating domain clients."""
    
    def test_create_instruments_client(self, test_instruments_cloud_target):
        """Test create_instruments_client factory function."""
        client = create_instruments_client(
            project_id=test_instruments_cloud_target.project_id,
            gcs_bucket=test_instruments_cloud_target.gcs_bucket,
            bigquery_dataset=test_instruments_cloud_target.bigquery_dataset,
        )
        
        assert isinstance(client, InstrumentsDomainClient)
        assert client.cloud_target.project_id == test_instruments_cloud_target.project_id
        assert client.cloud_target.gcs_bucket == test_instruments_cloud_target.gcs_bucket
    
    def test_create_market_tick_data_client(self, test_market_data_cloud_target):
        """Test create_market_tick_data_client factory function."""
        client = create_market_tick_data_client(
            project_id=test_market_data_cloud_target.project_id,
            gcs_bucket=test_market_data_cloud_target.gcs_bucket,
            bigquery_dataset=test_market_data_cloud_target.bigquery_dataset,
        )
        
        assert isinstance(client, MarketTickDataDomainClient)
        assert client.cloud_target.project_id == test_market_data_cloud_target.project_id
        assert client.cloud_target.gcs_bucket == test_market_data_cloud_target.gcs_bucket
    
    def test_create_instruments_client_defaults(self):
        """Test create_instruments_client with default parameters."""
        client = create_instruments_client()
        assert isinstance(client, InstrumentsDomainClient)
    
    def test_create_market_tick_data_client_defaults(self):
        """Test create_market_tick_data_client with default parameters."""
        client = create_market_tick_data_client()
        assert isinstance(client, MarketTickDataDomainClient)


class TestInstrumentsDomainClient:
    """Test InstrumentsDomainClient functionality."""
    
    def test_get_instruments_for_date(self, test_instruments_cloud_target):
        """Test getting instruments for a specific date."""
        client = InstrumentsDomainClient(
            project_id=test_instruments_cloud_target.project_id,
            gcs_bucket=test_instruments_cloud_target.gcs_bucket,
            bigquery_dataset=test_instruments_cloud_target.bigquery_dataset,
        )
        
        # Test date: Sep 23, 2024 (should have data after copy from prod)
        date = "2024-09-23"
        instruments_df = client.get_instruments_for_date(date)
        
        # Should return DataFrame (may be empty if no data)
        assert isinstance(instruments_df, pd.DataFrame)
    
    def test_get_instruments_with_venue_filter(self, test_instruments_cloud_target):
        """Test filtering instruments by venue."""
        client = InstrumentsDomainClient(
            project_id=test_instruments_cloud_target.project_id,
            gcs_bucket=test_instruments_cloud_target.gcs_bucket,
            bigquery_dataset=test_instruments_cloud_target.bigquery_dataset,
        )
        
        date = "2024-09-23"
        instruments_df = client.get_instruments_for_date(date, venue="BINANCE-SPOT")
        
        assert isinstance(instruments_df, pd.DataFrame)
        if not instruments_df.empty:
            assert all(instruments_df["venue"] == "BINANCE-SPOT")
    
    def test_get_instruments_with_instrument_type_filter(self, test_instruments_cloud_target):
        """Test filtering instruments by instrument type."""
        client = InstrumentsDomainClient(
            project_id=test_instruments_cloud_target.project_id,
            gcs_bucket=test_instruments_cloud_target.gcs_bucket,
            bigquery_dataset=test_instruments_cloud_target.bigquery_dataset,
        )
        
        date = "2024-09-23"
        instruments_df = client.get_instruments_for_date(date, instrument_type="SPOT_PAIR")
        
        assert isinstance(instruments_df, pd.DataFrame)
        if not instruments_df.empty:
            assert all(instruments_df["instrument_type"] == "SPOT_PAIR")
    
    def test_get_instruments_with_instrument_ids(self, test_instruments_cloud_target):
        """Test filtering instruments by specific instrument IDs."""
        client = InstrumentsDomainClient(
            project_id=test_instruments_cloud_target.project_id,
            gcs_bucket=test_instruments_cloud_target.gcs_bucket,
            bigquery_dataset=test_instruments_cloud_target.bigquery_dataset,
        )
        
        date = "2024-09-23"
        # Test with VIX instrument ID
        instrument_ids = ["CBOE:INDEX:VIX-USD"]
        instruments_df = client.get_instruments_for_date(date, instrument_ids=instrument_ids)
        
        assert isinstance(instruments_df, pd.DataFrame)
        if not instruments_df.empty:
            assert all(instruments_df["instrument_key"].isin(instrument_ids))
    
    def test_get_summary_stats(self, test_instruments_cloud_target):
        """Test getting summary statistics."""
        client = InstrumentsDomainClient(
            project_id=test_instruments_cloud_target.project_id,
            gcs_bucket=test_instruments_cloud_target.gcs_bucket,
            bigquery_dataset=test_instruments_cloud_target.bigquery_dataset,
        )
        
        date = "2024-09-23"
        stats = client.get_summary_stats(date)
        
        assert isinstance(stats, dict)
        assert "total_instruments" in stats


class TestMarketTickDataDomainClient:
    """Test MarketTickDataDomainClient functionality."""
    
    def test_get_tick_data(self, test_market_data_cloud_target):
        """Test getting tick data for a specific date."""
        from datetime import datetime
        
        client = MarketTickDataDomainClient(
            project_id=test_market_data_cloud_target.project_id,
            gcs_bucket=test_market_data_cloud_target.gcs_bucket,
            bigquery_dataset=test_market_data_cloud_target.bigquery_dataset,
        )
        
        date = datetime(2024, 9, 23)
        instrument_id = "BINANCE-SPOT:SPOT_PAIR:BTC-USDT"
        data_type = "trades"
        
        tick_data = client.get_tick_data(
            date=date,
            instrument_id=instrument_id,
            data_type=data_type,
        )
        
        # Should return DataFrame (may be empty if no data)
        assert isinstance(tick_data, pd.DataFrame)
    
    def test_get_tick_data_with_venue_filter(self, test_market_data_cloud_target):
        """Test getting tick data filtered by venue."""
        from datetime import datetime
        
        client = MarketTickDataDomainClient(
            project_id=test_market_data_cloud_target.project_id,
            gcs_bucket=test_market_data_cloud_target.gcs_bucket,
            bigquery_dataset=test_market_data_cloud_target.bigquery_dataset,
        )
        
        date = datetime(2024, 9, 23)
        instrument_id = "BINANCE-SPOT:SPOT_PAIR:BTC-USDT"
        venue = "BINANCE-SPOT"
        data_type = "trades"
        
        tick_data = client.get_tick_data(
            date=date,
            instrument_id=instrument_id,
            data_type=data_type,
            venue=venue,
        )
        
        assert isinstance(tick_data, pd.DataFrame)

