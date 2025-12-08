"""Mount status checking utilities for GCS FUSE."""
import os
from pathlib import Path
from typing import Dict, Any


def check_mount_status() -> Dict[str, Any]:
    """
    Check if /app/data_downloads is mounted via FUSE or local volume.
    
    Returns:
        Dictionary with mount status information
    """
    mount_point = Path("/app/data_downloads")
    use_fuse = os.getenv("USE_GCS_FUSE", "false").lower() == "true"
    gcs_bucket = os.getenv("GCS_FUSE_BUCKET", "")
    
    status = {
        "mounted": False,
        "mount_type": "local",
        "fuse_enabled": use_fuse,
        "gcs_bucket": gcs_bucket if use_fuse else None,
        "path_exists": mount_point.exists(),
        "path_readable": False,
        "file_count": 0,
    }
    
    if not mount_point.exists():
        return status
    
    # Check if it's a FUSE mount by checking /proc/mounts
    try:
        with open("/proc/mounts", "r") as f:
            mounts = f.read()
            if "gcsfuse" in mounts and str(mount_point) in mounts:
                status["mount_type"] = "gcsfuse"
                status["mounted"] = True
            elif str(mount_point) in mounts:
                status["mount_type"] = "local"
                status["mounted"] = True
    except Exception:
        pass
    
    # Check if path is readable and count files
    try:
        if mount_point.is_dir():
            status["path_readable"] = True
            # Count files (limit to avoid performance issues)
            try:
                files = list(mount_point.rglob("*"))[:100]
                status["file_count"] = len(files)
            except Exception:
                pass
    except Exception:
        pass
    
    return status

