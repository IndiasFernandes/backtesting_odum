#!/usr/bin/env python3
"""
Generic script to store secrets in Google Secret Manager

This script can be used by any service to store secrets securely in Google Secret Manager.
It requires GCP authentication and Secret Manager Admin permissions.

Usage:
    python scripts/store_secret.py --secret-name SECRET_NAME --secret-value SECRET_VALUE [--project-id PROJECT_ID]

Examples:
    # Store GitHub token using service account (default)
    python scripts/store_secret.py --secret-name github-token --secret-value YOUR_TOKEN

    # Store GitHub token using your personal gcloud auth credentials
    python scripts/store_secret.py --secret-name github-token --secret-value YOUR_TOKEN --use-adc

    # Store API key with custom project
    python scripts/store_secret.py --secret-name my-api-key --secret-value KEY_VALUE --project-id my-project

    # Store from environment variable
    python scripts/store_secret.py --secret-name github-token --secret-value "$GITHUB_TOKEN"

This script stores secrets in Secret Manager so they can be accessed via unified-cloud-services
without hardcoding them in .env files or committing them to the repository.
"""

import argparse
import sys
import os
from pathlib import Path

# Set default environment variables before importing to avoid BaseServiceConfig validation errors
# These are only defaults - actual values can be overridden via environment or .env file
package_root = Path(__file__).parent.parent

if "GCP_PROJECT_ID" not in os.environ:
    os.environ["GCP_PROJECT_ID"] = "central-element-323112"
if "GCS_REGION" not in os.environ:
    os.environ["GCS_REGION"] = "asia-northeast1-c"
if "BIGQUERY_LOCATION" not in os.environ:
    os.environ["BIGQUERY_LOCATION"] = "asia-northeast1"

# Parse args early to check for --use-adc flag
import sys
use_adc_flag = "--use-adc" in sys.argv

# GOOGLE_APPLICATION_CREDENTIALS handling:
# - If --use-adc flag is set, don't set GOOGLE_APPLICATION_CREDENTIALS (use ADC)
# - If set to empty string in .env, unset it to use Application Default Credentials (gcloud auth)
# - If not set, auto-detect credentials file
# - If explicitly set to a path, use that path
if use_adc_flag:
    # Force using Application Default Credentials
    if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
        del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
    # Set to empty string for BaseServiceConfig (it will be handled specially)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = ""
elif "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
    if os.environ["GOOGLE_APPLICATION_CREDENTIALS"] == "":
        # Empty string means use Application Default Credentials (gcloud auth)
        # Keep it as empty string for BaseServiceConfig
        pass
elif "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
    # Auto-detect credentials file if not set
    creds_file = package_root / "central-element-323112-e35fb0ddafe2.json"
    if creds_file.exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(creds_file.absolute())
    else:
        # Check parent directories (instruments-service, etc.)
        parent_dirs = [
            package_root.parent / "instruments-service" / "central-element-323112-e35fb0ddafe2.json",
            package_root.parent / "market-tick-data-handler" / "central-element-323112-e35fb0ddafe2.json",
        ]
        for parent_creds in parent_dirs:
            if parent_creds.exists():
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(parent_creds.absolute())
                break
        else:
            # Not found, set to empty string for BaseServiceConfig
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = ""

# Add parent directory to path for imports
package_root = Path(__file__).parent.parent
sys.path.insert(0, str(package_root))

try:
    from unified_cloud_services import create_secret_if_not_exists
except ImportError:
    print(
        "❌ Error: unified-cloud-services not found. Install with: pip install -e ."
    )
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Store a secret in Google Secret Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Store GitHub token
  python scripts/store_secret.py --secret-name github-token --secret-value YOUR_TOKEN

  # Store API key with custom project
  python scripts/store_secret.py --secret-name my-api-key --secret-value KEY_VALUE --project-id my-project

  # Store from environment variable
  python scripts/store_secret.py --secret-name github-token --secret-value "$GITHUB_TOKEN"
        """
    )
    parser.add_argument(
        "--secret-name",
        required=True,
        help="Name of the secret in Secret Manager (e.g., 'github-token', 'api-key')",
    )
    parser.add_argument(
        "--secret-value",
        required=True,
        help="Value of the secret to store",
    )
    parser.add_argument(
        "--project-id",
        default="central-element-323112",
        help="GCP project ID (default: central-element-323112)",
    )
    parser.add_argument(
        "--skip-confirmation",
        action="store_true",
        help="Skip confirmation prompt for non-standard secret names",
    )
    parser.add_argument(
        "--use-adc",
        action="store_true",
        help="Use Application Default Credentials (gcloud auth application-default login) instead of service account file. "
             "Use this when your personal account has permissions but the service account doesn't.",
    )

    args = parser.parse_args()

    secret_name = args.secret_name.strip()
    secret_value = args.secret_value.strip()
    project_id = args.project_id.strip()

    if not secret_value:
        print("❌ Error: Secret value cannot be empty")
        return 1

    # Validate secret name format (should be lowercase with hyphens)
    if not secret_name.replace("-", "").replace("_", "").isalnum():
        print("⚠️  Warning: Secret names should contain only alphanumeric characters, hyphens, and underscores")
        if not args.skip_confirmation:
            response = input("Continue anyway? (y/n): ")
            if response.lower() != "y":
                print("Aborted.")
                return 1

    print(f"📦 Storing secret in Secret Manager...")
    print(f"   Project: {project_id}")
    print(f"   Secret name: {secret_name}")
    # Show partial value for confirmation (first 10 chars, last 4 chars)
    if len(secret_value) > 14:
        display_value = f"{secret_value[:10]}...{secret_value[-4:]}"
    else:
        display_value = f"{secret_value[:10]}..." if len(secret_value) > 10 else "***"
    print(f"   Secret value: {display_value}")

    try:
        # Determine credentials path
        # If --use-adc flag is set, unset GOOGLE_APPLICATION_CREDENTIALS to use ADC
        original_creds = None
        if use_adc_flag:
            original_creds = os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
            creds_path = None  # None means use ADC
        else:
            creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            if not creds_path:
                creds_path = None
        
        success = create_secret_if_not_exists(
            project_id=project_id,
            secret_name=secret_name,
            secret_value=secret_value,
            credentials_path=creds_path,
        )
        
        # Restore original if we unset it
        if use_adc_flag and original_creds:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = original_creds

        if success:
            print(f"\n✅ Successfully stored secret '{secret_name}' in Secret Manager!")
            print(f"\n📝 Next steps:")
            print(f"   1. Update your code to retrieve the secret:")
            print(f"      from unified_cloud_services import get_secret_with_fallback")
            print(f"      secret_value = get_secret_with_fallback('{secret_name}', '{project_id}', 'ENV_VAR_NAME')")
            print(f"   2. You can now safely commit .env files without the secret value")
            print(f"   3. The secret will be automatically retrieved from Secret Manager")
            return 0
        else:
            print(f"\n❌ Failed to store secret. Check your GCP permissions.")
            return 1

    except Exception as e:
        print(f"\n❌ Error storing secret: {e}")
        print(f"\n💡 Make sure you have:")
        print(f"   1. GCP credentials configured:")
        print(f"      export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json")
        print(f"      OR use: gcloud auth application-default login")
        print(f"   2. Secret Manager Admin permissions on project: {project_id}")
        print(f"   3. Correct project ID: {project_id}")
        print(f"\n💡 To check authentication:")
        print(f"   gcloud auth list")
        print(f"   gcloud config get-value project")
        return 1


if __name__ == "__main__":
    exit(main())

