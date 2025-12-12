"""
Standalone stderr filter - NO IMPORTS FROM BACKEND.

This file installs the stderr filter BEFORE any backend imports.
It must be completely standalone to avoid circular imports.
"""
import sys
from typing import TextIO


class FilteredStderr:
    """Filtered stderr that suppresses specific warning messages."""
    
    def __init__(self, original_stderr: TextIO):
        self.original_stderr = original_stderr
    
    def write(self, message: str) -> None:
        """Write to stderr, filtering out suppressed messages."""
        # Check for databento warnings (case-insensitive)
        msg_lower = message.lower()
        if 'databento' in msg_lower and ('not available' in msg_lower or 'install' in msg_lower):
            return  # Suppress databento warnings
        
        # Check for UCS local copy warnings
        if 'unified-cloud-services' in message and 'appears to be from local copy' in message:
            return  # Suppress UCS local copy warnings
        
        # Check for UCS warning prefix (with emoji)
        if '⚠️' in message and 'unified-cloud-services' in message:
            return  # Suppress UCS warnings
        
        # Check for UCS warning (without emoji)
        if 'WARNING' in message and 'unified-cloud-services' in message and 'local copy' in message:
            return  # Suppress UCS warnings
        
        self.original_stderr.write(message)
    
    def flush(self) -> None:
        """Flush stderr."""
        self.original_stderr.flush()
    
    def __getattr__(self, name: str):
        """Delegate other attributes to original stderr."""
        return getattr(self.original_stderr, name)


# Install filter immediately if not already installed
if not isinstance(sys.stderr, FilteredStderr):
    sys.stderr = FilteredStderr(sys.stderr)

