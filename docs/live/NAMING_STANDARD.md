# Component Naming Standards

> Standardized component names across all live execution documentation

## ✅ Standardized Component Names

All documentation uses these exact names:

| Component | Standard Name | Alternative Names (Deprecated) |
|-----------|--------------|-------------------------------|
| Main Orchestrator | `LiveExecutionOrchestrator` | `LiveEngine` ❌ |
| TradingNode Wrapper | `LiveTradingNode` | `TradingNode` (direct) ❌ |
| Order Management | `UnifiedOrderManager` | `UnifiedOMS` ❌ |
| Position Tracking | `UnifiedPositionTracker` | `PositionTracker` ❌ |
| Risk Engine | `PreTradeRiskEngine` | `RiskEngine` ❌ |
| Router | `LiveSmartRouter` | `SmartRouter` (base) ✅ |

## File Locations

| Component | File Path |
|-----------|-----------|
| `LiveExecutionOrchestrator` | `backend/live/orchestrator.py` |
| `LiveTradingNode` | `backend/live/trading_node.py` |
| `UnifiedOrderManager` | `backend/live/oms.py` |
| `UnifiedPositionTracker` | `backend/live/positions.py` |
| `PreTradeRiskEngine` | `backend/live/risk.py` |
| `LiveSmartRouter` | `backend/live/router.py` |

## GCS Bucket Names

| Purpose | Bucket Name |
|---------|-------------|
| Instruments | `gs://instruments-store-cefi-central-element-323112/` |
| Market Data | `gs://market-data-tick-cefi-central-element-323112/` |
| Execution Results | `gs://execution-store-cefi-central-element-323112/` ✅ |

---

*Last updated: December 2025*
*Status: Standardized across all documentation*

