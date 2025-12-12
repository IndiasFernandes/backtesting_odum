"""
Stderr filter to suppress unwanted warnings from dependencies.

Filters:
- Databento warnings (optional dependency)
- UCS local copy warnings (development is fine)
"""
import sys
import re
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
        if '⚠️' in message and 'unified-cloud-services' in message and 'local copy' in message:
            return  # Suppress UCS warnings
        
        # Check for UCS warning (without emoji)
        if 'WARNING' in message and 'unified-cloud-services' in message and 'local copy' in message:
            return  # Suppress UCS warnings
        
        # Write non-suppressed messages
        self.original_stderr.write(message)
    
    def flush(self) -> None:
        """Flush stderr."""
        self.original_stderr.flush()
    
    def __getattr__(self, name: str):
        """Delegate other attributes to original stderr."""
        return getattr(self.original_stderr, name)


# Global flag to track if filter is installed
_filter_installed = False


def install_global_filter():
    """Install global stderr filter to suppress unwanted warnings."""
    global _filter_installed
    
    if _filter_installed:
        return  # Already installed
    
    # Replace sys.stderr with filtered version
    sys.stderr = FilteredStderr(sys.stderr)
    _filter_installed = True


def uninstall_global_filter():
    """Uninstall global stderr filter (restore original stderr)."""
    global _filter_installed
    
    if not _filter_installed:
        return
    
    if isinstance(sys.stderr, FilteredStderr):
        sys.stderr = sys.stderr.original_stderr
        _filter_installed = False

