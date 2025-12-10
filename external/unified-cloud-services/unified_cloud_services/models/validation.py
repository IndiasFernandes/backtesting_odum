"""
Validation models for unified cloud services
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class ValidationResult:
    """Result from data validation operations - used across all validation services"""

    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    validation_type: str = "general"
    total_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0

    @property
    def validity_rate(self) -> float:
        return self.valid_records / self.total_records if self.total_records > 0 else 0.0
