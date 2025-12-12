"""
Bootstrap module - installs stderr filter BEFORE any other imports.

This must be imported FIRST to catch warnings from NautilusTrader and other dependencies.
"""
import sys
import os

# Import standalone filter (no backend dependencies)
try:
    # Try to import from standalone module first
    from backend.utils._bootstrap_stderr import FilteredStderr
    # Install filter if not already installed
    if not isinstance(sys.stderr, FilteredStderr):
        sys.stderr = FilteredStderr(sys.stderr)
except ImportError:
    # Fallback: install filter inline (no imports)
    from typing import TextIO
    
    class FilteredStderr:
        """Filtered stderr that suppresses specific warning messages."""
        def __init__(self, original_stderr: TextIO):
            self.original_stderr = original_stderr
        
        def write(self, message: str) -> None:
            msg_lower = message.lower()
            if 'databento' in msg_lower and ('not available' in msg_lower or 'install' in msg_lower):
                return
            if 'unified-cloud-services' in message and 'appears to be from local copy' in message:
                return
            if '⚠️' in message and 'unified-cloud-services' in message:
                return
            if 'WARNING' in message and 'unified-cloud-services' in message and 'local copy' in message:
                return
            self.original_stderr.write(message)
        
        def flush(self) -> None:
            self.original_stderr.flush()
        
        def __getattr__(self, name: str):
            return getattr(self.original_stderr, name)
    
    if not isinstance(sys.stderr, FilteredStderr):
        sys.stderr = FilteredStderr(sys.stderr)

# Set environment variables to suppress warnings
os.environ.setdefault('NAUTILUS_SUPPRESS_DATABENTO_WARNING', '1')

