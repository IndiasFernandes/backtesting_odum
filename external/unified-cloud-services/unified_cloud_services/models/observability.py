"""
Generic Observability Models for Unified Cloud Services

Reusable observability models that work across all domains (market_data, features, strategy, ml, execution).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List


@dataclass
class OperationContext:
    """Generic operation context for observability"""

    operation_name: str
    component: str = ""
    operation_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None

    @property
    def duration(self) -> Optional[float]:
        """Calculate operation duration in seconds"""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        return {
            "operation_name": self.operation_name,
            "component": self.component,
            "operation_id": self.operation_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "metadata": self.metadata,
            "performance_metrics": self.performance_metrics,
            "success": self.success,
            "error": self.error,
        }
