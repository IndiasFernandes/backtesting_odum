#!/bin/bash
# Setup script for Unified Cloud Services (UCS) integration
# This script installs UCS and verifies the installation

set -e  # Exit on error

echo "=========================================="
echo "UCS Setup Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}ERROR: python3 not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Python found: $(python3 --version)"
echo ""

# Check if pip is available
if ! command -v pip3 &> /dev/null && ! command -v pip &> /dev/null; then
    echo -e "${RED}ERROR: pip not found${NC}"
    exit 1
fi

PIP_CMD="pip3"
if ! command -v pip3 &> /dev/null; then
    PIP_CMD="pip"
fi

echo -e "${GREEN}✓${NC} pip found: $PIP_CMD"
echo ""

# Install UCS from GitHub
echo "Installing Unified Cloud Services from GitHub..."
echo "Repository: https://github.com/IggyIkenna/unified-cloud-services"
echo ""

$PIP_CMD install --upgrade git+https://github.com/IggyIkenna/unified-cloud-services.git

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} UCS installed successfully"
else
    echo -e "${RED}✗${NC} UCS installation failed"
    exit 1
fi

echo ""

# Verify installation
echo "Verifying UCS installation..."
python3 -c "from unified_cloud_services import UnifiedCloudService, CloudTarget; print('✓ UCS imported successfully')" 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} UCS import test passed"
else
    echo -e "${RED}✗${NC} UCS import test failed"
    exit 1
fi

echo ""

# Check for ucs-mount command (for GCS FUSE mounting)
echo "Checking for ucs-mount command..."
if command -v ucs-mount &> /dev/null; then
    echo -e "${GREEN}✓${NC} ucs-mount command found"
    ucs-mount --help | head -5
else
    echo -e "${YELLOW}⚠${NC} ucs-mount command not found (may need to install separately)"
    echo "   This is OK if you're using direct GCS access or manual FUSE mounting"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Run connection test:"
echo "   python3 backend/scripts/test_ucs_connection.py"
echo ""
echo "2. Configure GCS credentials (if using direct GCS access):"
echo "   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json"
echo ""
echo "3. Test with specific bucket:"
echo "   python3 backend/scripts/test_ucs_connection.py --bucket YOUR_BUCKET_NAME"
echo ""
echo "4. Test upload functionality:"
echo "   python3 backend/scripts/test_ucs_connection.py --test-upload"
echo ""

