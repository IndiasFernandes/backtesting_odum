#!/bin/bash
# Helper script to build Docker containers with GitHub token authentication

set -e

echo "🔐 Docker Build Helper for Private GitHub Repo"
echo "=============================================="
echo ""

# Check if GITHUB_TOKEN is set
if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ GITHUB_TOKEN environment variable is not set"
    echo ""
    echo "To build with authentication, you need a GitHub Personal Access Token:"
    echo ""
    echo "1. Create a token:"
    echo "   https://github.com/settings/tokens"
    echo "   → Generate new token (classic)"
    echo "   → Select 'repo' scope"
    echo "   → Generate and copy the token"
    echo ""
    echo "2. Set the token and build:"
    echo "   export GITHUB_TOKEN=your_token_here"
    echo "   ./build.sh"
    echo ""
    echo "Or build directly:"
    echo "   GITHUB_TOKEN=your_token_here docker-compose build"
    echo ""
    exit 1
fi

echo "✅ GITHUB_TOKEN is set"
echo "🔨 Building Docker containers..."
echo ""

# Build with docker-compose
docker-compose build "$@"

echo ""
echo "✅ Build complete!"
echo ""
echo "To start the containers:"
echo "   docker-compose up -d"
echo ""

