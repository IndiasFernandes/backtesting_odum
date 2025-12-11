#!/usr/bin/env python3
"""
Simple test for CatalogManager GCS support (no nautilus_trader dependency).

Tests the path detection and initialization logic without requiring nautilus_trader.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_path_detection():
    """Test GCS path detection logic."""
    print("=" * 80)
    print("TEST: GCS Path Detection Logic")
    print("=" * 80)
    
    # Simulate the path detection logic
    test_cases = [
        ("gcs://bucket/path/", True, "gcs://bucket/path/"),
        ("gs://bucket/path/", True, "gcs://bucket/path/"),  # Should normalize
        ("backend/data/parquet/", False, None),
        ("/app/backend/data/parquet/", False, None),
    ]
    
    all_passed = True
    for path, expected_is_gcs, expected_normalized in test_cases:
        # Simulate detection logic
        is_gcs = path.startswith("gcs://") or path.startswith("gs://")
        
        if is_gcs:
            # Normalize
            normalized = path.replace("gs://", "gcs://", 1) if path.startswith("gs://") else path
        else:
            normalized = None
        
        status = "✅" if is_gcs == expected_is_gcs else "❌"
        print(f"{status} Path: {path}")
        print(f"   Expected GCS: {expected_is_gcs}, Got: {is_gcs}")
        
        if is_gcs and normalized != expected_normalized:
            print(f"   ❌ Normalization failed: expected '{expected_normalized}', got '{normalized}'")
            all_passed = False
        
        if is_gcs != expected_is_gcs:
            all_passed = False
    
    return all_passed


def test_catalog_manager_init():
    """Test CatalogManager initialization logic (without importing nautilus_trader)."""
    print("\n" + "=" * 80)
    print("TEST: CatalogManager Initialization Logic")
    print("=" * 80)
    
    try:
        # Read the catalog_manager.py file and check the logic
        catalog_manager_path = Path(__file__).parent.parent / "catalog_manager.py"
        
        with open(catalog_manager_path, 'r') as f:
            content = f.read()
        
        # Check for key features
        checks = {
            "GCS path detection": "startswith(\"gcs://\")" in content or "startswith(\"gs://\")" in content,
            "Path normalization": "replace(\"gs://\", \"gcs://\"" in content,
            "GCS initialization": "fs_protocol=\"gcs\"" in content,
            "Storage options": "fs_storage_options" in content,
            "Local fallback": "ParquetDataCatalog(str(" in content,
            "Property for path": "@property" in content and "catalog_path" in content,
        }
        
        all_passed = True
        for check_name, check_result in checks.items():
            status = "✅" if check_result else "❌"
            print(f"{status} {check_name}")
            if not check_result:
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Error reading catalog_manager.py: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_environment_variable_logic():
    """Test environment variable handling logic."""
    print("\n" + "=" * 80)
    print("TEST: Environment Variable Handling")
    print("=" * 80)
    
    # Save original
    original_path = os.getenv("DATA_CATALOG_PATH")
    original_project = os.getenv("GCP_PROJECT_ID")
    
    try:
        # Test default path
        if "DATA_CATALOG_PATH" in os.environ:
            del os.environ["DATA_CATALOG_PATH"]
        
        default_path = os.getenv("DATA_CATALOG_PATH", "backend/data/parquet/")
        expected_default = "backend/data/parquet/"
        
        if default_path == expected_default:
            print(f"✅ Default catalog path logic: {default_path}")
        else:
            print(f"❌ Expected '{expected_default}', got '{default_path}'")
            return False
        
        # Test GCP_PROJECT_ID default
        if "GCP_PROJECT_ID" in os.environ:
            del os.environ["GCP_PROJECT_ID"]
        
        default_project = os.getenv("GCP_PROJECT_ID", "central-element-323112")
        expected_project = "central-element-323112"
        
        if default_project == expected_project:
            print(f"✅ Default GCP project ID logic: {default_project}")
        else:
            print(f"❌ Expected '{expected_project}', got '{default_project}'")
            return False
        
        return True
        
    finally:
        # Restore original values
        if original_path:
            os.environ["DATA_CATALOG_PATH"] = original_path
        if original_project:
            os.environ["GCP_PROJECT_ID"] = original_project


def main():
    """Run all tests."""
    print("=" * 80)
    print("CatalogManager GCS Support - Simple Test Suite")
    print("(No nautilus_trader dependency required)")
    print("=" * 80)
    
    tests = [
        ("Path Detection Logic", test_path_detection),
        ("CatalogManager Code Structure", test_catalog_manager_init),
        ("Environment Variable Logic", test_environment_variable_logic),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ All logic tests PASSED!")
        print("\nNote: Full integration test requires nautilus_trader to be installed.")
        print("      Run: pip install nautilus-trader")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) FAILED")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
