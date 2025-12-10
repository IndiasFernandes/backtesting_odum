"""
Entry point for `python -m unified_cloud_services`.

Usage:
    python -m unified_cloud_services           # Show help
    python -m unified_cloud_services setup     # Run ucs-setup
    python -m unified_cloud_services status    # Run ucs-status
"""

import sys
from unified_cloud_services.cli import (
    main,
    setup_gcsfuse,
    print_status,
    mount_bucket,
    unmount_bucket,
)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        # Remove the command from argv so argparse works correctly
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        
        if command == "setup":
            sys.exit(setup_gcsfuse())
        elif command == "status":
            sys.exit(print_status())
        elif command == "mount":
            sys.exit(mount_bucket())
        elif command == "unmount":
            sys.exit(unmount_bucket())
        else:
            print(f"Unknown command: {command}")
            main()
            sys.exit(1)
    else:
        main()

