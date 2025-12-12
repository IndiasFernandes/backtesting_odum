# Sports Betting Venues

> **Related Documentation**:
> - [`00_PROJECT_OVERVIEW.md`](./00_PROJECT_OVERVIEW.md) - System architecture and common concepts
> - [`01_CEFI_VENUES.md`](./01_CEFI_VENUES.md) - CeFi venues
> - [`02_DEFI_VENUES.md`](./02_DEFI_VENUES.md) - DeFi venues
> - [`03_TRADFI_VENUES.md`](./03_TRADFI_VENUES.md) - TradFi venues

---

## Table of Contents

1. [Overview](#overview)
2. [Betfair](#betfair)
3. [Market Types](#market-types)
4. [Execution Flow Examples](#execution-flow-examples)
5. [Position Tracking](#position-tracking)

---

## Overview

Sports betting venues enable trading on sports event outcomes through betting exchanges. The execution system routes orders to sports betting venues via their APIs, primarily Betfair Exchange.

### Supported Venues

| Venue | Venue Code | Supported Markets | Status |
|-------|------------|------------------|--------|
| **Betfair** | `BETFAIR` | MATCH_WINNER, TOTAL_GOALS_OU_2_5, BTTS | ⏳ Planned |

### Common Characteristics

- **Order Types**: BACK (bet for), LAY (bet against)
- **Stake Sizing**: Kelly criterion recommended
- **Market Format**: Competition code, kickoff time, team slugs
- **Position Tracking**: Positions tracked as SPOT_ASSET with outcome selection

---

## Betfair

### Venue Information

**Venue Code**: `BETFAIR`

**Supported Instrument Types**:
- `MATCH_WINNER` (1X2 market)
- `TOTAL_GOALS_OU_2_5` (Over/Under 2.5 goals)
- `BTTS` (Both Teams To Score)

### Instrument ID Format

```
FOOTBALL:BETFAIR:MATCH_WINNER:ENG-PREMIER_LEAGUE:20250315T1500:ARSENAL-LIVERPOOL
FOOTBALL:BETFAIR:TOTAL_GOALS_OU_2_5:ENG-PREMIER_LEAGUE:20250315T1500:ARSENAL-LIVERPOOL@2.5
FOOTBALL:BETFAIR:BTTS:ENG-PREMIER_LEAGUE:20250315T1500:ARSENAL-LIVERPOOL
```

### Execution Attributes

- **API**: `https://api.betfair.com/exchange/betting/json-rpc/v1`
- **Authentication**: Application Key + Session Token
- **Order Types**: `BACK` (bet for), `LAY` (bet against)
- **Stake Sizing**: Kelly criterion recommended
- **Markets**: Match Odds (Home/Draw/Away), Over/Under, BTTS

### Market Format

**Competition Code**: Format like `ENG-PREMIER_LEAGUE`, `GER-BUNDESLIGA`, etc.

**Kickoff Time**: `YYYYMMDDTHHMM` format (UTC)
- Example: `20250315T1500` = March 15, 2025 at 15:00 UTC

**Team Slugs**: Normalized team names (e.g., `ARSENAL-LIVERPOOL`)

### Betfair Market ID Mapping

- Instrument ID → Betfair `eventId` + `marketId` + `selectionId`
- Market type codes: `MATCH_ODDS` (1X2), `TOTAL_GOALS` (O/U), `BOTH_TEAMS_TO_SCORE` (BTTS)

### Execution Flow

1. Parse instrument ID to extract competition, kickoff, teams
2. Match to Betfair event via API-Football fixture ID
3. Fetch Betfair market catalogue for event
4. Map instrument type to Betfair market type code
5. Execute BACK/LAY order with stake sizing
6. Return execution result with bet ID

---

## Market Types

### MATCH_WINNER (1X2 Market)

**Purpose**: Bet on match outcome (Home win, Draw, Away win)

**Instrument ID Format**:
```
FOOTBALL:BETFAIR:MATCH_WINNER:COMPETITION:YYYYMMDDTHHMM:HOME-AWAY
```

**Examples**:
```
FOOTBALL:BETFAIR:MATCH_WINNER:ENG-PREMIER_LEAGUE:20250315T1500:ARSENAL-LIVERPOOL
FOOTBALL:BETFAIR:MATCH_WINNER:GER-BUNDESLIGA:20250316T1430:BAYERN-MUNICH-BORUSSIA-DORTMUND
```

**Selections**:
- `Home`: Home team wins
- `Draw`: Match ends in draw
- `Away`: Away team wins

**Order Example**:
```json
{
  "operation_id": "bet_001",
  "operation": "bet",
  "instrument_key": "FOOTBALL:BETFAIR:MATCH_WINNER:ENG-PREMIER_LEAGUE:20250315T1500:ARSENAL-LIVERPOOL",
  "venue": "BETFAIR",
  "side": "BACK",
  "amount": 100.0,
  "odds": 2.5,
  "selection": "Home",
  "expected_deltas": {
    "FOOTBALL:BETFAIR:MATCH_WINNER:ENG-PREMIER_LEAGUE:20250315T1500:ARSENAL-LIVERPOOL:Home": 1
  },
  "strategy_id": "sports_ml_v1"
}
```

---

### TOTAL_GOALS_OU_2_5 (Over/Under 2.5 Goals)

**Purpose**: Bet on whether total goals will be over or under 2.5

**Instrument ID Format**:
```
FOOTBALL:BETFAIR:TOTAL_GOALS_OU_2_5:COMPETITION:YYYYMMDDTHHMM:HOME-AWAY@2.5
```

**Examples**:
```
FOOTBALL:BETFAIR:TOTAL_GOALS_OU_2_5:ENG-PREMIER_LEAGUE:20250315T1500:ARSENAL-LIVERPOOL@2.5
FOOTBALL:BETFAIR:TOTAL_GOALS_OU_2_5:GER-BUNDESLIGA:20250316T1430:BAYERN-MUNICH-BORUSSIA-DORTMUND@2.5
```

**Selections**:
- `Over`: Total goals > 2.5
- `Under`: Total goals < 2.5

**Note**: The line parameter (`@2.5`) specifies the over/under threshold. Other thresholds (e.g., `@1.5`, `@3.5`) would use separate instrument IDs.

**Order Example**:
```json
{
  "operation_id": "bet_002",
  "operation": "bet",
  "instrument_key": "FOOTBALL:BETFAIR:TOTAL_GOALS_OU_2_5:ENG-PREMIER_LEAGUE:20250315T1500:ARSENAL-LIVERPOOL@2.5",
  "venue": "BETFAIR",
  "side": "BACK",
  "amount": 50.0,
  "odds": 1.8,
  "selection": "Over",
  "expected_deltas": {
    "FOOTBALL:BETFAIR:TOTAL_GOALS_OU_2_5:ENG-PREMIER_LEAGUE:20250315T1500:ARSENAL-LIVERPOOL@2.5:Over": 1
  }
}
```

---

### BTTS (Both Teams To Score)

**Purpose**: Bet on whether both teams will score (YES/NO)

**Instrument ID Format**:
```
FOOTBALL:BETFAIR:BTTS:COMPETITION:YYYYMMDDTHHMM:HOME-AWAY
```

**Examples**:
```
FOOTBALL:BETFAIR:BTTS:ENG-PREMIER_LEAGUE:20250315T1500:ARSENAL-LIVERPOOL
FOOTBALL:BETFAIR:BTTS:GER-BUNDESLIGA:20250316T1430:BAYERN-MUNICH-BORUSSIA-DORTMUND
```

**Selections**:
- `Yes`: Both teams score
- `No`: At least one team doesn't score

**Order Example**:
```json
{
  "operation_id": "bet_003",
  "operation": "bet",
  "instrument_key": "FOOTBALL:BETFAIR:BTTS:ENG-PREMIER_LEAGUE:20250315T1500:ARSENAL-LIVERPOOL",
  "venue": "BETFAIR",
  "side": "BACK",
  "amount": 75.0,
  "odds": 1.6,
  "selection": "Yes",
  "expected_deltas": {
    "FOOTBALL:BETFAIR:BTTS:ENG-PREMIER_LEAGUE:20250315T1500:ARSENAL-LIVERPOOL:Yes": 1
  }
}
```

---

## Execution Flow Examples

### Example 1: Sports Betting Order (Betfair)

**Input**: Order instruction
```json
{
  "operation_id": "bet_001",
  "operation": "bet",
  "instrument_key": "FOOTBALL:BETFAIR:MATCH_WINNER:ENG-PREMIER_LEAGUE:20250315T1500:ARSENAL-LIVERPOOL",
  "venue": "BETFAIR",
  "side": "BACK",
  "amount": 100.0,
  "odds": 2.5,
  "selection": "Home",
  "expected_deltas": {
    "FOOTBALL:BETFAIR:MATCH_WINNER:ENG-PREMIER_LEAGUE:20250315T1500:ARSENAL-LIVERPOOL:Home": 1
  },
  "strategy_id": "sports_ml_v1"
}
```

**Execution Flow**:
1. Parse instrument ID → venue=`BETFAIR`, type=`MATCH_WINNER`, payload=`ENG-PREMIER_LEAGUE:20250315T1500:ARSENAL-LIVERPOOL`
2. Extract selection from order (`selection: "Home"`)
3. Route to BetfairMiddlewareAdapter
4. Place BACK order via Betfair Exchange API:
   - Market ID: Extracted from instrument key
   - Selection ID: Home (Arsenal)
   - Stake: 100.0
   - Odds: 2.5
5. Return execution result with bet ID

**Output**: Execution response
```json
{
  "execution_id": "exec_003",
  "status": "success",
  "venue": "BETFAIR",
  "instrument_id": "FOOTBALL:BETFAIR:MATCH_WINNER:ENG-PREMIER_LEAGUE:20250315T1500:ARSENAL-LIVERPOOL",
  "betfair_order_id": "123.456789",
  "stake": 100.0,
  "odds": 2.5,
  "potential_payout": 250.0,
  "position_deltas": {
    "FOOTBALL:BETFAIR:MATCH_WINNER:ENG-PREMIER_LEAGUE:20250315T1500:ARSENAL-LIVERPOOL:Home": 1
  }
}
```

**Note**: Sports betting positions are tracked as SPOT_ASSET positions with the outcome selection appended to the instrument key (e.g., `:Home`, `:Draw`, `:Away`).

---

## Position Tracking

### Position Instrument Keys

Sports betting positions are tracked as SPOT_ASSET positions with the outcome selection appended to the instrument key:

**MATCH_WINNER**:
- `FOOTBALL:BETFAIR:MATCH_WINNER:ENG-PREMIER_LEAGUE:20250315T1500:ARSENAL-LIVERPOOL:Home`
- `FOOTBALL:BETFAIR:MATCH_WINNER:ENG-PREMIER_LEAGUE:20250315T1500:ARSENAL-LIVERPOOL:Draw`
- `FOOTBALL:BETFAIR:MATCH_WINNER:ENG-PREMIER_LEAGUE:20250315T1500:ARSENAL-LIVERPOOL:Away`

**TOTAL_GOALS_OU_2_5**:
- `FOOTBALL:BETFAIR:TOTAL_GOALS_OU_2_5:ENG-PREMIER_LEAGUE:20250315T1500:ARSENAL-LIVERPOOL@2.5:Over`
- `FOOTBALL:BETFAIR:TOTAL_GOALS_OU_2_5:ENG-PREMIER_LEAGUE:20250315T1500:ARSENAL-LIVERPOOL@2.5:Under`

**BTTS**:
- `FOOTBALL:BETFAIR:BTTS:ENG-PREMIER_LEAGUE:20250315T1500:ARSENAL-LIVERPOOL:Yes`
- `FOOTBALL:BETFAIR:BTTS:ENG-PREMIER_LEAGUE:20250315T1500:ARSENAL-LIVERPOOL:No`

### Position Values

- **Position Value**: 1 = bet placed, 0 = no bet
- **BACK Position**: Positive value (betting for the outcome)
- **LAY Position**: Negative value (betting against the outcome)

### Settlement

After match completion:
- Winning bets: Position value converted to payout amount
- Losing bets: Position value set to 0
- Payout calculation: `stake × odds` for BACK bets

---

## Order Type Mapping

### Sports Betting Order Types

| System Order Type | Betfair | Description |
|-------------------|---------|-------------|
| `BACK` | `BACK` | Bet for selection (betting that outcome will happen) |
| `LAY` | `LAY` | Bet against selection (betting that outcome won't happen) |

### Order Type Details

**BACK Orders**:
- Betting for the selection to win
- If selection wins, receive `stake × odds`
- If selection loses, lose `stake`
- Example: BACK Arsenal to win at odds 2.5 with stake 100 → if Arsenal wins, receive 250 (profit 150)

**LAY Orders**:
- Betting against the selection (acting as bookmaker)
- If selection wins, pay `stake × odds`
- If selection loses, receive `stake`
- Example: LAY Arsenal to win at odds 2.5 with stake 100 → if Arsenal loses, receive 100 (profit 100)

---

## Stake Sizing

### Kelly Criterion

**Recommended**: Use Kelly criterion for optimal stake sizing

**Formula**:
```
stake = (bp - q) / b
```

Where:
- `b` = decimal odds - 1
- `p` = probability of winning (from ML model)
- `q` = probability of losing = 1 - p

**Example**:
- Odds: 2.5 (b = 1.5)
- ML predicted probability: 0.45 (p = 0.45, q = 0.55)
- Kelly stake = (1.5 × 0.45 - 0.55) / 1.5 = 0.0833 = 8.33% of bankroll

**Fractional Kelly**: Often use fractional Kelly (e.g., 0.5 × Kelly) to reduce risk

---

## Backtesting for Sports Betting

### Data Sources

- **Historical Odds Data**: Betfair historical odds data
- **Match Results**: API-Football or similar for match outcomes
- **Market Microstructure**: Historical order book data from Betfair

### Execution Simulation

- **Odds Simulation**: Use historical odds at time of bet
- **Fill Simulation**: Model order matching based on available liquidity
- **Settlement Simulation**: Apply match results to calculate payouts
- **Kelly Criterion Simulation**: Simulate stake sizing based on ML predictions

### Backtesting Flow

```
Pre-generated Orders (from Strategy Service)
  ↓
Read Orders from GCS
  ↓
Query Historical Odds Data
  ↓
Simulate Order Execution
  ↓
Apply Match Results
  ↓
Calculate Payouts
  ↓
Return Execution Results
  ↓
Update Strategy Positions
```

---

## Related Documentation

- **Project Overview**: [`00_PROJECT_OVERVIEW.md`](./00_PROJECT_OVERVIEW.md)
- **CeFi Venues**: [`01_CEFI_VENUES.md`](./01_CEFI_VENUES.md)
- **DeFi Venues**: [`02_DEFI_VENUES.md`](./02_DEFI_VENUES.md)
- **TradFi Venues**: [`03_TRADFI_VENUES.md`](./03_TRADFI_VENUES.md)





