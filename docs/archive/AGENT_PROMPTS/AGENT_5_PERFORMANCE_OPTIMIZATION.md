# Agent 5: Performance & Optimization Agent

## Objective
Profile system performance, identify bottlenecks, and implement optimizations to ensure production-ready performance for backtest execution, data processing, and UI responsiveness.

## System Context
- **Backend**: Python 3.11 + NautilusTrader + FastAPI
- **Frontend**: React + TypeScript + Vite
- **Data**: Parquet files in `data_downloads/raw_tick_data/by_date/day-YYYY-MM-DD/` (mounted at `/app/data_downloads` in container)
- **Catalog**: Converted data in `backend/data/parquet/`
- **Results**: JSON files in `backend/backtest_results/`

## Key Files to Review
- `backend/backtest_engine.py` - Backtest execution
- `backend/data_converter.py` - Data conversion logic
- `backend/catalog_manager.py` - Catalog management
- `backend/strategy_evaluator.py` - Performance evaluation
- `frontend/src/pages/BacktestRunnerPage.tsx` - UI rendering
- `BACKTEST_SPEC.md` - Performance tuning section

## Optimization Areas

### 1. Backtest Execution Performance

**Current State:**
- BacktestNode orchestrates execution
- Data conversion happens on first run
- Catalog queries for time window

**Optimization Opportunities:**
- ✅ Use `BacktestEngine.reset()` for parameter sweeps (avoid reloading data)
- ✅ Optimize catalog queries (predicate pushdown)
- ✅ Batch data conversion
- ✅ Parallel processing for multiple runs

**Benchmarking:**
```bash
# Measure execution time
time curl -X POST http://localhost:8000/api/backtest/run ...

# Profile memory usage
docker stats nautilus-backend

# Check CPU usage
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

### 2. Data Conversion Performance

**Current State:**
- Automatic conversion on first run
- Caching for subsequent runs
- Batch processing (10,000 rows)

**Optimization Opportunities:**
- ✅ Increase batch size for large files
- ✅ Parallel conversion for multiple files
- ✅ Optimize timestamp conversion
- ✅ Optimize column mapping

**Measurements:**
- First run conversion time
- Subsequent run time (should use cache)
- Memory usage during conversion

### 3. Catalog Query Performance

**Current State:**
- ParquetDataCatalog with predicate pushdown
- Time window filtering

**Optimization Opportunities:**
- ✅ Verify predicate pushdown is working
- ✅ Optimize Parquet file structure
- ✅ Add indexes if needed
- ✅ Cache catalog metadata

### 4. API Performance

**Current State:**
- FastAPI with async endpoints
- JSON serialization

**Optimization Opportunities:**
- ✅ Response caching for repeated queries
- ✅ Optimize JSON serialization
- ✅ Add response compression
- ✅ Implement pagination for large results

**Benchmarking:**
```bash
# Measure API response times
curl -w "@curl-format.txt" http://localhost:8000/api/health
curl -w "@curl-format.txt" http://localhost:8000/api/backtest/results

# Load testing
ab -n 100 -c 10 http://localhost:8000/api/health
```

### 5. Frontend Performance

**Current State:**
- React components
- API calls via React Query
- No virtualization yet

**Optimization Opportunities:**
- ✅ Implement virtualization for large lists/tables
- ✅ Implement Web Workers for tick parsing
- ✅ Optimize bundle size (code splitting)
- ✅ Implement API response caching
- ✅ Lazy load heavy components

**Measurements:**
- Initial page load time
- Time to interactive
- Bundle size
- API call times

**Tools:**
- Chrome DevTools Performance tab
- React DevTools Profiler
- Lighthouse audit

### 6. Memory Optimization

**Current State:**
- Data loaded into memory
- Results stored in memory

**Optimization Opportunities:**
- ✅ Stream large files instead of loading all
- ✅ Clear unused data from memory
- ✅ Optimize data structures
- ✅ Implement memory limits

**Measurements:**
- Peak memory usage
- Memory leaks (check with memory profiler)
- Garbage collection frequency

### 7. Redis Caching (Optional)

**Current State:**
- Redis available but optional
- Not currently used

**Optimization Opportunities:**
- ✅ Cache catalog discovery results
- ✅ Cache frequently accessed configs
- ✅ Cache result summaries
- ✅ Cache dataset listings

**Implementation:**
- Add Redis client to backend
- Implement caching layer
- Measure cache hit rates
- Benchmark performance improvement

## Performance Benchmarks

### Baseline Measurements

**Backtest Execution:**
- Small dataset (5 minutes): Target < 10 seconds
- Medium dataset (1 hour): Target < 60 seconds
- Large dataset (1 day): Target < 5 minutes

**Data Conversion:**
- First run: Measure time
- Subsequent runs: Should be < 10% of first run

**API Response Times:**
- Health check: < 100ms
- List results: < 500ms
- Get result: < 200ms
- Run backtest: Depends on execution time

**Frontend:**
- Initial load: < 2 seconds
- Time to interactive: < 3 seconds
- Bundle size: < 500KB (gzipped)

## Test Scenarios

### Scenario 1: Parameter Sweep Optimization
```python
# Without reset() - recreate engine each time
for param in params:
    engine = BacktestEngine(...)
    engine.run()
    # Slow: reloads data each time

# With reset() - reuse engine
engine = BacktestEngine(...)
for param in params:
    engine.reset()
    engine.run()
    # Fast: reuses data
```

### Scenario 2: Large Dataset Performance
- Test with full day dataset
- Measure execution time
- Measure memory usage
- Identify bottlenecks

### Scenario 3: Multiple Concurrent Runs
- Test multiple API calls simultaneously
- Measure throughput
- Check for race conditions
- Verify resource usage

## Success Criteria
- ✅ Performance improvements measurable (>10% improvement)
- ✅ No functionality regressions
- ✅ Memory usage is reasonable (<2GB for typical runs)
- ✅ Frontend is responsive (<100ms for interactions)
- ✅ Backend handles load efficiently
- ✅ Caching improves repeated operations

## Deliverables
1. Performance profiling report with benchmarks
2. Optimization implementation (code changes)
3. Before/after performance comparison
4. Recommendations for further improvements
5. Performance monitoring setup (if applicable)

