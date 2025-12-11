#!/bin/bash
# Test script for running Docker services
# Assumes services are already running via: docker compose up -d

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
        ((PASSED++))
    elif [ "$status" == "FAIL" ]; then
        echo -e "${RED}✗${NC} $message"
        ((FAILED++))
    elif [ "$status" == "SKIP" ]; then
        echo -e "${YELLOW}⊘${NC} $message"
        ((SKIPPED++))
    fi
}

echo "=========================================="
echo "Docker Services Test Suite"
echo "Testing against running services"
echo "=========================================="
echo ""

# Check if services are running
echo "=== Checking Service Status ==="

if ! docker compose ps | grep -q "Up"; then
    echo -e "${RED}✗${NC} No services are running. Please start them with: docker compose up -d"
    exit 1
fi

set +e  # Temporarily disable exit on error for status checks
BACKEND_RUNNING=$(docker compose ps backend 2>/dev/null | grep -q "Up" && echo "yes" || echo "no")
FRONTEND_RUNNING=$(docker compose ps frontend 2>/dev/null | grep -q "Up" && echo "yes" || echo "no")
REDIS_RUNNING=$(docker compose ps redis 2>/dev/null | grep -q "Up" && echo "yes" || echo "no")
set -e  # Re-enable exit on error

set +e  # Temporarily disable exit on error
if [ "$BACKEND_RUNNING" = "yes" ]; then
    test_result "PASS" "Backend container is running"
else
    test_result "FAIL" "Backend container is not running"
fi

if [ "$FRONTEND_RUNNING" = "yes" ]; then
    test_result "PASS" "Frontend container is running"
else
    test_result "FAIL" "Frontend container is not running"
fi

if [ "$REDIS_RUNNING" = "yes" ]; then
    test_result "PASS" "Redis container is running"
else
    test_result "SKIP" "Redis container is not running (optional service)"
fi
set -e  # Re-enable exit on error

echo ""

# 1. Service Health Checks
echo "=== 1. Service Health Checks ==="

# Backend health check
echo "Checking backend health..."
sleep 2
if curl -f http://localhost:8000/api/health >/dev/null 2>&1; then
    HEALTH_RESPONSE=$(curl -s http://localhost:8000/api/health)
    test_result "PASS" "Backend health check endpoint responds"
    echo "  Response: $HEALTH_RESPONSE"
else
    test_result "FAIL" "Backend health check endpoint failed"
    echo "  Backend logs (last 10 lines):"
    docker compose logs --tail=10 backend
fi

# Check API docs
if curl -f http://localhost:8000/docs >/dev/null 2>&1; then
    test_result "PASS" "Backend API docs accessible at http://localhost:8000/docs"
else
    test_result "FAIL" "Backend API docs not accessible"
fi

# Frontend health check
echo "Checking frontend health..."
sleep 2
if curl -f http://localhost:5173 >/dev/null 2>&1; then
    test_result "PASS" "Frontend is accessible at http://localhost:5173"
else
    test_result "FAIL" "Frontend is not accessible"
    echo "  Frontend logs (last 10 lines):"
    docker compose logs --tail=10 frontend
fi

# Check Docker health checks
BACKEND_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' nautilus-backend 2>/dev/null || echo "unknown")
if [ "$BACKEND_HEALTH" == "healthy" ]; then
    test_result "PASS" "Backend container health check: $BACKEND_HEALTH"
elif [ "$BACKEND_HEALTH" == "starting" ]; then
    test_result "SKIP" "Backend container health check: $BACKEND_HEALTH (still starting)"
else
    test_result "FAIL" "Backend container health check: $BACKEND_HEALTH"
fi

FRONTEND_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' nautilus-frontend 2>/dev/null || echo "unknown")
if [ "$FRONTEND_HEALTH" == "healthy" ]; then
    test_result "PASS" "Frontend container health check: $FRONTEND_HEALTH"
elif [ "$FRONTEND_HEALTH" == "starting" ]; then
    test_result "SKIP" "Frontend container health check: $FRONTEND_HEALTH (still starting)"
else
    test_result "FAIL" "Frontend container health check: $FRONTEND_HEALTH"
fi

if [ "$REDIS_RUNNING" = "yes" ]; then
    REDIS_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' nautilus-redis 2>/dev/null || echo "unknown")
    if [ "$REDIS_HEALTH" == "healthy" ]; then
        test_result "PASS" "Redis container health check: $REDIS_HEALTH"
    elif [ "$REDIS_HEALTH" == "starting" ]; then
        test_result "SKIP" "Redis container health check: $REDIS_HEALTH (still starting)"
    else
        test_result "FAIL" "Redis container health check: $REDIS_HEALTH"
    fi
fi

echo ""

# 2. Volume Management
echo "=== 2. Volume Management ==="

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

echo ""

# 3. Network Connectivity
echo "=== 3. Network Connectivity ==="

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

# 4. Environment Variables
echo "=== 4. Environment Variables ==="
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

# 5. API Endpoints
echo "=== 5. API Endpoints ==="

# Test datasets endpoint
if curl -f http://localhost:8000/api/datasets >/dev/null 2>&1; then
    DATASETS=$(curl -s http://localhost:8000/api/datasets)
    test_result "PASS" "Datasets endpoint accessible"
    echo "  Found datasets: $(echo "$DATASETS" | jq -r 'length' 2>/dev/null || echo 'N/A')"
else
    test_result "FAIL" "Datasets endpoint not accessible"
fi

# Test configs endpoint
if curl -f http://localhost:8000/api/configs >/dev/null 2>&1; then
    CONFIGS=$(curl -s http://localhost:8000/api/configs)
    test_result "PASS" "Configs endpoint accessible"
    echo "  Found configs: $(echo "$CONFIGS" | jq -r 'length' 2>/dev/null || echo 'N/A')"
else
    test_result "FAIL" "Configs endpoint not accessible"
fi

# Test results endpoint
if curl -f http://localhost:8000/api/backtest/results >/dev/null 2>&1; then
    RESULTS=$(curl -s http://localhost:8000/api/backtest/results)
    test_result "PASS" "Results endpoint accessible"
    echo "  Found results: $(echo "$RESULTS" | jq -r 'length' 2>/dev/null || echo 'N/A')"
else
    test_result "FAIL" "Results endpoint not accessible"
fi

echo ""

# 6. Container Configuration
echo "=== 6. Container Configuration ==="

# Check if containers run as non-root
BACKEND_USER=$(docker compose exec -T backend whoami 2>/dev/null || echo "unknown")
if [ "$BACKEND_USER" == "root" ]; then
    test_result "SKIP" "Backend runs as root (consider using non-root user for production)"
else
    test_result "PASS" "Backend runs as non-root user: $BACKEND_USER"
fi

FRONTEND_USER=$(docker compose exec -T frontend whoami 2>/dev/null || echo "unknown")
if [ "$FRONTEND_USER" == "root" ]; then
    test_result "SKIP" "Frontend runs as root (consider using non-root user for production)"
else
    test_result "PASS" "Frontend runs as non-root user: $FRONTEND_USER"
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

