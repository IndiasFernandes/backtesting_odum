#!/bin/bash
# Setup script to create .env file from .env.example
# This script copies .env.example to .env if it doesn't exist

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_EXAMPLE="$PROJECT_ROOT/.env.example"
ENV_FILE="$PROJECT_ROOT/.env"

echo "=========================================="
echo "Environment Setup"
echo "=========================================="
echo ""

# Check if .env.example exists
if [ ! -f "$ENV_EXAMPLE" ]; then
    echo "❌ ERROR: .env.example not found at $ENV_EXAMPLE"
    exit 1
fi

# Check if .env already exists
if [ -f "$ENV_FILE" ]; then
    echo "⚠️  WARNING: .env file already exists at $ENV_FILE"
    echo ""
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "ℹ️  Keeping existing .env file"
        echo ""
        echo "To edit it manually:"
        echo "  nano $ENV_FILE"
        echo "  # or"
        echo "  vim $ENV_FILE"
        exit 0
    fi
    echo "⚠️  Overwriting existing .env file..."
fi

# Copy .env.example to .env
cp "$ENV_EXAMPLE" "$ENV_FILE"

echo "✅ Created .env file from .env.example"
echo ""
echo "📝 Next steps:"
echo "1. Edit .env file and fill in your values:"
echo "   nano $ENV_FILE"
echo ""
echo "2. Required variables:"
echo "   - GCP_PROJECT_ID"
echo "   - GOOGLE_APPLICATION_CREDENTIALS"
echo "   - UNIFIED_CLOUD_SERVICES_GCS_BUCKET"
echo "   - GCS_BUCKET"
echo ""
echo "3. Optional variables (if using FUSE mount):"
echo "   - USE_GCS_FUSE=true"
echo "   - GCS_FUSE_BUCKET=your-bucket-name"
echo ""
echo "4. After configuring, test the connection:"
echo "   python3 backend/scripts/test_ucs_connection.py"
echo ""

