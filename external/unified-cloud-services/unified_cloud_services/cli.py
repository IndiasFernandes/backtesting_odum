"""
unified-cloud-services CLI

Provides command-line tools for setup and management:

    ucs-setup     - Install gcsfuse and set up GCS FUSE mounting
    ucs-status    - Show GCS FUSE status and mount points
    ucs-mount     - Mount a GCS bucket
    ucs-unmount   - Unmount a GCS bucket

Usage after pip install:
    $ ucs-setup                              # Install gcsfuse (interactive)
    $ ucs-status                             # Show current status
    $ ucs-mount market-data-tick-...         # Mount specific bucket
    $ ucs-unmount market-data-tick-...       # Unmount bucket
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

from unified_cloud_services.core.gcsfuse_helper import GCSFuseHelper


def setup_gcsfuse():
    """
    CLI entry point: ucs-setup
    
    Installs gcsfuse and sets up GCS FUSE mounting.
    """
    parser = argparse.ArgumentParser(
        prog="ucs-setup",
        description="Install gcsfuse and set up GCS FUSE mounting for fast I/O",
    )
    parser.add_argument(
        "bucket",
        nargs="?",
        default="market-data-tick-central-element-323112",
        help="GCS bucket to mount (default: market-data-tick-central-element-323112)",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check if gcsfuse is installed, don't install",
    )
    parser.add_argument(
        "--skip-mount",
        action="store_true",
        help="Install gcsfuse but don't mount any buckets",
    )
    args = parser.parse_args()

    helper = GCSFuseHelper()
    
    print("\n" + "=" * 60)
    print("🚀 unified-cloud-services GCS FUSE Setup")
    print("=" * 60 + "\n")

    # Check current status
    if helper.is_gcsfuse_installed():
        print(f"✅ gcsfuse is already installed: {helper.get_gcsfuse_version()}")
        
        if args.check_only:
            helper.print_status([args.bucket])
            return 0
    else:
        print("❌ gcsfuse is NOT installed\n")
        
        if args.check_only:
            print("Run 'ucs-setup' (without --check-only) to install.")
            return 1
        
        # Try to install
        print("Attempting to install gcsfuse...\n")
        success = _install_gcsfuse(helper)
        
        if not success:
            print("\n" + "=" * 60)
            print("⚠️  Automatic installation failed. Please install manually:")
            print("=" * 60)
            helper.print_install_instructions()
            return 1

    # Mount bucket if requested
    if not args.skip_mount:
        print(f"\n📁 Mounting bucket: {args.bucket}")
        success, msg = helper.mount_bucket(args.bucket)
        print(f"   {msg}")
        
        if success:
            # Set environment variable hint
            mount_path = helper.get_mount_path(args.bucket) or helper.get_recommended_mount_path(args.bucket)
            print(f"\n💡 Add to your shell config (.bashrc/.zshrc):")
            print(f'   export GCS_FUSE_MOUNT_PATH="{mount_path}"')

    # Show final status
    print("\n")
    helper.print_status([args.bucket])
    
    return 0


def _install_gcsfuse(helper: GCSFuseHelper) -> bool:
    """Attempt to install gcsfuse based on the system."""
    system = helper.system
    
    # Environment to skip slow Homebrew auto-update
    brew_env = os.environ.copy()
    brew_env["HOMEBREW_NO_AUTO_UPDATE"] = "1"
    brew_env["HOMEBREW_NO_INSTALL_CLEANUP"] = "1"
    
    try:
        if system == "darwin":
            # macOS: gcsfuse doesn't provide official macOS binaries
            # Recommend Docker instead
            print("🍎 macOS detected")
            print("\n" + "=" * 60)
            print("⚠️  gcsfuse Native macOS Support")
            print("=" * 60)
            print("\ngcsfuse does not provide official macOS binaries.")
            print("For macOS, we recommend using Docker (Linux container).\n")
            
            # Check if Docker is available
            docker_available = subprocess.run(
                ["which", "docker"], capture_output=True
            ).returncode == 0
            
            if docker_available:
                print("✅ Docker is installed!")
                print("\nRecommended: Use Docker container (Linux environment)")
                print("=" * 60)
                
                # Check Docker disk space
                try:
                    result = subprocess.run(
                        ["docker", "system", "df", "--format", "{{.Type}}\t{{.Size}}\t{{.Reclaimable}}"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        print("\n💾 Docker Disk Usage:")
                        for line in result.stdout.strip().split('\n'):
                            if line.strip():
                                print(f"   {line}")
                except Exception:
                    pass
                
                print("\n⚠️  If build fails with 'not enough free space':")
                print("   Clean Docker disk space:")
                print("   docker system prune -a --volumes")
                print("   # See DOCKER_TROUBLESHOOTING.md for details")
                print("\n1. Start Docker containers:")
                print("   cd unified-cloud-services")
                print("   docker compose up -d")
                print("\n2. Run commands in container:")
                print("   docker compose run --rm app bash")
                print("   # Inside container, gcsfuse is pre-installed")
                print("   ucs-setup")
                print("\n3. Access mounted buckets from host:")
                print("   # Buckets mounted in container at /mnt/gcs/")
                print("   # Access via Docker volume mounts")
                print("\n" + "=" * 60)
            else:
                print("❌ Docker is not installed")
                print("\nOption 1: Install Docker Desktop (Recommended)")
                print("   https://www.docker.com/products/docker-desktop/")
                print("\nOption 2: Build gcsfuse from source (Advanced)")
                print("   See: https://github.com/GoogleCloudPlatform/gcsfuse")
                print("\nOption 3: Use Linux VM or remote Linux machine")
                print("\n" + "=" * 60)
            
            print("\n💡 For local development without Docker:")
            print("   The unified-cloud-services package works without gcsfuse.")
            print("   It will use GCS API directly (slower but functional).")
            print("   Set UCS_SKIP_GCSFUSE_CHECK=1 to disable this check.\n")
            
            return False  # Don't try to install on macOS
                
        elif system == "linux":
            # Linux: Use apt
            print("📦 Installing via apt...")
            
            # Check if apt is available
            if subprocess.run(["which", "apt-get"], capture_output=True).returncode != 0:
                print("❌ apt-get not found. This installer supports Debian/Ubuntu only.")
                print("   For other distributions, please install manually.")
                return False
            
            # This requires sudo, which may prompt for password
            print("   Adding Google Cloud apt repository...")
            print("   (You may be prompted for sudo password)")
            
            # Get distribution codename
            result = subprocess.run(["lsb_release", "-c", "-s"], capture_output=True, text=True)
            if result.returncode != 0:
                print("❌ Could not detect distribution")
                return False
            
            codename = result.stdout.strip()
            gcsfuse_repo = f"gcsfuse-{codename}"
            
            # Add repository and install
            commands = [
                f'echo "deb https://packages.cloud.google.com/apt {gcsfuse_repo} main" | sudo tee /etc/apt/sources.list.d/gcsfuse.list',
                "curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -",
                "sudo apt-get update",
                "sudo apt-get install -y gcsfuse",
            ]
            
            for cmd in commands:
                print(f"   Running: {cmd[:50]}...")
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"❌ Command failed: {result.stderr}")
                    return False
        else:
            print(f"❌ Unsupported system: {system}")
            return False
        
        # Verify installation
        if helper.is_gcsfuse_installed():
            print(f"\n✅ gcsfuse installed successfully: {helper.get_gcsfuse_version()}")
            return True
        else:
            print("\n❌ Installation completed but gcsfuse not found in PATH")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Installation timed out. Try running manually:")
        if system == "darwin":
            print("   brew install --cask macfuse && brew install gcsfuse")
        else:
            print("   sudo apt-get install -y gcsfuse")
        return False
    except Exception as e:
        print(f"❌ Installation error: {e}")
        return False


def print_status():
    """
    CLI entry point: ucs-status
    
    Shows GCS FUSE status and mount points.
    """
    parser = argparse.ArgumentParser(
        prog="ucs-status",
        description="Show GCS FUSE status and mount points",
    )
    parser.add_argument(
        "buckets",
        nargs="*",
        default=[
            "market-data-tick-central-element-323112",
            "instruments-store-cefi-central-element-323112",
        ],
        help="Buckets to check status for",
    )
    args = parser.parse_args()

    helper = GCSFuseHelper()
    helper.print_status(args.buckets)
    
    return 0


def mount_bucket():
    """
    CLI entry point: ucs-mount
    
    Mount a GCS bucket via FUSE.
    """
    parser = argparse.ArgumentParser(
        prog="ucs-mount",
        description="Mount a GCS bucket via FUSE",
    )
    parser.add_argument(
        "bucket",
        help="GCS bucket name to mount",
    )
    parser.add_argument(
        "--path",
        help="Custom mount path (default: auto-detected based on OS)",
    )
    args = parser.parse_args()

    helper = GCSFuseHelper()
    
    if not helper.is_gcsfuse_installed():
        print("❌ gcsfuse is not installed. Run 'ucs-setup' first.")
        return 1
    
    mount_path = Path(args.path) if args.path else None
    success, msg = helper.mount_bucket(args.bucket, mount_path)
    
    if success:
        print(f"✅ {msg}")
        return 0
    else:
        print(f"❌ {msg}")
        return 1


def unmount_bucket():
    """
    CLI entry point: ucs-unmount
    
    Unmount a GCS bucket.
    """
    parser = argparse.ArgumentParser(
        prog="ucs-unmount",
        description="Unmount a GCS bucket",
    )
    parser.add_argument(
        "bucket",
        help="GCS bucket name to unmount",
    )
    args = parser.parse_args()

    helper = GCSFuseHelper()
    success, msg = helper.unmount_bucket(args.bucket)
    
    if success:
        print(f"✅ {msg}")
        return 0
    else:
        print(f"❌ {msg}")
        return 1


# Also provide a main entry point for `python -m unified_cloud_services`
def main():
    """Main entry point for `python -m unified_cloud_services`."""
    print("unified-cloud-services")
    print("=" * 40)
    print("\nAvailable CLI commands (after pip install):")
    print("  ucs-setup     - Install gcsfuse and set up mounting")
    print("  ucs-status    - Show GCS FUSE status")
    print("  ucs-mount     - Mount a GCS bucket")
    print("  ucs-unmount   - Unmount a GCS bucket")
    print("\nPython API:")
    print("  from unified_cloud_services import GCSFuseHelper")
    print("  GCSFuseHelper().print_status()")
    print()


if __name__ == "__main__":
    main()

