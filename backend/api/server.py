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
    from backend.backtest_engine import BacktestEngine
    from backend.catalog_manager import CatalogManager
    from backend.config_loader import ConfigLoader
    from backend.utils.validation import validate_iso8601
    from backend.api.mount_status import check_mount_status
    from backend.utils.log_capture import get_log_capture
except ImportError as e:
    import sys
    print(f"Error importing backend modules: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    raise

app = FastAPI(title="Odum Trader Backtest API")

# Store active backtest tasks and their log queues (thread-safe queues)
_active_backtests: Dict[str, queue.Queue] = {}

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
    dataset: str
    config: str
    start: str
    end: str
    fast: bool = False
    report: bool = False
    export_ticks: bool = False
    snapshot_mode: str = "both"


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
            
            send_step("Initializing backtest engine...")
            
            # Initialize engine
            catalog_manager = CatalogManager()
            engine = BacktestEngine(config_loader, catalog_manager)
            
            send_step("Running backtest...")
            
            # Run backtest
            result = engine.run(
                instrument=request.instrument,
                dataset=request.dataset,
                start=start,
                end=end,
                snapshot_mode=request.snapshot_mode,
                fast_mode=request.fast,
                export_ticks=request.export_ticks,
                close_positions=True  # Default to closing positions
            )
            
            send_step("Saving results...")
            
            # Save results to disk (same as CLI)
            from backend.results import ResultSerializer
            if request.fast:
                output_dir = Path("backend/backtest_results/fast")
                ResultSerializer.save_fast(result, output_dir)
            elif request.report or not request.fast:
                # Report mode (explicit or default when fast=False)
                output_dir = Path("backend/backtest_results/report")
                ResultSerializer.save_report(result, output_dir)
                print(f"Report mode result saved to: {output_dir}/{result['run_id']}/summary.json")
            
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
            
            # Initialize engine
            catalog_manager = CatalogManager()
            engine = BacktestEngine(config_loader, catalog_manager)
            
            # Run backtest
            result = engine.run(
                instrument=request.instrument,
                dataset=request.dataset,
                start=start,
                end=end,
                snapshot_mode=request.snapshot_mode,
                fast_mode=request.fast,
                export_ticks=request.export_ticks,
                close_positions=True  # Default to closing positions
            )
            
            # Save results to disk (same as CLI)
            from backend.results import ResultSerializer
            if request.fast:
                output_dir = Path("backend/backtest_results/fast")
                ResultSerializer.save_fast(result, output_dir)
            elif request.report or not request.fast:
                # Report mode (explicit or default when fast=False)
                output_dir = Path("backend/backtest_results/report")
                ResultSerializer.save_report(result, output_dir)
                print(f"Report mode result saved to: {output_dir}/{result['run_id']}/summary.json")
            
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
    """Load fast results synchronously (called from async endpoint). Optimized for speed."""
    results = []
    
    # Only scan fast results (limit to most recent 100 files)
    # Try multiple possible paths for Docker compatibility
    possible_paths = [
        Path("backend/backtest_results/fast"),  # Relative from project root
        Path("/app/backend/backtest_results/fast"),  # Docker absolute path
        Path(__file__).parent.parent.parent / "backtest_results" / "fast",  # Relative from this file
    ]
    
    fast_dir = None
    for path in possible_paths:
        if path.exists():
            fast_dir = path
            break
    
    if not fast_dir or not fast_dir.exists():
        # Return empty list if directory doesn't exist
        return results
    
    try:
        fast_files = sorted(
            [f for f in fast_dir.glob("*.json") if f.is_file()],
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:100]  # Limit to 100 most recent
        
        for result_file in fast_files:
            try:
                with open(result_file, 'r') as f:
                    data = json.load(f)
                    # Only include fast mode results
                    if data.get('mode') == 'fast':
                        results.append(data)
            except (json.JSONDecodeError, IOError, OSError, KeyError) as e:
                # Skip malformed files
                continue
    except (OSError, PermissionError) as e:
        # If we can't read the directory, return empty list
        # The error will be handled by the endpoint
        raise
    
    # Sort by run_id (which contains timestamp) descending to show newest first
    results.sort(key=lambda x: x.get('run_id', ''), reverse=True)
    
    return results

def _load_results_report() -> List[Dict[str, Any]]:
    """Load report results synchronously (called from async endpoint). Returns lightweight metadata only."""
    results = []
    
    # Scan report results (limit to most recent 50 directories for performance)
    # Try multiple possible paths for Docker compatibility
    possible_paths = [
        Path("backend/backtest_results/report"),  # Relative from project root
        Path("/app/backend/backtest_results/report"),  # Docker absolute path
        Path(__file__).parent.parent.parent / "backtest_results" / "report",  # Relative from this file
    ]
    
    report_dir = None
    for path in possible_paths:
        if path.exists():
            report_dir = path
            break
    
    if not report_dir or not report_dir.exists():
        return results
    
    try:
        report_dirs = sorted(
            [d for d in report_dir.iterdir() if d.is_dir()],
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:50]  # Limit to 50 most recent
        
        for run_dir in report_dirs:
            summary_file = run_dir / "summary.json"
            if summary_file.exists():
                try:
                    with open(summary_file, 'r') as f:
                        data = json.load(f)
                        # Return lightweight version with just metadata and summary
                        results.append({
                            "run_id": data.get('run_id'),
                            "mode": "report",
                            "instrument": data.get('instrument'),
                            "dataset": data.get('dataset'),
                            "start": data.get('start'),
                            "end": data.get('end'),
                            "summary": data.get('summary', {}),
                            "metadata": data.get('metadata', {})
                        })
                except (json.JSONDecodeError, IOError, OSError, KeyError):
                    continue
    except (OSError, PermissionError):
        raise
    
    # Sort by run_id (which contains timestamp) descending to show newest first
    results.sort(key=lambda x: x.get('run_id', ''), reverse=True)
    
    return results


@app.get("/api/backtest/results")
@app.get("/api/backtest/results/fast")
async def get_results() -> List[Dict[str, Any]]:
    """List all fast backtest results. Optimized for fast loading."""
    try:
        # Run file I/O in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, _load_results_fast)
        return results
    except Exception as e:
        # Log the error and return a proper HTTP error response
        import traceback
        error_detail = f"Error loading fast backtest results: {str(e)}"
        print(f"Error in get_results: {error_detail}")
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


@app.get("/api/backtest/results/{run_id}")
async def get_result(run_id: str) -> Dict[str, Any]:
    """Get a specific backtest result (fast or report)."""
    # Try multiple possible paths for Docker compatibility
    fast_paths = [
        Path(f"backend/backtest_results/fast/{run_id}.json"),
        Path(f"/app/backend/backtest_results/fast/{run_id}.json"),
    ]
    
    for fast_file in fast_paths:
        if fast_file.exists():
            try:
                with open(fast_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError, OSError):
                continue
    
    # Try report results
    report_paths = [
        Path(f"backend/backtest_results/report/{run_id}/summary.json"),
        Path(f"/app/backend/backtest_results/report/{run_id}/summary.json"),
    ]
    
    for report_file in report_paths:
        if report_file.exists():
            try:
                with open(report_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError, OSError):
                continue
    
    raise HTTPException(status_code=404, detail=f"Result not found: {run_id}")


@app.get("/api/backtest/results/{run_id}/report")
async def get_report_result(run_id: str) -> Dict[str, Any]:
    """Get full report result including timeline and orders."""
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
    
    # Load timeline if exists
    timeline_file = report_dir / "timeline.json"
    if timeline_file.exists():
        try:
            with open(timeline_file, 'r') as f:
                timeline_data = json.load(f)
                result['timeline'] = timeline_data if isinstance(timeline_data, list) else []
        except (json.JSONDecodeError, IOError, OSError):
            result['timeline'] = []
    
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
    """Scan data_downloads folder for available datasets."""
    datasets = []
    data_dir = Path(os.getenv("UNIFIED_CLOUD_LOCAL_PATH", "/app/data_downloads"))
    
    if data_dir.exists():
        raw_tick_dir = data_dir / "raw_tick_data" / "by_date"
        if raw_tick_dir.exists():
            for day_dir in raw_tick_dir.iterdir():
                if day_dir.is_dir() and day_dir.name.startswith("day-"):
                    datasets.append(day_dir.name)
    
    return sorted(datasets)


@app.get("/api/configs")
async def get_configs() -> List[str]:
    """List available config files."""
    configs = []
    config_dir = _get_configs_dir()
    
    if config_dir and config_dir.exists():
        for config_file in config_dir.glob("*.json"):
            configs.append(config_file.name)
    
    return sorted(configs)


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

