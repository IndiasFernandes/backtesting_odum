#!/bin/bash
# Test script for 3 deployment modes
# Usage: ./test_deployments.sh

set -e  # Exit on error

echo "=========================================="
echo "Testing 3 Deployment Modes"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if service is healthy
check_health() {
    local url=$1
    local service_name=$2
    local max_attempts=10
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -sf "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} $service_name is healthy"
            return 0
        fi
        echo -e "${YELLOW}Waiting for $service_name... (attempt $attempt/$max_attempts)${NC}"
        sleep 3
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}✗${NC} $service_name failed to become healthy"
    return 1
}

# Function to check if container is running
check_container() {
    local container=$1
    if docker-compose ps | grep -q "$container.*Up"; then
        echo -e "${GREEN}✓${NC} Container $container is running"
        return 0
    else
        echo -e "${RED}✗${NC} Container $container is not running"
        return 1
    fi
}

# Cleanup function
cleanup() {
    echo ""
    echo "Cleaning up..."
    docker-compose down > /dev/null 2>&1 || true
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

# ==========================================
# MODE 1: Backtest Profile
# ==========================================
echo -e "${YELLOW}=== MODE 1: Backtest Profile ===${NC}"
echo "Starting backtest profile..."
docker-compose --profile backtest down > /dev/null 2>&1 || true
docker-compose --profile backtest up -d

echo "Waiting for services to start..."
sleep 10

echo ""
echo "Checking services..."
check_container "odum-backend" || exit 1
check_container "odum-frontend" || exit 1

echo ""
echo "Checking APIs..."
check_health "http://localhost:8000/api/health" "Backtest API" || exit 1

echo ""
echo "Verifying live services are NOT running..."
if curl -sf "http://localhost:8001/api/health" > /dev/null 2>&1; then
    echo -e "${RED}✗${NC} Live API should not be running!"
    exit 1
else
    echo -e "${GREEN}✓${NC} Live services correctly not running"
fi

docker-compose --profile backtest down
echo -e "${GREEN}✅ MODE 1 PASSED${NC}"
echo ""

# ==========================================
# MODE 2: Live Profile
# ==========================================
echo -e "${YELLOW}=== MODE 2: Live Profile ===${NC}"
echo "Starting live services..."
docker-compose --profile live up -d

echo "Waiting for services to start..."
sleep 30

echo ""
echo "Checking services..."
check_container "odum-backend" || exit 1
check_container "odum-frontend" || exit 1
check_container "odum-live-backend" || exit 1
check_container "odum-postgres" || exit 1
check_container "odum-redis-live" || exit 1

echo ""
echo "Checking APIs..."
check_health "http://localhost:8000/api/health" "Backtest API" || exit 1
check_health "http://localhost:8001/api/health" "Live API" || exit 1

echo ""
echo "Checking PostgreSQL..."
if docker-compose exec -T postgres psql -U user -d execution_db -c "\dt" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} PostgreSQL is accessible"
else
    echo -e "${RED}✗${NC} PostgreSQL connection failed"
    exit 1
fi

echo ""
echo "Running database migrations..."
if docker-compose exec -T live-backend bash -c "cd backend/live && alembic upgrade head" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Migrations completed successfully"
else
    echo -e "${YELLOW}⚠${NC} Migrations may have already run (checking schema)..."
    if docker-compose exec -T postgres psql -U user -d execution_db -c "\dt" | grep -q "unified_orders"; then
        echo -e "${GREEN}✓${NC} Database schema exists"
    else
        echo -e "${RED}✗${NC} Database schema not found"
        exit 1
    fi
fi

echo ""
echo "Checking Redis..."
if docker-compose exec -T redis-live redis-cli ping | grep -q "PONG"; then
    echo -e "${GREEN}✓${NC} Redis is accessible"
else
    echo -e "${RED}✗${NC} Redis connection failed"
    exit 1
fi

docker-compose --profile live down
echo -e "${GREEN}✅ MODE 2 PASSED${NC}"
echo ""

# ==========================================
# MODE 3: Both Profile
# ==========================================
echo -e "${YELLOW}=== MODE 3: Both Profile ===${NC}"
echo "Starting both services..."
docker-compose --profile both up -d

echo "Waiting for services to start..."
sleep 30

echo ""
echo "Checking all services..."
check_container "odum-backend" || exit 1
check_container "odum-frontend" || exit 1
check_container "odum-live-backend" || exit 1
check_container "odum-postgres" || exit 1
check_container "odum-redis-live" || exit 1

echo ""
echo "Checking both APIs work simultaneously..."
check_health "http://localhost:8000/api/health" "Backtest API" || exit 1
check_health "http://localhost:8001/api/health" "Live API" || exit 1

echo ""
echo "Testing independent restart..."
docker-compose restart live-backend
sleep 5
check_health "http://localhost:8000/api/health" "Backtest API (after live restart)" || exit 1
check_health "http://localhost:8001/api/health" "Live API (after restart)" || exit 1

docker-compose --profile both down
echo -e "${GREEN}✅ MODE 3 PASSED${NC}"
echo ""

# ==========================================
# SUMMARY
# ==========================================
echo "=========================================="
echo -e "${GREEN}🎉 ALL TESTS PASSED!${NC}"
echo "=========================================="
echo ""
echo "Summary:"
echo "  ✓ Mode 1: Backtest Profile - PASSED"
echo "  ✓ Mode 2: Live Profile - PASSED"
echo "  ✓ Mode 3: Both Profile - PASSED"
echo ""
echo "All deployment modes are working correctly!"

