"""Utility for capturing stdout/stderr and print statements during backtest execution."""
import sys
import io
from typing import List, Callable, Optional
from threading import Lock
from contextlib import contextmanager


class LogCapture:
    """Captures stdout/stderr and print statements, forwarding them to callbacks."""
    
    def __init__(self):
        self.logs: List[str] = []
        self.lock = Lock()
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.callbacks: List[Callable[[str], None]] = []
        self.enabled = False
        self._stdout_wrapper: Optional[object] = None
        self._stderr_wrapper: Optional[object] = None
    
    def add_callback(self, callback: Callable[[str], None]):
        """Add a callback function to be called for each log line."""
        self.callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[str], None]):
        """Remove a callback function."""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def _write(self, stream, data: str):
        """Internal write method that captures and forwards logs."""
        with self.lock:
            # Write to original stream (so logs still appear in console)
            stream.write(data)
            stream.flush()
            
            # Store log line
            if data.strip():
                log_line = data.rstrip()
                self.logs.append(log_line)
                
                # Call all callbacks
                for callback in self.callbacks:
                    try:
                        callback(log_line)
                    except Exception:
                        pass  # Don't let callback errors break logging
    
    def start(self):
        """Start capturing logs."""
        if self.enabled:
            return
        
        self.enabled = True
        
        # Create custom stdout/stderr that forward to original + capture
        class CapturingIO:
            def __init__(self, original, capture_func):
                self.original = original
                self.capture_func = capture_func
            
            def write(self, data):
                if isinstance(data, bytes):
                    data = data.decode('utf-8', errors='replace')
                self.capture_func(self.original, data)
            
            def flush(self):
                self.original.flush()
            
            def __getattr__(self, name):
                return getattr(self.original, name)
        
        # Replace stdout/stderr
        self._stdout_wrapper = CapturingIO(self.original_stdout, self._write)
        self._stderr_wrapper = CapturingIO(self.original_stderr, self._write)
        sys.stdout = self._stdout_wrapper
        sys.stderr = self._stderr_wrapper
    
    def stop(self):
        """Stop capturing logs and restore original streams."""
        if not self.enabled:
            return
        
        self.enabled = False
        
        # Restore original streams
        if sys.stdout is self._stdout_wrapper:
            sys.stdout = self.original_stdout
        if sys.stderr is self._stderr_wrapper:
            sys.stderr = self.original_stderr
    
    def get_logs(self) -> List[str]:
        """Get all captured logs."""
        with self.lock:
            return self.logs.copy()
    
    def get_latest_step(self) -> Optional[str]:
        """Extract the latest step from logs (looks for 'Status:' prefix)."""
        with self.lock:
            # Look for the most recent "Status:" line
            for log in reversed(self.logs):
                if "Status:" in log:
                    # Extract step description (remove "Status:" prefix)
                    step = log.split("Status:")[-1].strip()
                    # Clean up common prefixes and formatting
                    step = step.replace("✓", "").strip()
                    # Remove leading/trailing dashes or colons
                    step = step.lstrip(":- ").rstrip(":- ")
                    if step:
                        return step
            return None
    
    def clear(self):
        """Clear captured logs."""
        with self.lock:
            self.logs = []
    
    @contextmanager
    def capture(self):
        """Context manager for capturing logs."""
        self.start()
        self.clear()
        try:
            yield self
        finally:
            self.stop()


# Thread-local storage for per-request log capture
import threading
_thread_local = threading.local()


def get_log_capture() -> LogCapture:
    """Get or create a thread-local log capture instance."""
    if not hasattr(_thread_local, 'capture'):
        _thread_local.capture = LogCapture()
    return _thread_local.capture

