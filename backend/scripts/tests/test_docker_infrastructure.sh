#!/bin/bash
# Comprehensive Docker Infrastructure Test Script
# Tests all aspects of Docker setup as per AGENT_3_DOCKER_INFRASTRUCTURE.md

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results tracking
PASSED=0
FAILED=0
SKIPPED=0

# Function to print test results
test_result() {
    local status=$1
    local message=$2
    if [ "$status" == "PASS" ]; then
        echo -e "${GREEN}✓${NC} $message"
        PASSED=$((PASSED + 1))
    elif [ "$status" == "FAIL" ]; then
        echo -e "${RED}✗${NC} $message"
        FAILED=$((FAILED + 1))
    elif [ "$status" == "SKIP" ]; then
        echo -e "${YELLOW}⊘${NC} $message"
        SKIPPED=$((SKIPPED + 1))
    fi
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

echo "=========================================="
echo "Docker Infrastructure Test Suite"
echo "=========================================="
echo ""

# 1. Docker Setup & Installation
echo "=== 1. Docker Setup & Installation ==="

if command_exists docker; then
    DOCKER_VERSION=$(docker --version)
    test_result "PASS" "Docker is installed: $DOCKER_VERSION"
else
    test_result "FAIL" "Docker is not installed"
    exit 1
fi

# Check Docker Compose (handle both V1 and V2)
set +e  # Temporarily disable exit on error for this check
COMPOSE_AVAILABLE=false
COMPOSE_VERSION=""
if command_exists docker-compose; then
    COMPOSE_VERSION=$(docker-compose --version 2>&1)
    if [ $? -eq 0 ] && [ -n "$COMPOSE_VERSION" ]; then
        COMPOSE_AVAILABLE=true
    fi
fi

if [ "$COMPOSE_AVAILABLE" != true ]; then
    docker compose version >/dev/null 2>&1
    if [ $? -eq 0 ]; then
        COMPOSE_VERSION=$(docker compose version 2>&1)
        if [ $? -eq 0 ] && [ -n "$COMPOSE_VERSION" ]; then
            COMPOSE_AVAILABLE=true
        fi
    fi
fi
set -e  # Re-enable exit on error

if [ "$COMPOSE_AVAILABLE" = true ] && [ -n "$COMPOSE_VERSION" ]; then
    test_result "PASS" "Docker Compose is installed: $COMPOSE_VERSION"
else
    test_result "FAIL" "Docker Compose is not installed"
    exit 1
fi

# Check disk space (at least 5GB free)
# macOS uses -g flag, Linux uses -BG flag
if df -g . >/dev/null 2>&1; then
    AVAILABLE_SPACE=$(df -g . | tail -1 | awk '{print $4}')
else
    AVAILABLE_SPACE=$(df -BG . | tail -1 | awk '{print $4}' | sed 's/G//')
fi
if [ "$AVAILABLE_SPACE" -ge 5 ]; then
    test_result "PASS" "Sufficient disk space: ${AVAILABLE_SPACE}GB available"
else
    test_result "FAIL" "Insufficient disk space: ${AVAILABLE_SPACE}GB available (need at least 5GB)"
fi

# Check memory (at least 4GB)
TOTAL_MEM=$(sysctl -n hw.memsize 2>/dev/null || echo "0")
if [ "$TOTAL_MEM" -gt 0 ]; then
    TOTAL_MEM_GB=$((TOTAL_MEM / 1024 / 1024 / 1024))
    if [ "$TOTAL_MEM_GB" -ge 4 ]; then
        test_result "PASS" "Sufficient memory: ${TOTAL_MEM_GB}GB total"
    else
        test_result "FAIL" "Insufficient memory: ${TOTAL_MEM_GB}GB total (need at least 4GB)"
    fi
else
    test_result "SKIP" "Could not check memory (non-macOS system)"
fi

echo ""

# 2. Build Process
echo "=== 2. Build Process ==="

echo "Building backend..."
if docker compose build backend >/dev/null 2>&1; then
    test_result "PASS" "Backend image builds successfully"
else
    test_result "FAIL" "Backend image build failed"
    docker compose build backend
    exit 1
fi

echo "Building frontend..."
if docker compose build frontend >/dev/null 2>&1; then
    test_result "PASS" "Frontend image builds successfully"
else
    test_result "FAIL" "Frontend image build failed"
    docker compose build frontend
    exit 1
fi

# Check image sizes
BACKEND_SIZE=$(docker images --format "{{.Size}}" nautilus-backend 2>/dev/null | head -1 || echo "unknown")
FRONTEND_SIZE=$(docker images --format "{{.Size}}" nautilus-frontend 2>/dev/null | head -1 || echo "unknown")
test_result "PASS" "Backend image size: $BACKEND_SIZE"
test_result "PASS" "Frontend image size: $FRONTEND_SIZE"

echo ""

# 3. Service Startup
echo "=== 3. Service Startup ==="

echo "Starting services..."
if docker compose up -d >/dev/null 2>&1; then
    test_result "PASS" "Services started successfully"
else
    test_result "FAIL" "Failed to start services"
    docker compose up -d
    exit 1
fi

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10

# Check container status
if docker compose ps | grep -q "Up"; then
    test_result "PASS" "Containers are running"
else
    test_result "FAIL" "Some containers are not running"
    docker compose ps
fi

# Check for port conflicts
if lsof -i :8000 >/dev/null 2>&1 && ! docker compose ps | grep -q "8000"; then
    test_result "FAIL" "Port 8000 is already in use by another process"
else
    test_result "PASS" "Port 8000 is available"
fi

if lsof -i :5173 >/dev/null 2>&1 && ! docker compose ps | grep -q "5173"; then
    test_result "FAIL" "Port 5173 is already in use by another process"
else
    test_result "PASS" "Port 5173 is available"
fi

echo ""

# 4. Service Health Checks
echo "=== 4. Service Health Checks ==="

# Backend health check
echo "Checking backend health..."
sleep 5
if curl -f http://localhost:8000/api/health >/dev/null 2>&1; then
    test_result "PASS" "Backend health check endpoint responds"
    HEALTH_RESPONSE=$(curl -s http://localhost:8000/api/health)
    echo "  Response: $HEALTH_RESPONSE"
else
    test_result "FAIL" "Backend health check endpoint failed"
    echo "  Backend logs:"
    docker compose logs backend | tail -20
fi

# Check API docs
if curl -f http://localhost:8000/docs >/dev/null 2>&1; then
    test_result "PASS" "Backend API docs accessible"
else
    test_result "FAIL" "Backend API docs not accessible"
fi

# Frontend health check
echo "Checking frontend health..."
sleep 5
if curl -f http://localhost:5173 >/dev/null 2>&1; then
    test_result "PASS" "Frontend is accessible"
else
    test_result "FAIL" "Frontend is not accessible"
    echo "  Frontend logs:"
    docker compose logs frontend | tail -20
fi

# Check Docker health checks
BACKEND_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' nautilus-backend 2>/dev/null || echo "unknown")
if [ "$BACKEND_HEALTH" == "healthy" ] || [ "$BACKEND_HEALTH" == "starting" ]; then
    test_result "PASS" "Backend container health check: $BACKEND_HEALTH"
else
    test_result "FAIL" "Backend container health check: $BACKEND_HEALTH"
fi

FRONTEND_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' nautilus-frontend 2>/dev/null || echo "unknown")
if [ "$FRONTEND_HEALTH" == "healthy" ] || [ "$FRONTEND_HEALTH" == "starting" ]; then
    test_result "PASS" "Frontend container health check: $FRONTEND_HEALTH"
else
    test_result "FAIL" "Frontend container health check: $FRONTEND_HEALTH"
fi

echo ""

# 5. Volume Management
echo "=== 5. Volume Management ==="

# Check data_downloads mount (read-only)
if docker compose exec -T backend test -r /app/data_downloads >/dev/null 2>&1; then
    test_result "PASS" "data_downloads volume is readable"
    if docker compose exec -T backend test -w /app/data_downloads >/dev/null 2>&1; then
        test_result "FAIL" "data_downloads volume should be read-only but is writable"
    else
        test_result "PASS" "data_downloads volume is read-only (correct)"
    fi
else
    test_result "FAIL" "data_downloads volume is not readable"
fi

# Check parquet catalog mount (read-write)
if docker compose exec -T backend test -w /app/backend/data/parquet >/dev/null 2>&1; then
    test_result "PASS" "parquet catalog volume is writable"
else
    test_result "FAIL" "parquet catalog volume is not writable"
fi

# Check backtest_results mount (read-write)
if docker compose exec -T backend test -w /app/backend/backtest_results >/dev/null 2>&1; then
    test_result "PASS" "backtest_results volume is writable"
else
    test_result "FAIL" "backtest_results volume is not writable"
fi

# Check tickdata mount (read-write)
if docker compose exec -T backend test -w /app/frontend/public/tickdata >/dev/null 2>&1; then
    test_result "PASS" "tickdata volume is writable"
else
    test_result "FAIL" "tickdata volume is not writable"
fi

# Check configs mount (read-only)
if docker compose exec -T backend test -r /app/external/data_downloads/configs >/dev/null 2>&1; then
    test_result "PASS" "configs volume is readable"
    if docker compose exec -T backend test -w /app/external/data_downloads/configs >/dev/null 2>&1; then
        test_result "FAIL" "configs volume should be read-only but is writable"
    else
        test_result "PASS" "configs volume is read-only (correct)"
    fi
else
    test_result "FAIL" "configs volume is not readable"
fi

# Test volume persistence
echo "Testing volume persistence..."
TEST_FILE="/app/backend/data/parquet/test_persistence.txt"
echo "test" | docker compose exec -T backend bash -c "cat > $TEST_FILE" >/dev/null 2>&1
docker compose stop >/dev/null 2>&1
docker compose start >/dev/null 2>&1
sleep 5
if docker compose exec -T backend test -f "$TEST_FILE" >/dev/null 2>&1; then
    test_result "PASS" "Volume data persists across restarts"
    docker compose exec -T backend rm -f "$TEST_FILE" >/dev/null 2>&1
else
    test_result "FAIL" "Volume data does not persist across restarts"
fi

echo ""

# 6. Network Connectivity
echo "=== 6. Network Connectivity ==="

# Test backend API from host
if curl -f http://localhost:8000/api/health >/dev/null 2>&1; then
    test_result "PASS" "Backend API accessible from host"
else
    test_result "FAIL" "Backend API not accessible from host"
fi

# Test frontend from host
if curl -f http://localhost:5173 >/dev/null 2>&1; then
    test_result "PASS" "Frontend accessible from host"
else
    test_result "FAIL" "Frontend not accessible from host"
fi

# Test backend from frontend container
if docker compose exec -T frontend wget -q -O- http://backend:8000/api/health >/dev/null 2>&1; then
    test_result "PASS" "Frontend can reach backend API via internal network"
else
    test_result "FAIL" "Frontend cannot reach backend API via internal network"
fi

echo ""

# 7. Environment Variables
echo "=== 7. Environment Variables ==="
# Note: PYTHONPATH no longer needed - package is installed via pip install -e .

ENV_VARS=(
    "UNIFIED_CLOUD_LOCAL_PATH=/app/data_downloads"
    "UNIFIED_CLOUD_SERVICES_USE_PARQUET=true"
    "DATA_CATALOG_PATH=/app/backend/data/parquet"
)

for var in "${ENV_VARS[@]}"; do
    KEY="${var%%=*}"
    EXPECTED="${var#*=}"
    ACTUAL=$(docker compose exec -T backend printenv "$KEY" 2>/dev/null || echo "")
    if [ "$ACTUAL" == "$EXPECTED" ]; then
        test_result "PASS" "Backend env var $KEY=$EXPECTED"
    else
        test_result "FAIL" "Backend env var $KEY: expected '$EXPECTED', got '$ACTUAL'"
    fi
done

# Check frontend env vars
FRONTEND_API_URL=$(docker compose exec -T frontend printenv VITE_API_URL 2>/dev/null || echo "")
if [ -n "$FRONTEND_API_URL" ]; then
    test_result "PASS" "Frontend env var VITE_API_URL=$FRONTEND_API_URL"
else
    test_result "FAIL" "Frontend env var VITE_API_URL is not set"
fi

echo ""

# 8. Container Configuration
echo "=== 8. Container Configuration ==="

# Check if containers run as non-root (if configured)
BACKEND_USER=$(docker compose exec -T backend whoami 2>/dev/null || echo "unknown")
if [ "$BACKEND_USER" == "root" ]; then
    test_result "SKIP" "Backend runs as root (consider using non-root user for production)"
else
    test_result "PASS" "Backend runs as non-root user: $BACKEND_USER"
fi

# Check logs are accessible
if docker compose logs backend >/dev/null 2>&1; then
    test_result "PASS" "Backend logs are accessible"
else
    test_result "FAIL" "Backend logs are not accessible"
fi

if docker compose logs frontend >/dev/null 2>&1; then
    test_result "PASS" "Frontend logs are accessible"
else
    test_result "FAIL" "Frontend logs are not accessible"
fi

echo ""

# Summary
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "${GREEN}Passed:${NC} $PASSED"
echo -e "${RED}Failed:${NC} $FAILED"
echo -e "${YELLOW}Skipped:${NC} $SKIPPED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please review the output above.${NC}"
    exit 1
fi

