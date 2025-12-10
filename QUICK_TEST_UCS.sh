#!/bin/bash
# Quick script to test UCS connection before integration

set -e

echo "=========================================="
echo "UCS Connection Test"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found"
    echo "   Creating from .env.example..."
    cp .env.example .env
    echo ""
    echo "⚠️  Please edit .env and add your values:"
    echo "   - GCP_PROJECT_ID"
    echo "   - UNIFIED_CLOUD_SERVICES_GCS_BUCKET"
    echo "   - GCS_BUCKET"
    echo ""
    echo "   GOOGLE_APPLICATION_CREDENTIALS is already set to:"
    echo "   .secrets/gcs/gcs-service-account.json"
    echo ""
    exit 1
fi

# Check if credentials exist
if [ ! -f .secrets/gcs/gcs-service-account.json ]; then
    echo "❌ Credentials file not found: .secrets/gcs/gcs-service-account.json"
    exit 1
fi

echo "✅ Credentials file found"
echo ""

# Check if UCS is installed
echo "Checking UCS installation..."
if python3 -c "from unified_cloud_services import UnifiedCloudService" 2>/dev/null; then
    echo "✅ UCS is installed"
else
    echo "❌ UCS is NOT installed"
    echo ""
    echo "Installing UCS..."
    pip install git+https://github.com/IggyIkenna/unified-cloud-services.git
    echo ""
fi

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set default for GOOGLE_APPLICATION_CREDENTIALS if not set
if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    export GOOGLE_APPLICATION_CREDENTIALS=.secrets/gcs/gcs-service-account.json
fi

echo ""
echo "=========================================="
echo "Running UCS Connection Tests"
echo "=========================================="
echo ""

# Run test script
python3 backend/scripts/test_ucs_connection.py "$@"

echo ""
echo "=========================================="
echo "Test Complete"
echo "=========================================="
echo ""
echo "If all tests passed, you're ready to integrate!"
echo "Next step: Update backtest_engine.py and results.py"

