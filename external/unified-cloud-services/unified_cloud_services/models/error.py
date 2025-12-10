"""
Generic Error Models for Unified Cloud Services

Reusable error models that work across all domains (market_data, features, strategy, ml, execution).
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional


class ErrorSeverity(str, Enum):
    """Generic error severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Generic error categories for classification"""

    NETWORK = "network"
    API = "api"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    DATA_VALIDATION = "data_validation"
    STORAGE = "storage"
    CONFIGURATION = "configuration"
    SYSTEM = "system"
    BUSINESS_LOGIC = "business_logic"


@dataclass
class ErrorContext:
    """Generic error context for error tracking"""

    operation: str = ""
    component: str = ""
    input_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    additional_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        return {
            "operation": self.operation,
            "component": self.component,
            "timestamp": self.timestamp.isoformat(),
            "input_data": self.input_data,
            **self.additional_data,
        }
