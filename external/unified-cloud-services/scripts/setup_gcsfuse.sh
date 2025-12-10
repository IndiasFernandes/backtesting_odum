#!/bin/bash
# GCS FUSE Setup Script for unified-cloud-services
#
# This script installs gcsfuse and sets up mount points for local development.
# Run with: ./scripts/setup_gcsfuse.sh [bucket_name]
#
# Examples:
#   ./scripts/setup_gcsfuse.sh market-data-tick-central-element-323112
#   ./scripts/setup_gcsfuse.sh  # Uses default bucket

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default bucket (can be overridden by argument)
DEFAULT_BUCKET="market-data-tick-central-element-323112"
BUCKET_NAME="${1:-$DEFAULT_BUCKET}"

echo -e "${GREEN}🚀 GCS FUSE Setup for unified-cloud-services${NC}"
echo "================================================"
echo "Bucket: $BUCKET_NAME"
echo ""

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ -f /etc/debian_version ]]; then
        echo "debian"
    elif [[ -f /etc/redhat-release ]]; then
        echo "redhat"
    else
        echo "unknown"
    fi
}

OS=$(detect_os)
echo -e "Detected OS: ${YELLOW}$OS${NC}"

# Install gcsfuse based on OS
install_gcsfuse() {
    echo ""
    echo -e "${GREEN}📦 Installing gcsfuse...${NC}"
    
    case $OS in
        macos)
            if command -v brew &> /dev/null; then
                echo "Installing macFUSE (required dependency)..."
                brew install --cask macfuse || true
                
                # Check if macFUSE installed successfully
                if ! command -v mount_macfuse &> /dev/null; then
                    echo -e "${YELLOW}⚠️  macFUSE may need manual installation${NC}"
                fi
                
                # Note: gcsfuse via Homebrew doesn't work on macOS
                # We'll download the binary directly via Python script
                echo "Note: gcsfuse will be installed via Python (ucs-setup command)"
                echo "   Run: ucs-setup to complete installation"
            else
                echo -e "${RED}❌ Homebrew not found. Please install Homebrew first:${NC}"
                echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
                exit 1
            fi
            ;;
        debian)
            echo "Adding Google Cloud apt repository..."
            export GCSFUSE_REPO=gcsfuse-$(lsb_release -c -s)
            echo "deb https://packages.cloud.google.com/apt $GCSFUSE_REPO main" | sudo tee /etc/apt/sources.list.d/gcsfuse.list
            curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
            sudo apt-get update
            sudo apt-get install -y gcsfuse
            ;;
        redhat)
            sudo tee /etc/yum.repos.d/gcsfuse.repo > /dev/null <<EOF
[gcsfuse]
name=gcsfuse (packages.cloud.google.com)
baseurl=https://packages.cloud.google.com/yum/repos/gcsfuse-el7-x86_64
enabled=1
gpgcheck=1
repo_gpgcheck=0
gpgkey=https://packages.cloud.google.com/yum/doc/yum-key.gpg
       https://packages.cloud.google.com/yum/doc/rpm-package-key.gpg
EOF
            sudo yum install -y gcsfuse
            ;;
        *)
            echo -e "${RED}❌ Unknown OS. Please install gcsfuse manually:${NC}"
            echo "   https://github.com/GoogleCloudPlatform/gcsfuse/blob/master/docs/installing.md"
            exit 1
            ;;
    esac
}

# Check if gcsfuse is installed
check_gcsfuse() {
    if command -v gcsfuse &> /dev/null; then
        GCSFUSE_VERSION=$(gcsfuse --version 2>&1 | head -1)
        echo -e "${GREEN}✅ gcsfuse is installed: $GCSFUSE_VERSION${NC}"
        return 0
    else
        return 1
    fi
}

# Check gcloud authentication
check_gcloud_auth() {
    echo ""
    echo -e "${GREEN}🔐 Checking gcloud authentication...${NC}"
    
    if ! command -v gcloud &> /dev/null; then
        echo -e "${RED}❌ gcloud CLI not found. Please install Google Cloud SDK:${NC}"
        echo "   https://cloud.google.com/sdk/docs/install"
        exit 1
    fi
    
    if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
        ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
        echo -e "${GREEN}✅ Authenticated as: $ACCOUNT${NC}"
    else
        echo -e "${YELLOW}⚠️  Not authenticated. Running gcloud auth login...${NC}"
        gcloud auth login
        gcloud auth application-default login
    fi
}

# Create mount point and mount bucket
setup_mount() {
    echo ""
    echo -e "${GREEN}📁 Setting up mount point...${NC}"
    
    # Determine mount location
    if [[ "$OS" == "macos" ]]; then
        MOUNT_BASE="$HOME/gcs"
    else
        MOUNT_BASE="/mnt/gcs"
    fi
    
    MOUNT_POINT="$MOUNT_BASE/$BUCKET_NAME"
    
    # Create mount directory
    if [[ "$OS" == "macos" ]]; then
        mkdir -p "$MOUNT_POINT"
    else
        sudo mkdir -p "$MOUNT_POINT"
        sudo chown $(whoami):$(whoami) "$MOUNT_POINT"
    fi
    
    echo "Mount point: $MOUNT_POINT"
    
    # Check if already mounted
    if mountpoint -q "$MOUNT_POINT" 2>/dev/null || mount | grep -q "$MOUNT_POINT"; then
        echo -e "${YELLOW}⚠️  Already mounted at $MOUNT_POINT${NC}"
        return 0
    fi
    
    # Mount the bucket
    echo "Mounting $BUCKET_NAME..."
    gcsfuse --implicit-dirs "$BUCKET_NAME" "$MOUNT_POINT"
    
    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}✅ Successfully mounted $BUCKET_NAME at $MOUNT_POINT${NC}"
    else
        echo -e "${RED}❌ Failed to mount bucket${NC}"
        exit 1
    fi
}

# Add environment variable to shell config
setup_env_var() {
    echo ""
    echo -e "${GREEN}🔧 Setting up environment variable...${NC}"
    
    # Determine shell config file
    if [[ -f "$HOME/.zshrc" ]]; then
        SHELL_RC="$HOME/.zshrc"
    elif [[ -f "$HOME/.bashrc" ]]; then
        SHELL_RC="$HOME/.bashrc"
    else
        SHELL_RC="$HOME/.profile"
    fi
    
    # Add GCS_FUSE_MOUNT_PATH if not already present
    if ! grep -q "GCS_FUSE_MOUNT_PATH" "$SHELL_RC"; then
        echo "" >> "$SHELL_RC"
        echo "# GCS FUSE mount path for unified-cloud-services" >> "$SHELL_RC"
        echo "export GCS_FUSE_MOUNT_PATH=\"$MOUNT_POINT\"" >> "$SHELL_RC"
        echo -e "${GREEN}✅ Added GCS_FUSE_MOUNT_PATH to $SHELL_RC${NC}"
        echo -e "${YELLOW}   Run: source $SHELL_RC${NC}"
    else
        echo -e "${YELLOW}⚠️  GCS_FUSE_MOUNT_PATH already in $SHELL_RC${NC}"
    fi
    
    # Export for current session
    export GCS_FUSE_MOUNT_PATH="$MOUNT_POINT"
}

# Create unmount script
create_unmount_script() {
    UNMOUNT_SCRIPT="$HOME/.local/bin/unmount-gcs"
    mkdir -p "$HOME/.local/bin"
    
    cat > "$UNMOUNT_SCRIPT" << EOF
#!/bin/bash
# Unmount GCS FUSE bucket
MOUNT_POINT="$MOUNT_POINT"

if mountpoint -q "\$MOUNT_POINT" 2>/dev/null || mount | grep -q "\$MOUNT_POINT"; then
    fusermount -u "\$MOUNT_POINT" 2>/dev/null || umount "\$MOUNT_POINT"
    echo "✅ Unmounted \$MOUNT_POINT"
else
    echo "⚠️  Not mounted: \$MOUNT_POINT"
fi
EOF
    chmod +x "$UNMOUNT_SCRIPT"
    echo -e "${GREEN}✅ Created unmount script: $UNMOUNT_SCRIPT${NC}"
}

# Main execution
main() {
    # Install gcsfuse if not present
    if ! check_gcsfuse; then
        install_gcsfuse
        check_gcsfuse || exit 1
    fi
    
    # Check authentication
    check_gcloud_auth
    
    # Setup mount
    setup_mount
    
    # Setup environment variable
    setup_env_var
    
    # Create unmount helper
    create_unmount_script
    
    echo ""
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}✅ GCS FUSE setup complete!${NC}"
    echo ""
    echo "Mount point: $MOUNT_POINT"
    echo "Environment: GCS_FUSE_MOUNT_PATH=$MOUNT_POINT"
    echo ""
    echo "To verify, run:"
    echo "  ls $MOUNT_POINT"
    echo ""
    echo "To unmount later:"
    echo "  ~/.local/bin/unmount-gcs"
    echo "  # or: fusermount -u $MOUNT_POINT"
    echo ""
}

main

