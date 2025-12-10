"""Package models"""

from unified_cloud_services.models.validation import ValidationResult
from unified_cloud_services.models.error import ErrorSeverity, ErrorCategory, ErrorContext
from unified_cloud_services.models.observability import OperationContext
from unified_cloud_services.models.instrument import (
    Venue,
    InstrumentType,
)
from unified_cloud_services.models.venue_config import (
    VenueMapping,
    DataTypeConfig,
    ExchangeInstrumentConfig,
)
from unified_cloud_services.models.schemas import (
    InstrumentKey,
    ValidationConfig,
    DownloadTarget,
    OrchestrationResult,
)
from unified_cloud_services.models.nautilus_schema import (
    NAUTILUS_TRADES_SCHEMA,
    NAUTILUS_BOOK_SNAPSHOT_5_SCHEMA,
    NAUTILUS_LIQUIDATIONS_SCHEMA,
    NAUTILUS_DERIVATIVE_TICKER_SCHEMA,
    NAUTILUS_SCHEMA_MAP,
    convert_to_nautilus_instrument_id,
    convert_from_nautilus_instrument_id,
    transform_to_nautilus,
    transform_trades_to_nautilus,
    transform_book_snapshot_to_nautilus,
    get_nautilus_schema,
    get_nautilus_pyarrow_schema,
)

__all__ = [
    "ValidationResult",
    "ErrorSeverity",
    "ErrorCategory",
    "ErrorContext",
    "OperationContext",
    "Venue",
    "InstrumentType",
    # Venue configuration classes
    "VenueMapping",
    "DataTypeConfig",
    "ExchangeInstrumentConfig",
    # Shared schemas
    "InstrumentKey",
    "ValidationConfig",
    "DownloadTarget",
    "OrchestrationResult",
    # NautilusTrader schemas and transformers
    "NAUTILUS_TRADES_SCHEMA",
    "NAUTILUS_BOOK_SNAPSHOT_5_SCHEMA",
    "NAUTILUS_LIQUIDATIONS_SCHEMA",
    "NAUTILUS_DERIVATIVE_TICKER_SCHEMA",
    "NAUTILUS_SCHEMA_MAP",
    "convert_to_nautilus_instrument_id",
    "convert_from_nautilus_instrument_id",
    "transform_to_nautilus",
    "transform_trades_to_nautilus",
    "transform_book_snapshot_to_nautilus",
    "get_nautilus_schema",
    "get_nautilus_pyarrow_schema",
]
