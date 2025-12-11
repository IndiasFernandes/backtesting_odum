"""REST API server for backtest operations."""
import json
import os
import asyncio
import uuid
import queue
from pathlib import Path
from typing import List, Dict, Any, Optional
from functools import lru_cache
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

try:
    from backend.core.engine import BacktestEngine
    from backend.data.catalog import CatalogManager
    from backend.config.loader import ConfigLoader
    from backend.utils.validation import validate_iso8601
    from backend.api.mount_status import check_mount_status
    from backend.utils.log_capture import get_log_capture
    from backend.api.data_checker import DataAvailabilityChecker
    # Import ResultSerializer at module level to verify it loads
    from backend.results.serializer import ResultSerializer
    print("=" * 80)
    print("✓ ResultSerializer imported successfully at module level")
    print("=" * 80)
except ImportError as e:
    import sys
    print(f"Error importing backend modules: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    raise

app = FastAPI(title="Odum Trader Backtest API")

# Store active backtest tasks and their log queues (thread-safe queues)
_active_backtests: Dict[str, queue.Queue] = {}

# Import and include algorithm manager router
try:
    from backend.api.algorithm_manager import router as algorithm_router
    app.include_router(algorithm_router)
    print(f"✓ Algorithm manager router included: {len([r for r in app.routes if hasattr(r, 'path') and 'algorithm' in r.path.lower()])} routes")
except Exception as e:
    print(f"✗ Warning: Could not import/include algorithm manager router: {e}")
    import traceback
    traceback.print_exc()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_configs_dir() -> Optional[Path]:
    """Get the configs directory, trying multiple possible paths."""
    possible_paths = [
        Path("external/data_downloads/configs"),  # Relative from project root
        Path(__file__).parent.parent.parent / "external" / "data_downloads" / "configs",  # Relative from this file
        Path("/app/external/data_downloads/configs"),  # Docker absolute path
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
    
    return None


def _resolve_config_path(config_name: str) -> Optional[Path]:
    """Resolve a config file path, trying multiple possible locations."""
    # First try as absolute path
    config_path = Path(config_name)
    if config_path.exists():
        return config_path
    
    # Try relative to configs directory
    configs_dir = _get_configs_dir()
    if configs_dir:
        candidate = configs_dir / config_name
        if candidate.exists():
            return candidate
    
    return None


def _get_results_output_dir() -> Path:
    """Get the results output directory, trying multiple possible paths."""
    import os
    cwd = Path(os.getcwd())
    
    # Try multiple possible base paths
    possible_bases = [
        cwd,  # Current working directory
        Path(__file__).parent.parent.parent,  # Project root relative to this file
        Path("/app"),  # Docker absolute path
    ]
    
    for base in possible_bases:
        results_dir = base / "backend" / "backtest_results"
        if results_dir.exists():
            return results_dir
    
    # Fallback: create in current directory
    results_dir = cwd / "backend" / "backtest_results"
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Odum Trader Backtest API"}


@app.get("/api/mount/status")
async def get_mount_status() -> Dict[str, Any]:
    """Get GCS FUSE mount status."""
    return check_mount_status()


class BacktestRunRequest(BaseModel):
    instrument: str
    dataset: Optional[str] = None  # Optional - auto-detected from time window if not provided
    config: str
    start: str
    end: str
    fast: bool = False
    report: bool = False
    export_ticks: bool = False
    snapshot_mode: str = "both"
    data_source: str = "gcs"  # 'local' or 'gcs' (default: 'gcs')
    exec_algorithm: Optional[str] = None  # 'NORMAL', 'TWAP', 'VWAP', 'ICEBERG'
    exec_algorithm_params: Optional[Dict[str, Any]] = None  # Algorithm-specific parameters


class DataCheckRequest(BaseModel):
    instrument_id: str
    start: str
    end: str
    snapshot_mode: str = "both"
    data_source: str = "gcs"


def _run_backtest_sync(
    request: BacktestRunRequest,
    log_queue: queue.Queue
) -> Dict[str, Any]:
    """Run backtest synchronously in executor and send logs to queue."""
    log_capture = get_log_capture()
    
    def send_log(log_line: str):
        """Callback to send log to queue."""
        try:
            log_queue.put_nowait({"type": "log", "data": log_line})
        except Exception:
            pass  # Ignore queue errors
    
    def send_step(step: str):
        """Callback to send step update to queue."""
        try:
            log_queue.put_nowait({"type": "step", "data": step})
        except Exception:
            pass
    
    # Use context manager to ensure logs are captured and cleaned up
    with log_capture.capture():
        log_capture.add_callback(send_log)
        
        try:
            # Send initial step
            send_step("Loading configuration...")
            
            # Load config
            config_path = _resolve_config_path(request.config)
            if not config_path:
                raise ValueError(f"Config not found: {request.config}")
            
            config_loader = ConfigLoader(str(config_path))
            config_loader.load()
            
            send_step("Parsing timestamps...")
            
            # Parse timestamps
            start = validate_iso8601(request.start)
            end = validate_iso8601(request.end)
            
            # Auto-detect dataset from time window if not provided
            dataset = request.dataset
            if not dataset:
                start_date = start.date() if hasattr(start, 'date') else start.date()
                dataset = f"day-{start_date.strftime('%Y-%m-%d')}"
                print(f"Status: Auto-detected dataset '{dataset}' from time window")
            
            send_step("Initializing backtest engine...")
            
            # Initialize engine
            catalog_manager = CatalogManager()
            engine = BacktestEngine(config_loader, catalog_manager)
            
            send_step("Running backtest...")
            
            # Run backtest
            result = engine.run(
                instrument=request.instrument,
                dataset=dataset,
                start=start,
                end=end,
                snapshot_mode=request.snapshot_mode,
                fast_mode=request.fast,
                export_ticks=request.export_ticks,
                close_positions=True,  # Default to closing positions
                data_source=request.data_source,
                exec_algorithm_type=request.exec_algorithm,
                exec_algorithm_params=request.exec_algorithm_params
            )
            
            send_step("Saving results...")
            
            # Save results to disk (same as CLI)
            # ResultSerializer is already imported at module level
            results_base = _get_results_output_dir()
            
            if request.fast:
                output_dir = results_base / "fast"
                output_dir.mkdir(parents=True, exist_ok=True)
                ResultSerializer.save_fast(result, output_dir)
                print(f"Fast mode result saved to: {output_dir}/{result['run_id']}.json")
            elif request.report or not request.fast:
                # Report mode (explicit or default when fast=False)
                output_dir = results_base / "report"
                output_dir.mkdir(parents=True, exist_ok=True)
                try:
                    ResultSerializer.save_report(result, output_dir)
                    print(f"Report mode result saved to: {output_dir}/{result['run_id']}/summary.json")
                except Exception as e:
                    print(f"ERROR in save_report: {e}")
                    import traceback
                    traceback.print_exc()
                    raise
            
            # Get captured logs and latest step
            logs = log_capture.get_logs()
            latest_step = log_capture.get_latest_step() or "Complete"
            
            # Add logs and step info to result
            result['logs'] = logs
            result['latest_step'] = latest_step
            
            # Send completion message
            log_queue.put_nowait({"type": "complete", "data": result})
            
            return result
            
        except Exception as e:
            # Get logs even on error
            logs = log_capture.get_logs()
            latest_step = log_capture.get_latest_step() or "Error occurred"
            
            # Send error message
            log_queue.put_nowait({
                "type": "error",
                "data": {
                    "message": str(e),
                    "logs": logs[-20:] if logs else []  # Last 20 lines
                }
            })
            raise
        finally:
            log_capture.remove_callback(send_log)


@app.post("/api/backtest/run")
async def run_backtest(request: BacktestRunRequest) -> Dict[str, Any]:
    """Execute a backtest run (legacy endpoint - returns after completion)."""
    log_capture = get_log_capture()
    
    # Use context manager to ensure logs are captured and cleaned up
    with log_capture.capture():
        try:
            # Load config
            config_path = _resolve_config_path(request.config)
            if not config_path:
                raise HTTPException(status_code=404, detail=f"Config not found: {request.config}")
            
            config_loader = ConfigLoader(str(config_path))
            config_loader.load()
            
            # Parse timestamps
            start = validate_iso8601(request.start)
            end = validate_iso8601(request.end)
            
            # Auto-detect dataset from time window if not provided
            dataset = request.dataset
            if not dataset:
                start_date = start.date() if hasattr(start, 'date') else start.date()
                dataset = f"day-{start_date.strftime('%Y-%m-%d')}"
                print(f"Status: Auto-detected dataset '{dataset}' from time window")
            
            # Initialize engine
            catalog_manager = CatalogManager()
            engine = BacktestEngine(config_loader, catalog_manager)
            
            # Run backtest
            result = engine.run(
                instrument=request.instrument,
                dataset=dataset,
                start=start,
                end=end,
                snapshot_mode=request.snapshot_mode,
                fast_mode=request.fast,
                export_ticks=request.export_ticks,
                close_positions=True,  # Default to closing positions
                data_source=request.data_source,
                exec_algorithm_type=request.exec_algorithm,
                exec_algorithm_params=request.exec_algorithm_params
            )
            
            # Save results to disk (same as CLI)
            # ResultSerializer is already imported at module level
            results_base = _get_results_output_dir()
            
            if request.fast:
                output_dir = results_base / "fast"
                output_dir.mkdir(parents=True, exist_ok=True)
                ResultSerializer.save_fast(result, output_dir)
                print(f"Fast mode result saved to: {output_dir}/{result['run_id']}.json")
            elif request.report or not request.fast:
                # Report mode (explicit or default when fast=False)
                output_dir = results_base / "report"
                output_dir.mkdir(parents=True, exist_ok=True)
                try:
                    ResultSerializer.save_report(result, output_dir)
                    print(f"Report mode result saved to: {output_dir}/{result['run_id']}/summary.json")
                except Exception as e:
                    print(f"ERROR in save_report: {e}")
                    import traceback
                    traceback.print_exc()
                    raise
            
            # Get captured logs and latest step
            logs = log_capture.get_logs()
            latest_step = log_capture.get_latest_step() or "Complete"
            
            # Add logs and step info to result
            result['logs'] = logs
            result['latest_step'] = latest_step
            
            return result
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            # Get logs even on error
            logs = log_capture.get_logs()
            latest_step = log_capture.get_latest_step() or "Error occurred"
            
            # Include logs in error response
            error_detail = str(e)
            if logs:
                error_detail += f"\n\nLogs:\n" + "\n".join(logs[-20:])  # Last 20 lines
            
            raise HTTPException(status_code=500, detail=error_detail)


@app.post("/api/backtest/run/stream")
async def run_backtest_stream(request: BacktestRunRequest):
    """Execute a backtest run with Server-Sent Events streaming for real-time logs."""
    task_id = str(uuid.uuid4())
    log_queue: queue.Queue = queue.Queue()
    _active_backtests[task_id] = log_queue
    
    # Start backtest in background executor
    loop = asyncio.get_event_loop()
    executor_task = loop.run_in_executor(
        None,
        _run_backtest_sync,
        request,
        log_queue
    )
    
    async def event_generator():
        """Generate SSE events from log queue."""
        try:
            while True:
                try:
                    # Poll queue with timeout (non-blocking)
                    try:
                        message = log_queue.get(timeout=0.1)
                    except queue.Empty:
                        # Check if executor task is done
                        if executor_task.done():
                            # Task completed, check for any remaining messages
                            try:
                                while True:
                                    message = log_queue.get_nowait()
                                    if message["type"] in ("complete", "error"):
                                        yield f"data: {json.dumps(message)}\n\n"
                                        return
                                    yield f"data: {json.dumps(message)}\n\n"
                            except queue.Empty:
                                # No more messages, task must have completed without sending complete/error
                                yield f"data: {json.dumps({'type': 'error', 'data': {'message': 'Backtest completed unexpectedly'}})}\n\n"
                                return
                        # Send heartbeat to keep connection alive
                        yield f": heartbeat\n\n"
                        await asyncio.sleep(0.1)
                        continue
                    
                    if message["type"] == "complete":
                        # Send final result
                        yield f"data: {json.dumps(message)}\n\n"
                        break
                    elif message["type"] == "error":
                        # Send error
                        yield f"data: {json.dumps(message)}\n\n"
                        break
                    elif message["type"] == "step":
                        # Send step update
                        yield f"data: {json.dumps(message)}\n\n"
                    elif message["type"] == "log":
                        # Send log line
                        yield f"data: {json.dumps(message)}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'error', 'data': {'message': str(e)}})}\n\n"
                    break
        finally:
            # Clean up
            if task_id in _active_backtests:
                del _active_backtests[task_id]
            # Cancel executor task if still running
            if not executor_task.done():
                executor_task.cancel()
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering in nginx
        }
    )


def _load_results_fast() -> List[Dict[str, Any]]:
    """Load fast results synchronously (called from async endpoint). Loads ALL results."""
    results = []
    
    # Try multiple possible paths for Docker compatibility
    # Also try resolving relative to current working directory
    import os
    cwd = Path(os.getcwd())
    possible_paths = [
        Path("backend/backtest_results/fast"),  # Relative from project root
        Path("/app/backend/backtest_results/fast"),  # Docker absolute path
        Path(__file__).parent.parent.parent / "backtest_results" / "fast",  # Relative from this file
        cwd / "backend" / "backtest_results" / "fast",  # Relative from current working directory
        cwd / "backtest_results" / "fast",  # Alternative relative path
    ]
    
    fast_dir = None
    for path in possible_paths:
        abs_path = path.resolve()
        if abs_path.exists():
            fast_dir = abs_path
            print(f"DEBUG: Found fast directory at: {fast_dir}")
            break
    
    if not fast_dir or not fast_dir.exists():
        print(f"DEBUG: Fast directory not found. Tried paths: {[str(p) for p in possible_paths]}")
        return results
    
    try:
        # Load ALL fast results (no limit)
        # Sort by modification time (newest first) to preserve chronological order
        fast_files = sorted(
            [f for f in fast_dir.glob("*.json") if f.is_file()],
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        for result_file in fast_files:
            try:
                # Get modification time for sorting (fallback for old results)
                mtime = result_file.stat().st_mtime
                with open(result_file, 'r') as f:
                    data = json.load(f)
                    # Only include fast mode results
                    if data.get('mode') == 'fast':
                        # Use execution_time if available, otherwise use file mtime as fallback
                        execution_time = data.get('execution_time')
                        if not execution_time or execution_time is None:
                            # Convert mtime to ISO format UTC string for consistency
                            from datetime import datetime, timezone
                            execution_time = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat().replace('+00:00', 'Z')
                            print(f"DEBUG: Set execution_time for {data.get('run_id')}: {execution_time}")
                        # Always set execution_time to ensure it's present
                        data['execution_time'] = execution_time
                        data['_execution_time_sort'] = execution_time  # Internal field for sorting
                        results.append(data)
            except (json.JSONDecodeError, IOError, OSError, KeyError) as e:
                # Skip malformed files
                continue
    except (OSError, PermissionError) as e:
        raise
    
    # Sort by execution_time (newest first)
    results.sort(key=lambda x: x.get('_execution_time_sort', ''), reverse=True)
    
    # Remove internal sorting field before returning, but keep execution_time
    for result in results:
        result.pop('_mtime', None)
        result.pop('_execution_time_sort', None)
        # Ensure execution_time is present and not None (should already be set above)
        if 'execution_time' not in result or result.get('execution_time') is None:
            # Fallback: use file mtime if available, otherwise current time
            from datetime import datetime, timezone
            run_id = result.get('run_id', '')
            mtime = None
            try:
                # Try to get file mtime
                fast_paths = [
                    Path(f"backend/backtest_results/fast/{run_id}.json"),
                    Path(f"/app/backend/backtest_results/fast/{run_id}.json"),
                ]
                for path in fast_paths:
                    if path.exists():
                        mtime = path.stat().st_mtime
                        break
            except Exception:
                pass
            
            if mtime:
                result['execution_time'] = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat().replace('+00:00', 'Z')
            else:
                result['execution_time'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    return results

def _load_results_report() -> List[Dict[str, Any]]:
    """Load report results synchronously (called from async endpoint). Returns lightweight metadata only. Loads ALL results."""
    results = []
    
    # Try multiple possible paths for Docker compatibility
    # Also try resolving relative to current working directory
    import os
    cwd = Path(os.getcwd())
    possible_paths = [
        Path("backend/backtest_results/report"),  # Relative from project root
        Path("/app/backend/backtest_results/report"),  # Docker absolute path
        Path(__file__).parent.parent.parent / "backtest_results" / "report",  # Relative from this file
        cwd / "backend" / "backtest_results" / "report",  # Relative from current working directory
        cwd / "backtest_results" / "report",  # Alternative relative path
    ]
    
    report_dir = None
    for path in possible_paths:
        abs_path = path.resolve()
        if abs_path.exists():
            report_dir = abs_path
            print(f"DEBUG: Found report directory at: {report_dir}")
            break
    
    if not report_dir or not report_dir.exists():
        print(f"DEBUG: Report directory not found. Tried paths: {[str(p) for p in possible_paths]}")
        return results
    
    try:
        # Load ALL report results (no limit)
        # Sort by modification time (newest first) to preserve chronological order
        report_dirs = sorted(
            [d for d in report_dir.iterdir() if d.is_dir() and not d.name.startswith('.')],
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        for run_dir in report_dirs:
                summary_file = run_dir / "summary.json"
                if summary_file.exists():
                    try:
                        # Get modification time for sorting (fallback for old results)
                        mtime = summary_file.stat().st_mtime
                        with open(summary_file, 'r') as f:
                            data = json.load(f)
                        
                        # Use execution_time if available, otherwise use file mtime as fallback
                        execution_time = data.get('execution_time')
                        if not execution_time or execution_time is None:
                            # Convert mtime to ISO format UTC string for consistency
                            from datetime import datetime, timezone
                            execution_time = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat().replace('+00:00', 'Z')
                        
                        # Return lightweight version with just metadata and summary
                        results.append({
                            "run_id": data.get('run_id'),
                            "mode": "report",
                            "instrument": data.get('instrument'),
                            "dataset": data.get('dataset'),
                            "start": data.get('start'),
                            "end": data.get('end'),
                            "execution_time": execution_time,
                            "summary": data.get('summary', {}),
                            "metadata": data.get('metadata', {}),
                            "_execution_time_sort": execution_time  # Internal field for sorting
                        })
                    except (json.JSONDecodeError, IOError, OSError, KeyError):
                        # Skip malformed files
                        continue
    except (OSError, PermissionError):
        raise
    
    # Sort by execution_time (newest first)
    results.sort(key=lambda x: x.get('_execution_time_sort', ''), reverse=True)
    
    # Remove internal sorting field before returning
    for result in results:
        result.pop('_execution_time_sort', None)
    
    return results

def _load_all_results() -> List[Dict[str, Any]]:
    """Load both fast and report results, combined and sorted."""
    fast_results = _load_results_fast()
    report_results = _load_results_report()
    
    # Combine both lists and add mtime for sorting
    all_results = []
    for result in fast_results + report_results:
        # Try to get mtime from file system if not already present
        run_id = result.get('run_id', '')
        if not result.get('_mtime'):
            # Try to find the file and get its mtime
            try:
                # For report mode, check report directory
                report_paths = [
                    Path(f"backend/backtest_results/report/{run_id}/summary.json"),
                    Path(f"/app/backend/backtest_results/report/{run_id}/summary.json"),
                ]
                for path in report_paths:
                    if path.exists():
                        result['_mtime'] = path.stat().st_mtime
                        break
                
                # For fast mode, check fast directory
                if not result.get('_mtime'):
                    fast_paths = [
                        Path(f"backend/backtest_results/fast/{run_id}.json"),
                        Path(f"/app/backend/backtest_results/fast/{run_id}.json"),
                    ]
                    for path in fast_paths:
                        if path.exists():
                            result['_mtime'] = path.stat().st_mtime
                            break
            except Exception:
                pass
        
        all_results.append(result)
    
    # Ensure execution_time is present for all results (fallback to file mtime if missing)
    for result in all_results:
        run_id = result.get('run_id', 'unknown')
        if 'execution_time' not in result or result.get('execution_time') is None:
            print(f"DEBUG _load_all_results: Missing execution_time for {run_id}, adding fallback")
            # Try to get from file mtime
            run_id = result.get('run_id', '')
            try:
                from datetime import datetime, timezone
                # Try report directory first
                report_paths = [
                    Path(f"backend/backtest_results/report/{run_id}/summary.json"),
                    Path(f"/app/backend/backtest_results/report/{run_id}/summary.json"),
                ]
                mtime = None
                for path in report_paths:
                    if path.exists():
                        mtime = path.stat().st_mtime
                        break
                
                # Try fast directory if not found
                if mtime is None:
                    fast_paths = [
                        Path(f"backend/backtest_results/fast/{run_id}.json"),
                        Path(f"/app/backend/backtest_results/fast/{run_id}.json"),
                    ]
                    for path in fast_paths:
                        if path.exists():
                            mtime = path.stat().st_mtime
                            break
                
                if mtime:
                    result['execution_time'] = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat().replace('+00:00', 'Z')
                else:
                    # Last resort: use current time
                    result['execution_time'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            except Exception:
                # If all else fails, use current time
                from datetime import datetime, timezone
                result['execution_time'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    # Sort by execution_time (newest first) - most recent results appear first
    all_results.sort(key=lambda x: x.get('execution_time', ''), reverse=True)
    
    return all_results


@app.get("/api/backtest/results")
async def get_results() -> List[Dict[str, Any]]:
    """List all backtest results (both fast and report modes combined)."""
    try:
        # Run file I/O in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, _load_all_results)
        return results
    except Exception as e:
        # Log the error and return a proper HTTP error response
        import traceback
        error_detail = f"Error loading backtest results: {str(e)}"
        print(f"Error in get_results: {error_detail}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_detail)

@app.get("/api/backtest/results/fast")
async def get_fast_results() -> List[Dict[str, Any]]:
    """List only fast mode backtest results."""
    try:
        # Run file I/O in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, _load_results_fast)
        return results
    except Exception as e:
        # Log the error and return a proper HTTP error response
        import traceback
        error_detail = f"Error loading fast backtest results: {str(e)}"
        print(f"Error in get_fast_results: {error_detail}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_detail)


@app.get("/api/backtest/results/report")
async def get_report_results() -> List[Dict[str, Any]]:
    """List all report backtest results. Returns lightweight metadata only."""
    try:
        # Run file I/O in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, _load_results_report)
        return results
    except Exception as e:
        # Log the error and return a proper HTTP error response
        import traceback
        error_detail = f"Error loading report backtest results: {str(e)}"
        print(f"Error in get_report_results: {error_detail}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_detail)


@app.get("/api/backtest/results/{run_id}/fills")
async def get_fills(
    run_id: str,
    limit: int = 1000,
    offset: int = 0
) -> Dict[str, Any]:
    """Get fills for a specific backtest result with pagination.
    
    Args:
        run_id: Backtest run ID
        limit: Maximum number of fills to return (default: 1000, max: 10000)
        offset: Number of fills to skip (default: 0)
    
    Returns:
        Dictionary with 'fills' array and 'total' count
    """
    # Cap limit to prevent excessive memory usage
    limit = min(limit, 10000)
    limit = max(limit, 1)  # At least 1
    # Try report results first (only report mode has fills detail)
    # Use same path resolution as get_report_result
    report_paths = [
        Path(f"backend/backtest_results/report/{run_id}"),
        Path(f"/app/backend/backtest_results/report/{run_id}"),
    ]
    
    report_dir = None
    for path in report_paths:
        if path.exists():
            report_dir = path
            break
    
    if not report_dir or not report_dir.exists():
        raise HTTPException(status_code=404, detail=f"Report result not found: {run_id}")
    
    fills = []
    timeline_file = report_dir / "timeline.json"
    if timeline_file.exists():
        try:
            loop = asyncio.get_event_loop()
            def load_timeline():
                with open(timeline_file, 'r') as f:
                    return json.load(f)
            timeline_data = await loop.run_in_executor(None, load_timeline)
            if isinstance(timeline_data, list):
                fills = []
                for event in timeline_data:
                    event_type = event.get('event')
                    event_data = event.get('data', {})
                    ts = event.get('ts', '')
                    
                    # Extract fills from both 'Fill' events and 'Order' events with status='filled'
                    if event_type == 'Fill':
                        fill_data = dict(event_data)
                        fill_data['timestamp'] = ts
                        fills.append(fill_data)
                    elif event_type == 'Order' and event_data.get('status') == 'filled':
                        # Extract fill information from filled orders
                        fill_data = {
                            'id': event_data.get('id'),
                            'order_id': event_data.get('id'),
                            'side': event_data.get('side'),
                            'price': event_data.get('price'),
                            'quantity': event_data.get('amount'),  # amount in orders = quantity in fills
                            'amount': event_data.get('amount'),
                            'timestamp': ts,
                        }
                        fills.append(fill_data)
                # Sort by timestamp
                fills.sort(key=lambda x: x.get('timestamp', ''))
        except (json.JSONDecodeError, IOError, OSError, Exception) as e:
            print(f"Error loading fills: {e}")
            import traceback
            traceback.print_exc()
            pass
    
    # Return paginated results
    total = len(fills)
    paginated_fills = fills[offset:offset + limit]
    
    return {
        'fills': paginated_fills,
        'total': total,
        'limit': limit,
        'offset': offset,
        'has_more': offset + limit < total
    }


@app.get("/api/backtest/results/{run_id}/rejected-orders")
async def get_rejected_orders(
    run_id: str,
    limit: int = 1000,
    offset: int = 0
) -> Dict[str, Any]:
    """Get rejected/denied orders for a specific backtest result with analysis.
    
    Args:
        run_id: Backtest run ID
        limit: Maximum number of rejected orders to return (default: 1000, max: 10000)
        offset: Number of rejected orders to skip (default: 0)
    
    Returns:
        Dictionary with 'rejected_orders' array (paginated), 'analysis', and pagination info
    """
    # Cap limit to prevent excessive memory usage
    limit = min(limit, 10000)
    limit = max(limit, 1)  # At least 1
    # Try report results first (only report mode has order details)
    # Use same path resolution as get_report_result
    report_paths = [
        Path(f"backend/backtest_results/report/{run_id}"),
        Path(f"/app/backend/backtest_results/report/{run_id}"),
    ]
    
    report_dir = None
    for path in report_paths:
        if path.exists():
            report_dir = path
            break
    
    if not report_dir or not report_dir.exists():
        raise HTTPException(status_code=404, detail=f"Report result not found: {run_id}")
    
    rejected_orders = []
    # First, try to get timestamps from timeline
    timeline_file = report_dir / "timeline.json"
    timeline_orders_map = {}
    if timeline_file.exists():
        try:
            loop = asyncio.get_event_loop()
            def load_timeline():
                with open(timeline_file, 'r') as f:
                    return json.load(f)
            timeline_data = await loop.run_in_executor(None, load_timeline)
            if isinstance(timeline_data, list):
                # Map order IDs to their timestamps from timeline
                for event in timeline_data:
                    if event.get('event') == 'Order' and event.get('data'):
                        order_id = event['data'].get('id')
                        if order_id:
                            timeline_orders_map[order_id] = event.get('ts', '')
        except (json.JSONDecodeError, IOError, OSError, Exception) as e:
            print(f"Error loading timeline for rejected orders: {e}")
            pass
    
    orders_file = report_dir / "orders.json"
    if orders_file.exists():
        try:
            loop = asyncio.get_event_loop()
            orders_data = await loop.run_in_executor(None, lambda: json.loads(orders_file.read_text()))
            if isinstance(orders_data, list):
                rejected_orders = []
                for order in orders_data:
                    if order.get('status') in ['denied', 'rejected']:
                        order_with_timestamp = order.copy()
                        # Add timestamp from timeline if available
                        order_id = order.get('id')
                        if order_id in timeline_orders_map:
                            order_with_timestamp['timestamp'] = timeline_orders_map[order_id]
                        rejected_orders.append(order_with_timestamp)
                # Sort by timestamp if available
                rejected_orders.sort(key=lambda x: x.get('timestamp', ''))
        except (json.JSONDecodeError, IOError, OSError, Exception) as e:
            print(f"Error loading rejected orders: {e}")
            pass
    
    # Analyze rejection patterns
    analysis = {
        'total_rejected': len(rejected_orders),
        'by_side': {},
        'by_price_range': {},
        'common_patterns': []
    }
    
    # Calculate analysis on ALL rejected orders (before pagination)
    total_rejected = len(rejected_orders)
    
    if rejected_orders:
        # Count by side
        buy_rejected = sum(1 for o in rejected_orders if o.get('side') == 'buy')
        sell_rejected = sum(1 for o in rejected_orders if o.get('side') == 'sell')
        analysis['by_side'] = {
            'buy': buy_rejected,
            'sell': sell_rejected
        }
        analysis['total_rejected'] = total_rejected
        
        # Analyze price ranges (if prices available)
        if rejected_orders and 'price' in rejected_orders[0]:
            prices = [o['price'] for o in rejected_orders if 'price' in o]
            if prices:
                min_price = min(prices)
                max_price = max(prices)
                analysis['price_range'] = {
                    'min': min_price,
                    'max': max_price,
                    'avg': sum(prices) / len(prices)
                }
    
    # Paginate rejected orders
    paginated_rejected = rejected_orders[offset:offset + limit]
    
    return {
        'rejected_orders': paginated_rejected,
        'analysis': analysis,
        'total': total_rejected,
        'limit': limit,
        'offset': offset,
        'has_more': offset + limit < total_rejected
    }


@app.get("/api/backtest/results/{run_id}/report")
async def get_report_result(
    run_id: str,
    timeline_limit: int = 5000,
    timeline_offset: int = 0
) -> Dict[str, Any]:
    """Get full report result including timeline and orders.
    
    Args:
        run_id: Backtest run ID
        timeline_limit: Maximum number of timeline events to return (default: 5000, max: 50000)
        timeline_offset: Number of timeline events to skip (default: 0)
    
    Returns:
        Dictionary with report data, paginated timeline, and orders
    """
    # Cap limit to prevent excessive memory usage
    timeline_limit = min(timeline_limit, 50000)
    timeline_limit = max(timeline_limit, 1)  # At least 1
    # Try multiple possible paths for Docker compatibility
    report_paths = [
        Path(f"backend/backtest_results/report/{run_id}"),
        Path(f"/app/backend/backtest_results/report/{run_id}"),
    ]
    
    report_dir = None
    for path in report_paths:
        if path.exists():
            report_dir = path
            break
    
    if not report_dir or not report_dir.exists():
        raise HTTPException(status_code=404, detail=f"Report result not found: {run_id}")
    
    result = {}
    
    # Load summary
    summary_file = report_dir / "summary.json"
    if summary_file.exists():
        with open(summary_file, 'r') as f:
            result = json.load(f)
    
    # Load timeline if exists (with pagination)
    timeline_file = report_dir / "timeline.json"
    if timeline_file.exists():
        try:
            loop = asyncio.get_event_loop()
            def load_timeline():
                with open(timeline_file, 'r') as f:
                    return json.load(f)
            timeline_data = await loop.run_in_executor(None, load_timeline)
            if isinstance(timeline_data, list):
                total_timeline = len(timeline_data)
                # Paginate timeline
                paginated_timeline = timeline_data[timeline_offset:timeline_offset + timeline_limit]
                result['timeline'] = paginated_timeline
                result['timeline_pagination'] = {
                    'total': total_timeline,
                    'limit': timeline_limit,
                    'offset': timeline_offset,
                    'has_more': timeline_offset + timeline_limit < total_timeline
                }
            else:
                result['timeline'] = []
                result['timeline_pagination'] = {'total': 0, 'limit': timeline_limit, 'offset': timeline_offset, 'has_more': False}
        except (json.JSONDecodeError, IOError, OSError):
            result['timeline'] = []
            result['timeline_pagination'] = {'total': 0, 'limit': timeline_limit, 'offset': timeline_offset, 'has_more': False}
    
    # Load orders if exists
    orders_file = report_dir / "orders.json"
    if orders_file.exists():
        try:
            with open(orders_file, 'r') as f:
                orders_data = json.load(f)
                result['orders'] = orders_data if isinstance(orders_data, list) else []
        except (json.JSONDecodeError, IOError, OSError):
            result['orders'] = []
    
    return result


@app.get("/api/backtest/results/{run_id}/ticks")
async def get_tick_data(run_id: str):
    """Get tick data for a specific backtest result."""
    # Check frontend public directory first (where ticks are exported)
    tick_paths = [
        Path(f"frontend/public/tickdata/{run_id}.json"),
        Path(f"/app/frontend/public/tickdata/{run_id}.json"),
    ]
    
    for tick_file in tick_paths:
        if tick_file.exists():
            return FileResponse(tick_file, media_type="application/json")
    
    # Check backend results directory as fallback
    backend_tick_paths = [
        Path(f"backend/backtest_results/report/{run_id}/ticks.json"),
        Path(f"/app/backend/backtest_results/report/{run_id}/ticks.json"),
    ]
    
    for tick_file_backend in backend_tick_paths:
        if tick_file_backend.exists():
            return FileResponse(tick_file_backend, media_type="application/json")
    
    raise HTTPException(status_code=404, detail=f"Tick data not found for run_id: {run_id}")


@app.get("/api/datasets")
async def get_datasets() -> List[str]:
    """Scan data_downloads folder for available datasets (deprecated - use check-data instead)."""
    datasets = []
    data_dir = Path(os.getenv("UNIFIED_CLOUD_LOCAL_PATH", "/app/data_downloads"))
    
    if data_dir.exists():
        raw_tick_dir = data_dir / "raw_tick_data" / "by_date"
        if raw_tick_dir.exists():
            for day_dir in raw_tick_dir.iterdir():
                if day_dir.is_dir() and day_dir.name.startswith("day-"):
                    datasets.append(day_dir.name)
    
    return sorted(datasets)


@app.post("/api/backtest/check-data")
async def check_data_availability(request: DataCheckRequest) -> Dict[str, Any]:
    """
    Check data availability for a time window and instrument.
    
    Auto-detects dataset from time window and validates:
    - Trades data (required for backtest)
    - Book snapshot data (optional, depends on snapshot_mode)
    
    Returns validation result with clear messages about what's missing.
    """
    try:
        # Parse timestamps
        start = validate_iso8601(request.start)
        end = validate_iso8601(request.end)
        
        # Get instrument ID from request
        instrument_id = request.instrument_id
        
        # If instrument_id looks like a simple symbol (e.g., "BTCUSDT"), 
        # try to get the full instrument ID from config
        # For now, use instrument_id directly - frontend should send full ID from config
        
        # Check data availability
        try:
            checker = DataAvailabilityChecker(data_source=request.data_source)
            result = await checker.check_data_availability(
                instrument_id=instrument_id,
                start=start,
                end=end,
                snapshot_mode=request.snapshot_mode
            )
            
            return result
        except ValueError as ve:
            # Configuration errors (e.g., missing bucket, credentials)
            # Return as validation result with error instead of 500
            import traceback
            error_detail = str(ve)
            print(f"Configuration error in check_data_availability: {error_detail}")
            print(traceback.format_exc())
            
            # Return error result instead of raising HTTPException
            date_obj = start.date() if hasattr(start, 'date') else start.date()
            date_str = date_obj.strftime("%Y-%m-%d")
            return {
                "valid": False,
                "has_trades": False,
                "has_book": False,
                "date": date_str,
                "dataset": f"day-{date_str}",
                "source": request.data_source,
                "messages": [],
                "errors": [f"❌ GCS Configuration Error: {error_detail}"],
                "warnings": []
            }
        except Exception as checker_error:
            # Other errors - log and return error result
            import traceback
            error_detail = f"Error checking data availability: {str(checker_error)}"
            print(f"Error in check_data_availability: {error_detail}")
            print(traceback.format_exc())
            
            # Return error result instead of raising HTTPException
            date_obj = start.date() if hasattr(start, 'date') else start.date()
            date_str = date_obj.strftime("%Y-%m-%d")
            return {
                "valid": False,
                "has_trades": False,
                "has_book": False,
                "date": date_str,
                "dataset": f"day-{date_str}",
                "source": request.data_source,
                "messages": [],
                "errors": [f"❌ Error: {error_detail}"],
                "warnings": []
            }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        import traceback
        error_detail = f"Error checking data availability: {str(e)}"
        print(f"Error in check_data_availability endpoint: {error_detail}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_detail)


@app.get("/api/configs")
async def get_configs() -> List[str]:
    """List available config files."""
    configs = []
    config_dir = _get_configs_dir()
    
    if config_dir and config_dir.exists():
        for config_file in config_dir.glob("*.json"):
            configs.append(config_file.name)
    
    return sorted(configs)


@app.get("/api/instruments/venues")
async def get_venues() -> Dict[str, Any]:
    """
    Get list of available venues grouped by category.
    Returns all venues from registry immediately (fast, like before refactoring).
    """
    # Import registry config directly to avoid any import issues
    from backend.instruments.registry import VENUES_CONFIG
    
    # Build venue lists directly from config (fast, no function calls)
    cefi_venues = [
        {
            "code": code,
            "name": info["name"],
            "types": info["types"],
        }
        for code, info in VENUES_CONFIG.get("cefi", {}).items()
    ]
    
    tradfi_venues = [
        {
            "code": code,
            "name": info["name"],
            "types": info["types"],
        }
        for code, info in VENUES_CONFIG.get("tradfi", {}).items()
    ]
    
    return {
        "cefi": cefi_venues,
        "tradfi": tradfi_venues,
    }


@app.get("/api/instruments/types/{venue_code}")
async def get_instrument_types(venue_code: str) -> Dict[str, Any]:
    """Get available instrument types for a venue."""
    from backend.instruments.registry import get_instrument_types_for_venue
    
    types = get_instrument_types_for_venue(venue_code.upper())
    return {
        "venue_code": venue_code.upper(),
        "types": types,
    }


@app.get("/api/instruments/list/{venue_code}/{product_type}")
async def get_instruments(venue_code: str, product_type: str) -> Dict[str, Any]:
    """
    Get available instruments for a venue and product type.
    Returns registry instruments immediately (fast).
    GCS filtering is optional and non-blocking.
    """
    from backend.instruments.registry import (
        get_common_instruments,
        convert_to_gcs_format,
        convert_to_nautilus_format,
        get_config_instrument_id
    )
    import os
    
    venue_code_upper = venue_code.upper()
    product_type_upper = product_type.upper()
    
    # Get instruments from registry immediately (fast path)
    common = get_common_instruments(venue_code_upper, product_type_upper)
    
    # Build instrument list from registry
    instruments = []
    for symbol in common:
        gcs_id = convert_to_gcs_format(venue_code_upper, product_type_upper, symbol)
        nautilus_id = convert_to_nautilus_format(venue_code_upper, product_type_upper, symbol)
        config_id = get_config_instrument_id(venue_code_upper, product_type_upper, symbol)
        
        instruments.append({
            "symbol": symbol,
            "gcs_id": gcs_id,
            "nautilus_id": nautilus_id,
            "config_id": config_id,
        })
    
    # Optionally filter by GCS availability (non-blocking)
    bucket_name = os.getenv("UNIFIED_CLOUD_SERVICES_GCS_BUCKET")
    if bucket_name and instruments:
        try:
            from backend.data.loader import UCSDataLoader
            from unified_cloud_services.domain.standardized_service import StandardizedDomainCloudService
            
            ucs_loader = UCSDataLoader(bucket_name=bucket_name)
            standardized_service = StandardizedDomainCloudService(
                domain="market_data",
                cloud_target=ucs_loader.target
            )
            
            # Quick check - limit results for speed
            all_files = standardized_service.list_gcs_files(prefix="raw_tick_data/by_date/", max_results=200)
            
            # Build set of existing instrument IDs from GCS
            existing_instruments = set()
            for file_info in all_files:
                filename = file_info['name'].split('/')[-1]
                if filename.endswith('.parquet'):
                    file_instrument_id = filename[:-8]  # Remove .parquet
                    existing_instruments.add(file_instrument_id)
            
            # Filter instruments if we found matches in GCS
            if existing_instruments:
                filtered_instruments = []
                for inst in instruments:
                    if inst["gcs_id"] in existing_instruments:
                        filtered_instruments.append(inst)
                # Only use filtered list if we found matches, otherwise return all
                if filtered_instruments:
                    instruments = filtered_instruments
        except Exception as e:
            # If GCS check fails, return all registry instruments (fallback)
            print(f"Note: Could not check GCS for instruments (non-critical): {e}")
    
    return {
        "venue_code": venue_code_upper,
        "product_type": product_type_upper,
        "instruments": instruments,
    }


@app.get("/api/configs/{config_name}")
async def get_config(config_name: str) -> Dict[str, Any]:
    """Get a specific config file content."""
    config_file = _resolve_config_path(config_name)
    
    if not config_file or not config_file.exists():
        raise HTTPException(status_code=404, detail=f"Config not found: {config_name}")
    
    with open(config_file, 'r') as f:
        return json.load(f)


@app.post("/api/configs")
async def save_config(request: Dict[str, Any]):
    """Save a config file."""
    name = request.get("name")
    config = request.get("config")
    
    if not name or not config:
        raise HTTPException(status_code=400, detail="Missing 'name' or 'config' in request body")
    
    config_dir = _get_configs_dir()
    
    # If no existing directory found, try to create the first possible path
    if config_dir is None:
        config_dir = Path("external/data_downloads/configs")
    
    config_dir.mkdir(parents=True, exist_ok=True)
    
    config_file = config_dir / name
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    return {"status": "saved", "path": str(config_file)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

