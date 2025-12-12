# Frontend Service Detection & UI Management

> How the frontend adapts to active services (backtest only, live only, or both)

## Overview

The frontend dynamically detects which backend services are running and adapts the UI accordingly:
- **Backtest Only**: Shows backtest pages, hides live pages
- **Live Only**: Shows live pages, hides backtest pages  
- **Both**: Shows all pages
- **Neither**: Shows status page with connection instructions

---

## Service Detection Hook

### `useServiceDetection.ts`

```typescript
import { useState, useEffect } from 'react';

interface ServiceHealth {
  status: 'healthy' | 'unhealthy' | 'unknown';
  lastCheck: Date | null;
  error?: string;
}

interface ServiceDetection {
  backtestAvailable: boolean;
  liveAvailable: boolean;
  services: {
    backtest: ServiceHealth;
    live: ServiceHealth;
  };
  lastCheck: Date | null;
  checking: boolean;
}

export function useServiceDetection(): ServiceDetection {
  const [services, setServices] = useState({
    backtest: { status: 'unknown' as const, lastCheck: null },
    live: { status: 'unknown' as const, lastCheck: null },
  });
  const [checking, setChecking] = useState(false);
  const [lastCheck, setLastCheck] = useState<Date | null>(null);

  useEffect(() => {
    const checkServices = async () => {
      setChecking(true);
      
      // Check backtest service (port 8000)
      try {
        const backtestRes = await fetch('http://localhost:8000/api/health', {
          signal: AbortSignal.timeout(2000),
        });
        setServices(prev => ({
          ...prev,
          backtest: {
            status: backtestRes.ok ? 'healthy' : 'unhealthy',
            lastCheck: new Date(),
          },
        }));
      } catch (error) {
        setServices(prev => ({
          ...prev,
          backtest: {
            status: 'unhealthy',
            lastCheck: new Date(),
            error: error instanceof Error ? error.message : 'Unknown error',
          },
        }));
      }

      // Check live service (port 8001)
      try {
        const liveRes = await fetch('http://localhost:8001/api/live/health', {
          signal: AbortSignal.timeout(2000),
        });
        setServices(prev => ({
          ...prev,
          live: {
            status: liveRes.ok ? 'healthy' : 'unhealthy',
            lastCheck: new Date(),
          },
        }));
      } catch (error) {
        setServices(prev => ({
          ...prev,
          live: {
            status: 'unhealthy',
            lastCheck: new Date(),
            error: error instanceof Error ? error.message : 'Unknown error',
          },
        }));
      }

      setLastCheck(new Date());
      setChecking(false);
    };

    // Initial check
    checkServices();

    // Check every 5 seconds
    const interval = setInterval(checkServices, 5000);

    return () => clearInterval(interval);
  }, []);

  return {
    backtestAvailable: services.backtest.status === 'healthy',
    liveAvailable: services.live.status === 'healthy',
    services,
    lastCheck,
    checking,
  };
}
```

---

## Conditional Route Rendering

### `App.tsx`

```typescript
import { Routes, Route } from 'react-router-dom';
import { useServiceDetection } from './hooks/useServiceDetection';
import BacktestRunPage from './pages/BacktestRunPage';
import LiveExecutePage from './pages/LiveExecutePage';
import StatusPage from './pages/StatusPage';

function App() {
  const { backtestAvailable, liveAvailable } = useServiceDetection();

  return (
    <Routes>
      {/* Status page always accessible */}
      <Route path="/status" element={<StatusPage />} />
      
      {/* Backtest pages - only if backtest service available */}
      {backtestAvailable && (
        <>
          <Route path="/run" element={<BacktestRunPage />} />
          <Route path="/compare" element={<BacktestComparePage />} />
          <Route path="/algorithms" element={<AlgorithmsPage />} />
        </>
      )}
      
      {/* Live pages - only if live service available */}
      {liveAvailable && (
        <>
          <Route path="/live/execute" element={<LiveExecutePage />} />
          <Route path="/live/positions" element={<LivePositionsPage />} />
          <Route path="/live/orders" element={<LiveOrdersPage />} />
          <Route path="/live/strategies" element={<LiveStrategiesPage />} />
        </>
      )}
      
      {/* Default redirect */}
      <Route path="/" element={<Navigate to="/status" />} />
    </Routes>
  );
}
```

---

## Navigation Component

### `Navigation.tsx`

```typescript
import { Link } from 'react-router-dom';
import { useServiceDetection } from './hooks/useServiceDetection';

function Navigation() {
  const { backtestAvailable, liveAvailable } = useServiceDetection();

  return (
    <nav>
      <Link to="/status">Status</Link>
      
      {backtestAvailable && (
        <>
          <Link to="/run">Run Backtest</Link>
          <Link to="/compare">Compare Results</Link>
          <Link to="/algorithms">Algorithms</Link>
        </>
      )}
      
      {liveAvailable && (
        <>
          <Link to="/live/execute">Live Execute</Link>
          <Link to="/live/positions">Positions</Link>
          <Link to="/live/orders">Orders</Link>
          <Link to="/live/strategies">Strategies</Link>
        </>
      )}
    </nav>
  );
}
```

---

## Status Page

### `StatusPage.tsx`

```typescript
import { useServiceDetection } from '../hooks/useServiceDetection';

function StatusPage() {
  const { services, lastCheck, checking } = useServiceDetection();

  return (
    <div>
      <h1>Service Status</h1>
      
      <div>
        <h2>Backtest Service (Port 8000)</h2>
        <p>Status: {services.backtest.status}</p>
        {services.backtest.lastCheck && (
          <p>Last Check: {services.backtest.lastCheck.toLocaleString()}</p>
        )}
        {services.backtest.error && (
          <p>Error: {services.backtest.error}</p>
        )}
      </div>
      
      <div>
        <h2>Live Service (Port 8001)</h2>
        <p>Status: {services.live.status}</p>
        {services.live.lastCheck && (
          <p>Last Check: {services.live.lastCheck.toLocaleString()}</p>
        )}
        {services.live.error && (
          <p>Error: {services.live.error}</p>
        )}
      </div>
      
      {lastCheck && (
        <p>Last Check: {lastCheck.toLocaleString()}</p>
      )}
      
      {checking && <p>Checking services...</p>}
    </div>
  );
}
```

---

## Live Execution UI

### `LiveExecutePage.tsx` - Trade Submission & Testing

**Purpose**: Test execution engine by sending trades and viewing exactly what's being sent (matches CLI output)

**Features**:
- **Trade Submission Form**:
  - Instrument selector (canonical ID: `BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN`)
  - Side selector (BUY/SELL)
  - Quantity input
  - Order Type (MARKET/LIMIT)
  - Price input (if LIMIT)
  - Execution Algorithm selection (TWAP, VWAP, Iceberg, NORMAL)
  - Algorithm parameters configuration
- **CLI Output Display**:
  - Shows exactly what's being sent to the API (matches CLI output)
  - Real-time order status updates (matches CLI format)
  - Order submission confirmation with order ID
  - Fill notifications (matches CLI format)
- **Order Monitoring**:
  - Real-time order status display
  - Order history table
  - Fill details (price, quantity, fee, timestamp)
  - Position updates

**CLI Alignment**:
- Order status format matches CLI exactly
- Position format matches CLI exactly
- Fill format matches CLI exactly
- Log format matches CLI exactly
- Real-time updates via WebSocket or polling

### `LiveStrategiesPage.tsx` - Strategy Deployment

**Purpose**: Deploy and manage trading strategies

**Features**:
- Upload strategy configuration (JSON)
- Strategy list with status (active/inactive)
- Deploy strategy to live execution
- Start/stop strategy execution
- Monitor strategy performance
- View strategy logs (matches CLI output)
- Strategy configuration editor

### `LivePositionsPage.tsx` - Position Monitoring

**Purpose**: Monitor positions across all venues

**Features**:
- Real-time position display (matches CLI format)
- Position by instrument
- Position by venue
- Aggregated positions
- P&L tracking
- Position history

### `LiveOrdersPage.tsx` - Order History

**Purpose**: View order history and status

**Features**:
- Order history table
- Filter by status (PENDING, FILLED, REJECTED, CANCELED)
- Filter by instrument
- Filter by venue
- Order details modal
- Fill details

---

## Backend Health Endpoints

### Backtest Service (`/api/health`)

```python
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "backtest",
        "port": 8000
    }
```

### Live Service (`/api/live/health`)

```python
@app.get("/api/live/health")
async def live_health_check():
    # Check database connection
    db_healthy = await check_postgres_connection()
    
    return {
        "status": "healthy" if db_healthy else "degraded",
        "service": "live",
        "port": 8001,
        "database": "connected" if db_healthy else "disconnected"
    }
```

---

## Deployment Scenarios

### Scenario 1: Backtest Only

```bash
docker-compose --profile backtest up -d
```

**Frontend Behavior**:
- ✅ Shows backtest pages (`/run`, `/compare`, `/algorithms`)
- ❌ Hides live pages (`/live/*`)
- ✅ Status page shows only backtest service

### Scenario 2: Live Only

```bash
docker-compose --profile live up -d
```

**Frontend Behavior**:
- ❌ Hides backtest pages (`/run`, `/compare`, `/algorithms`)
- ✅ Shows live pages (`/live/execute`, `/live/positions`, etc.)
- ✅ Status page shows only live service

### Scenario 3: Both Services

```bash
docker-compose --profile both up -d
# OR
docker-compose up -d  # (backward compatible)
```

**Frontend Behavior**:
- ✅ Shows all backtest pages
- ✅ Shows all live pages
- ✅ Status page shows both services

---

## Implementation Checklist

- [ ] Create `useServiceDetection` hook
- [ ] Implement health check endpoints (`/api/health`, `/api/live/health`)
- [ ] Update `App.tsx` with conditional routes
- [ ] Update `Navigation.tsx` with conditional links
- [ ] Create `StatusPage.tsx`
- [ ] Create `LiveExecutePage.tsx` (trade submission)
- [ ] Create `LivePositionsPage.tsx` (position monitoring)
- [ ] Create `LiveOrdersPage.tsx` (order history)
- [ ] Create `LiveStrategiesPage.tsx` (strategy deployment)
- [ ] Implement WebSocket or polling for real-time updates
- [ ] Ensure CLI alignment (same output format)
- [ ] Test all 3 deployment scenarios

---

*Last updated: December 2025*

