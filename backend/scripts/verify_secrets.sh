#!/bin/bash
# Verify that secret files exist and have correct permissions

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SECRETS_DIR="$PROJECT_ROOT/.secrets/gcs"

echo "=========================================="
echo "Secrets Verification"
echo "=========================================="
echo ""

# Check if .secrets directory exists
if [ ! -d "$PROJECT_ROOT/.secrets" ]; then
    echo "❌ ERROR: .secrets directory not found"
    echo "   Expected: $PROJECT_ROOT/.secrets"
    exit 1
fi

echo "✅ .secrets directory exists"

# Check if gcs subdirectory exists
if [ ! -d "$SECRETS_DIR" ]; then
    echo "❌ ERROR: .secrets/gcs directory not found"
    echo "   Expected: $SECRETS_DIR"
    exit 1
fi

echo "✅ .secrets/gcs directory exists"

# Check for gcs-service-account.json
SERVICE_ACCOUNT_FILE="$SECRETS_DIR/gcs-service-account.json"
if [ ! -f "$SERVICE_ACCOUNT_FILE" ]; then
    echo "❌ ERROR: Service account file not found"
    echo "   Expected: $SERVICE_ACCOUNT_FILE"
    echo ""
    echo "   Please place your GCS service account JSON file at:"
    echo "   $SERVICE_ACCOUNT_FILE"
    exit 1
fi

echo "✅ Service account file found: $SERVICE_ACCOUNT_FILE"

# Check file permissions (should be 600 or 400)
PERMS=$(stat -f "%OLp" "$SERVICE_ACCOUNT_FILE" 2>/dev/null || stat -c "%a" "$SERVICE_ACCOUNT_FILE" 2>/dev/null)
if [ "$PERMS" != "600" ] && [ "$PERMS" != "400" ] && [ "$PERMS" != "644" ]; then
    echo "⚠️  WARNING: Service account file permissions are $PERMS"
    echo "   Recommended: chmod 600 $SERVICE_ACCOUNT_FILE"
    echo ""
    read -p "Fix permissions now? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        chmod 600 "$SERVICE_ACCOUNT_FILE"
        echo "✅ Permissions updated to 600"
    fi
else
    echo "✅ Service account file permissions OK ($PERMS)"
fi

# Check if file is valid JSON
if ! python3 -m json.tool "$SERVICE_ACCOUNT_FILE" > /dev/null 2>&1; then
    echo "⚠️  WARNING: Service account file may not be valid JSON"
    echo "   Please verify the file is a valid JSON service account key"
else
    echo "✅ Service account file is valid JSON"
    
    # Try to extract project_id
    PROJECT_ID=$(python3 -c "import json; print(json.load(open('$SERVICE_ACCOUNT_FILE')).get('project_id', 'NOT_FOUND'))" 2>/dev/null || echo "NOT_FOUND")
    if [ "$PROJECT_ID" != "NOT_FOUND" ]; then
        echo "   Project ID found in key: $PROJECT_ID"
    fi
fi

# Check for certs.json (optional)
CERTS_FILE="$SECRETS_DIR/certs.json"
if [ -f "$CERTS_FILE" ]; then
    echo "✅ Certificate file found: $CERTS_FILE"
    CERTS_PERMS=$(stat -f "%OLp" "$CERTS_FILE" 2>/dev/null || stat -c "%a" "$CERTS_FILE" 2>/dev/null)
    if [ "$CERTS_PERMS" != "600" ] && [ "$CERTS_PERMS" != "400" ]; then
        echo "⚠️  WARNING: Certificate file permissions are $CERTS_PERMS"
        echo "   Recommended: chmod 600 $CERTS_FILE"
    else
        echo "✅ Certificate file permissions OK ($CERTS_PERMS)"
    fi
else
    echo "ℹ️  Certificate file not found (optional): $CERTS_FILE"
fi

echo ""
echo "=========================================="
echo "Verification Complete"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Update .env file with your GCP_PROJECT_ID and bucket names"
echo "2. Test connection: python3 backend/scripts/test_ucs_connection.py"
echo ""

