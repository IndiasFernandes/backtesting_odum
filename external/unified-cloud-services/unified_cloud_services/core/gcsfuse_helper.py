"""
GCS FUSE Helper

Programmatic helper for checking GCS FUSE availability and mounting status.
Provides guidance for users who haven't set up GCS FUSE.

Usage:
    from unified_cloud_services.core.gcsfuse_helper import GCSFuseHelper
    
    helper = GCSFuseHelper()
    
    # Check if gcsfuse is available
    if helper.is_gcsfuse_installed():
        print("gcsfuse is ready")
    else:
        helper.print_install_instructions()
    
    # Get mount path for a bucket
    mount_path = helper.get_mount_path("market-data-tick-central-element-323112")
    
    # Check if a bucket is mounted
    if helper.is_bucket_mounted("market-data-tick-central-element-323112"):
        print("Bucket is accessible via FUSE")
"""

import logging
import os
import shutil
import subprocess
import platform
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class GCSFuseHelper:
    """Helper class for GCS FUSE operations."""

    # Common mount point patterns (in order of priority)
    MOUNT_PATTERNS = [
        "{env_var}",  # GCS_FUSE_MOUNT_PATH environment variable
        "/mnt/gcs/{bucket}",  # Linux standard
        "/gcs/{bucket}",  # Alternative Linux
        "{home}/gcs/{bucket}",  # User home directory
        "/mnt/disks/gcs/{bucket}",  # GCE default
    ]

    def __init__(self):
        self.system = platform.system().lower()
        self.home = str(Path.home())

    def is_gcsfuse_installed(self) -> bool:
        """Check if gcsfuse binary is available."""
        return shutil.which("gcsfuse") is not None

    def get_gcsfuse_version(self) -> Optional[str]:
        """Get installed gcsfuse version."""
        if not self.is_gcsfuse_installed():
            return None
        try:
            result = subprocess.run(
                ["gcsfuse", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip() or result.stderr.strip()
        except Exception:
            return None

    def is_bucket_mounted(self, bucket: str) -> bool:
        """Check if a GCS bucket is mounted via FUSE."""
        mount_path = self.get_mount_path(bucket)
        if mount_path is None:
            return False
        return mount_path.exists() and mount_path.is_dir()

    def get_mount_path(self, bucket: str) -> Optional[Path]:
        """
        Get the mount path for a GCS bucket.
        
        Checks common mount locations in order of priority.
        Returns the first existing path found, or None if not mounted.
        """
        # Check environment variable first
        env_mount = os.environ.get("GCS_FUSE_MOUNT_PATH")
        if env_mount:
            env_path = Path(env_mount)
            if env_path.exists():
                # If env var points to bucket-specific path, use it directly
                # Otherwise, append bucket name
                if bucket in str(env_path):
                    return env_path
                else:
                    bucket_path = env_path / bucket
                    if bucket_path.exists():
                        return bucket_path
                    # Check if env_path itself is the mount (no bucket subdir)
                    if env_path.exists():
                        return env_path

        # Check common mount patterns
        for pattern in self.MOUNT_PATTERNS[1:]:  # Skip env_var, already checked
            path_str = pattern.format(bucket=bucket, home=self.home)
            path = Path(path_str)
            if path.exists() and path.is_dir():
                return path

        return None

    def get_recommended_mount_path(self, bucket: str) -> Path:
        """Get the recommended mount path for this system."""
        if self.system == "darwin":  # macOS
            return Path.home() / "gcs" / bucket
        else:  # Linux
            return Path("/mnt/gcs") / bucket

    def mount_bucket(
        self, bucket: str, mount_path: Optional[Path] = None
    ) -> tuple[bool, str]:
        """
        Mount a GCS bucket using gcsfuse.
        
        Args:
            bucket: GCS bucket name
            mount_path: Optional mount path (uses recommended if not specified)
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        if not self.is_gcsfuse_installed():
            return False, "gcsfuse is not installed. Run: ./scripts/setup_gcsfuse.sh"

        if mount_path is None:
            mount_path = self.get_recommended_mount_path(bucket)

        # Create mount directory
        try:
            mount_path.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            return False, f"Permission denied creating {mount_path}. Try with sudo."

        # Check if already mounted
        if self.is_bucket_mounted(bucket):
            return True, f"Bucket already mounted at {mount_path}"

        # Run gcsfuse
        try:
            result = subprocess.run(
                ["gcsfuse", "--implicit-dirs", bucket, str(mount_path)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                logger.info(f"✅ Mounted {bucket} at {mount_path}")
                return True, f"Successfully mounted {bucket} at {mount_path}"
            else:
                return False, f"gcsfuse failed: {result.stderr}"
        except subprocess.TimeoutExpired:
            return False, "gcsfuse timed out. Check your network and authentication."
        except Exception as e:
            return False, f"Failed to run gcsfuse: {e}"

    def unmount_bucket(self, bucket: str) -> tuple[bool, str]:
        """Unmount a GCS bucket."""
        mount_path = self.get_mount_path(bucket)
        if mount_path is None:
            return True, "Bucket is not mounted"

        try:
            # Try fusermount first (Linux), then umount (macOS)
            if self.system == "linux":
                result = subprocess.run(
                    ["fusermount", "-u", str(mount_path)],
                    capture_output=True,
                    text=True,
                )
            else:
                result = subprocess.run(
                    ["umount", str(mount_path)],
                    capture_output=True,
                    text=True,
                )

            if result.returncode == 0:
                logger.info(f"✅ Unmounted {mount_path}")
                return True, f"Successfully unmounted {mount_path}"
            else:
                return False, f"Unmount failed: {result.stderr}"
        except Exception as e:
            return False, f"Failed to unmount: {e}"

    def get_install_instructions(self) -> str:
        """Get installation instructions for the current platform."""
        if self.system == "darwin":
            return """
GCS FUSE Installation (macOS):
==============================
⚠️  gcsfuse does not provide official macOS binaries.

RECOMMENDED: Use Docker (Linux container)
------------------------------------------
1. Install Docker Desktop: https://www.docker.com/products/docker-desktop/

2. Start containers:
   cd unified-cloud-services
   docker compose up -d

3. Run commands in container:
   docker compose run --rm app bash
   # Inside container, gcsfuse is pre-installed
   ucs-setup

ALTERNATIVE: Use without gcsfuse
---------------------------------
The unified-cloud-services package works without gcsfuse.
It will use GCS API directly (slower but functional).

   export UCS_SKIP_GCSFUSE_CHECK=1

ADVANCED: Build from source
----------------------------
See: https://github.com/GoogleCloudPlatform/gcsfuse
(Not recommended - requires Go toolchain and FUSE development)
"""
        elif self.system == "linux":
            return """
GCS FUSE Installation (Linux):
==============================
1. Add Google Cloud apt repository:
   export GCSFUSE_REPO=gcsfuse-$(lsb_release -c -s)
   echo "deb https://packages.cloud.google.com/apt $GCSFUSE_REPO main" | sudo tee /etc/apt/sources.list.d/gcsfuse.list
   curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -

2. Install gcsfuse:
   sudo apt-get update
   sudo apt-get install -y gcsfuse

3. Run our setup script:
   ./scripts/setup_gcsfuse.sh market-data-tick-central-element-323112

Or use the Python helper:
   from unified_cloud_services.core.gcsfuse_helper import GCSFuseHelper
   helper = GCSFuseHelper()
   helper.mount_bucket("market-data-tick-central-element-323112")
"""
        else:
            return """
GCS FUSE Installation:
======================
See: https://github.com/GoogleCloudPlatform/gcsfuse/blob/master/docs/installing.md
"""

    def print_install_instructions(self):
        """Print installation instructions to console."""
        print(self.get_install_instructions())

    def get_status(self, buckets: Optional[list[str]] = None) -> dict:
        """
        Get comprehensive GCS FUSE status.
        
        Args:
            buckets: Optional list of bucket names to check
        
        Returns:
            Status dictionary with installation and mount information
        """
        if buckets is None:
            buckets = [
                "market-data-tick-central-element-323112",
                "instruments-store-cefi-central-element-323112",
            ]

        status = {
            "gcsfuse_installed": self.is_gcsfuse_installed(),
            "gcsfuse_version": self.get_gcsfuse_version(),
            "system": self.system,
            "env_var": os.environ.get("GCS_FUSE_MOUNT_PATH"),
            "buckets": {},
        }

        for bucket in buckets:
            mount_path = self.get_mount_path(bucket)
            status["buckets"][bucket] = {
                "mounted": self.is_bucket_mounted(bucket),
                "mount_path": str(mount_path) if mount_path else None,
                "recommended_path": str(self.get_recommended_mount_path(bucket)),
            }

        return status

    def print_status(self, buckets: Optional[list[str]] = None):
        """Print GCS FUSE status to console."""
        status = self.get_status(buckets)

        print("\n" + "=" * 50)
        print("GCS FUSE Status")
        print("=" * 50)

        if status["gcsfuse_installed"]:
            print(f"✅ gcsfuse installed: {status['gcsfuse_version']}")
        else:
            print("❌ gcsfuse NOT installed")
            self.print_install_instructions()
            return

        print(f"📍 System: {status['system']}")
        print(f"🔧 GCS_FUSE_MOUNT_PATH: {status['env_var'] or '(not set)'}")

        print("\n📦 Bucket Status:")
        for bucket, info in status["buckets"].items():
            if info["mounted"]:
                print(f"  ✅ {bucket}")
                print(f"     Mount: {info['mount_path']}")
            else:
                print(f"  ❌ {bucket} (not mounted)")
                print(f"     Recommended: {info['recommended_path']}")

        print("=" * 50 + "\n")


# Convenience functions
def check_gcsfuse_available() -> bool:
    """Quick check if gcsfuse is available."""
    return GCSFuseHelper().is_gcsfuse_installed()


def get_bucket_mount_path(bucket: str) -> Optional[Path]:
    """Get mount path for a bucket (or None if not mounted)."""
    return GCSFuseHelper().get_mount_path(bucket)


def ensure_bucket_mounted(bucket: str) -> tuple[bool, str]:
    """Ensure a bucket is mounted, mounting if necessary."""
    helper = GCSFuseHelper()
    if helper.is_bucket_mounted(bucket):
        path = helper.get_mount_path(bucket)
        return True, f"Bucket already mounted at {path}"
    return helper.mount_bucket(bucket)

