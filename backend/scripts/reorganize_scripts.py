#!/usr/bin/env python3
"""
Script reorganization utility.

Moves scripts to appropriate directories based on REORGANIZATION_PLAN.md
"""
import os
import shutil
from pathlib import Path

# Scripts directory
SCRIPTS_DIR = Path(__file__).parent

# Files to archive (one-off/debug scripts)
ARCHIVE_FILES = [
    "check_gcs_paths.py",
    "download_may25_binance.py",
    "download_may26_binance.py",
    "download_one_day_verify.py",
    "download_and_verify_structure.py",
    "list_gcs_files.py",  # Redundant with list_gcs_dates_and_files.py
    "strategy_validator.py",  # Standalone validator
]

# Files to move to tests/
TEST_FILES = [
    "test_gcs_file_exists.py",
    "test_gcs_write.py",
    "verify_gcs_structure.py",
]

# Files to move to utils/
UTILS_FILES = [
    "list_available_dates.py",
    "list_gcs_dates_and_files.py",
]

# Files to remove (empty/duplicate)
REMOVE_FILES = [
    "gcs_write_examples.py",  # Empty, duplicate exists in utils/
]

# Production files (keep in root)
PRODUCTION_FILES = [
    "start.sh",
    "mount_gcs.sh",
    "setup_env.sh",
    "setup_ucs.sh",
    "verify_secrets.sh",
    "README.md",
    "REORGANIZATION_PLAN.md",
    "reorganize_scripts.py",  # This script
]


def create_directories():
    """Create necessary directories."""
    archive_dir = SCRIPTS_DIR / "archive"
    tests_dir = SCRIPTS_DIR / "tests"
    utils_dir = SCRIPTS_DIR / "utils"
    
    archive_dir.mkdir(exist_ok=True)
    tests_dir.mkdir(exist_ok=True)
    utils_dir.mkdir(exist_ok=True)
    
    return archive_dir, tests_dir, utils_dir


def move_files(files, target_dir, category):
    """Move files to target directory."""
    moved = []
    not_found = []
    
    for filename in files:
        source = SCRIPTS_DIR / filename
        if source.exists():
            target = target_dir / filename
            if target.exists():
                print(f"⚠️  {category}: {filename} already exists in {target_dir}, skipping")
                continue
            shutil.move(str(source), str(target))
            moved.append(filename)
            print(f"✅ {category}: Moved {filename} → {target_dir}")
        else:
            not_found.append(filename)
    
    return moved, not_found


def remove_files(files):
    """Remove files."""
    removed = []
    not_found = []
    
    for filename in files:
        filepath = SCRIPTS_DIR / filename
        if filepath.exists():
            filepath.unlink()
            removed.append(filename)
            print(f"🗑️  Removed: {filename}")
        else:
            not_found.append(filename)
    
    return removed, not_found


def create_archive_readme(archive_dir):
    """Create README in archive directory."""
    readme_content = """# Archived Scripts

This directory contains scripts that were archived as part of the reorganization.

## Why Archived?

These scripts are one-off debugging, testing, or verification scripts that:
- Are not imported or used by the main codebase
- Were created for specific debugging sessions
- Have functionality that may be useful for reference but not actively maintained

## Scripts

- `check_gcs_paths.py` - One-off debugging script for checking GCS path structure
- `download_may25_binance.py` - Specific date download script (May 25, 2023)
- `download_may26_binance.py` - Specific date download script (May 26, 2023)
- `download_one_day_verify.py` - One-off verification script
- `download_and_verify_structure.py` - Verification script (redundant with other tools)
- `list_gcs_files.py` - Basic listing script (redundant with list_gcs_dates_and_files.py)
- `strategy_validator.py` - Standalone validator (not integrated into main system)

## Usage

These scripts can still be run directly if needed for debugging or reference:

```bash
python backend/scripts/archive/check_gcs_paths.py
```

However, they are not actively maintained and may require updates to work with current codebase.

## Last Updated

Archived: December 2025
"""
    
    readme_path = archive_dir / "README.md"
    with open(readme_path, 'w') as f:
        f.write(readme_content)
    print(f"✅ Created {readme_path}")


def main():
    """Main reorganization function."""
    print("=" * 70)
    print("Backend Scripts Reorganization")
    print("=" * 70)
    print()
    
    # Create directories
    print("📁 Creating directories...")
    archive_dir, tests_dir, utils_dir = create_directories()
    print()
    
    # Move files to archive
    print("📦 Archiving one-off/debug scripts...")
    moved_archive, not_found_archive = move_files(ARCHIVE_FILES, archive_dir, "Archive")
    if not_found_archive:
        print(f"⚠️  Not found: {not_found_archive}")
    print()
    
    # Move files to tests/
    print("🧪 Moving test scripts to tests/...")
    moved_tests, not_found_tests = move_files(TEST_FILES, tests_dir, "Tests")
    if not_found_tests:
        print(f"⚠️  Not found: {not_found_tests}")
    print()
    
    # Move files to utils/
    print("🔧 Moving utility scripts to utils/...")
    moved_utils, not_found_utils = move_files(UTILS_FILES, utils_dir, "Utils")
    if not_found_utils:
        print(f"⚠️  Not found: {not_found_utils}")
    print()
    
    # Remove empty/duplicate files
    print("🗑️  Removing empty/duplicate files...")
    removed, not_found_remove = remove_files(REMOVE_FILES)
    if not_found_remove:
        print(f"⚠️  Not found: {not_found_remove}")
    print()
    
    # Create archive README
    print("📝 Creating archive README...")
    create_archive_readme(archive_dir)
    print()
    
    # Summary
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"✅ Archived: {len(moved_archive)} files")
    print(f"✅ Moved to tests/: {len(moved_tests)} files")
    print(f"✅ Moved to utils/: {len(moved_utils)} files")
    print(f"✅ Removed: {len(removed)} files")
    print()
    print("Reorganization complete! See REORGANIZATION_PLAN.md for details.")


if __name__ == "__main__":
    main()

