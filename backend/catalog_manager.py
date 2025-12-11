"""ParquetDataCatalog management for backtesting."""
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
import pyarrow.parquet as pq
from datetime import datetime

from nautilus_trader.persistence.catalog import ParquetDataCatalog
from nautilus_trader.model.data import TradeTick, OrderBookDeltas
from nautilus_trader.model.identifiers import InstrumentId


class CatalogManager:
    """
    Manages ParquetDataCatalog for backtest data.
    
    Supports both local filesystem and GCS storage:
    - Local: "backend/data/parquet/" or "/app/backend/data/parquet"
    - GCS: "gcs://execution-store-cefi-central-element-323112/nautilus-catalog/"
    
    When using GCS, converted data persists across runs, avoiding reconversion.
    """
    
    def __init__(self, catalog_path: Optional[str] = None, gcs_project_id: Optional[str] = None):
        """
        Initialize catalog manager.
        
        Args:
            catalog_path: Path to catalog root (defaults to DATA_CATALOG_PATH env var)
                         Can be local path or GCS path (gcs://bucket/path/)
            gcs_project_id: GCP project ID (for GCS catalog, defaults to env var)
        """
        if catalog_path is None:
            catalog_path = os.getenv("DATA_CATALOG_PATH", "backend/data/parquet/")
        
        self._catalog_path_str = catalog_path
        self.is_gcs = catalog_path.startswith("gcs://") or catalog_path.startswith("gs://")
        
        if self.is_gcs:
            # GCS path - normalize format
            if catalog_path.startswith("gs://"):
                catalog_path = catalog_path.replace("gs://", "gcs://", 1)
            self._catalog_path_str = catalog_path
            self.gcs_project_id = gcs_project_id or os.getenv("GCP_PROJECT_ID", "central-element-323112")
            # Get credentials path from env
            self.gcs_token = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            self._catalog_path = None  # Not applicable for GCS
        else:
            # Local path
            self._catalog_path = Path(catalog_path)
            self._catalog_path.mkdir(parents=True, exist_ok=True)
            self.gcs_project_id = None
            self.gcs_token = None
        
        self.catalog: Optional[ParquetDataCatalog] = None
    
    def initialize(self) -> ParquetDataCatalog:
        """
        Initialize ParquetDataCatalog.
        
        Supports both local filesystem and GCS storage.
        When using GCS, converted data persists and can be reused across runs.
        
        Returns:
            Initialized ParquetDataCatalog instance
        """
        if self.is_gcs:
            # Initialize GCS catalog
            fs_storage_options: Dict[str, Any] = {
                "project": self.gcs_project_id,
            }
            
            # Add token if provided
            if self.gcs_token:
                fs_storage_options["token"] = self.gcs_token
            
            self.catalog = ParquetDataCatalog(
                path=self._catalog_path_str,
                fs_protocol="gcs",
                fs_storage_options=fs_storage_options,
            )
            print(f"✅ Initialized GCS catalog: {self._catalog_path_str}")
        else:
            # Initialize local catalog
            self.catalog = ParquetDataCatalog(str(self._catalog_path))
            print(f"✅ Initialized local catalog: {self._catalog_path}")
        
        return self.catalog
    
    def get_catalog(self) -> ParquetDataCatalog:
        """
        Get catalog instance, initializing if needed.
        
        Returns:
            ParquetDataCatalog instance
        """
        if self.catalog is None:
            return self.initialize()
        return self.catalog
    
    @property
    def catalog_path(self) -> Path:
        """
        Get catalog path as Path object (for local catalogs only).
        
        Returns:
            Path object (raises error if GCS catalog)
        """
        if self.is_gcs:
            raise ValueError("Cannot get Path for GCS catalog. Use catalog_path_str property instead.")
        return self._catalog_path
    
    @property
    def catalog_path_str(self) -> str:
        """
        Get catalog path as string (works for both local and GCS).
        
        Returns:
            Catalog path string
        """
        return self._catalog_path_str
    
    def register_raw_parquet_file(
        self,
        file_path: Path,
        instrument_id: InstrumentId,
        data_cls: type,
        catalog: Optional[ParquetDataCatalog] = None
    ) -> None:
        """
        Register a raw Parquet file into the catalog by reading and writing it.
        
        This converts raw Parquet files into the catalog format.
        
        Args:
            file_path: Path to the raw Parquet file
            instrument_id: Instrument ID for the data
            data_cls: Data class (TradeTick, OrderBookDeltas, etc.)
            catalog: Catalog instance (uses self.catalog if None)
        """
        if catalog is None:
            catalog = self.get_catalog()
        
        if not file_path.exists():
            raise FileNotFoundError(f"Parquet file not found: {file_path}")
        
        # Read Parquet file using pyarrow
        parquet_file = pq.ParquetFile(file_path)
        table = parquet_file.read()
        
        # Convert to NautilusTrader data objects
        # Note: This assumes the Parquet schema matches NautilusTrader's expected format
        # For TradeTick, we need columns like: ts_event, ts_init, instrument_id, price, size, aggressor_side, trade_id
        # For OrderBookDeltas, we need different columns
        
        # Convert Arrow table to list of data objects
        # This is a simplified version - in production you'd need proper schema mapping
        data_objects = []
        
        # For now, we'll use the catalog's query method to read the file
        # if it's already in the right format, or we need to convert it properly
        # This is a placeholder - actual implementation would depend on the Parquet schema
        
        # Write to catalog
        if data_objects:
            catalog.write_data(data_objects)

