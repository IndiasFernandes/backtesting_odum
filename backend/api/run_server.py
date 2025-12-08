#!/usr/bin/env python3
"""Run the API server."""
import uvicorn
from backend.api.server import app

if __name__ == "__main__":
    import sys
    try:
        uvicorn.run("backend.api.server:app", host="0.0.0.0", port=8000, reload=False, log_level="info")
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

