# Charts Browser API Documentation

This document details the API endpoints available in the Charts Browser application running on port 8080.

## Overview

The Charts Browser provides technical analysis endpoints for financial markets, including:
- Weekly stop-loss estimates (ATR-based)
- Daily stop-loss estimates (1% below swing low)
- Buy point estimates (daily swing high)
- Daily swing low estimates (for confirmation)

All endpoints return JSON responses in the following format:
```json
{
  "symbol": "AAPL",
  "swing_low_date": "2026-11-06",
  "swing_low": 338.04,
  "pivot_window": 2,
  "latest_close": 342.56,
  "latest_date": "2026-11-20"
}
```

## Endpoints

### 1. Weekly Stop-Loss Estimate
**Endpoint:** `GET /api/stop-loss?symbol=<SYMBOL>`

**Description:** Calculates stop-loss levels based on weekly swing highs and ATR (Average True Range).

**Response Format:**
```json
{
  "symbol": "AAPL",
  "swing_high_date": "2026-11-09",
  "swing_high": 360.83,
  "atr_window": 15,
  "atr": 16.27,
  "estimates": [
    {
      "multiplier": 1.5,
      "atr_distance": 24.41,
      "stop_loss": 336.42
    },
    {
      "multiplier": 2.5,
      "atr_distance": 40.68,
      "stop_loss": 322.15
    },
    {
      "multiplier": 3.5,
      "atr_distance": 57.19,
      "stop_loss": 283.64
    }
  ],
  "latest_close": 342.56,
  "latest_date": "2026-11-20"
}
```

### 2. Daily Stop-Loss Estimate
**Endpoint:** `GET /api/daily-stop-loss?symbol=<SYMBOL>`

**Description:** Calculates stop-loss levels one percent below the latest confirmed daily swing low.

**Response Format:**
```json
{
  "symbol": "AAPL",
  "swing_low_date": "2026-11-06",
  "swing_low": 338.04,
  "percent_below": 1.0,
  "stop_distance": 3.38,
  "stop_loss": 334.66,
  "latest_close": 342.56,
  "latest_date": "2026-11-20"
}
```

### 3. Daily Swing Low Estimate
**Endpoint:** `GET /api/daily-swing-low?symbol=<SYMBOL>`

**Description:** Returns the latest confirmed daily swing low, which serves as a stop-loss candidate.

**Response Format:**
```json
{
  "symbol": "AAPL",
  "swing_low_date": "2026-11-06",
  "swing_low": 338.04,
  "pivot_window": 2,
  "latest_close": 342.56,
  "latest_date": "2026-11-20"
}
```

### 4. Daily Buy Point Estimate
**Endpoint:** `GET /api/buy-point?symbol=<SYMBOL>[&amount=<USD_AMOUNT>]`

**Description:** Estimates the latest confirmed daily swing high (buy point) for daily trading.
Optionally pass a positive investment amount in USD to calculate the number of whole
shares purchasable at the buy point. The response includes `whole_shares` only when
`amount` is provided.

**Response Format:**
```json
{
  "symbol": "AAPL",
  "swing_high_date": "2026-11-13",
  "swing_high": 360.83,
  "pivot_window": 2,
  "latest_close": 342.56,
  "latest_date": "2026-11-20",
  "whole_shares": 2
}
```

### 5. Main Page
**Endpoint:** `GET /` (or `/index.html`)

**Description:** The main dashboard page displaying chart browser interface with selector cards for different chart types.

**Features:**
- Weekly Charts
- Daily Charts
- Stop Loss Estimator
- Daily Stop Loss Estimator
- Buy Point Estimator
- Daily Swing Low Estimator

## Usage Examples

### Weekly Stop-Loss (AAPL)
```bash
curl "http://127.0.0.1:8080/api/stop-loss?symbol=AAPL"
```

### Daily Swing Low (AAPL)
```bash
curl "http://127.0.0.1:8080/api/daily-swing-low?symbol=AAPL"
```

### Daily Stop-Loss (AAPL)
```bash
curl "http://127.0.0.1:8080/api/daily-stop-loss?symbol=AAPL"
```

### Buy Point (AAPL)
```bash
curl "http://127.0.0.1:8080/api/buy-point?symbol=AAPL"
```

### Buy Point with Investment Amount (AAPL)
```bash
curl "http://127.0.0.1:8080/api/buy-point?symbol=AAPL&amount=1000"
```

## Technical Details

- **Data Source:** Yahoo Finance (split/dividend-adjusted)
- **Timeframes:**
  - Weekly: 5 years of data
  - Daily: 1 year of data
- **Response Format:** JSON
- **Error Handling:**
  - 400: Invalid symbol format
  - 502: Data retrieval failure
  - 422: Validation error (e.g., insufficient data)

## Development

The Charts Browser runs on port 8080 and can be accessed via:
- Main dashboard: `http://127.0.0.1:8080/`
- API endpoints: `http://127.0.0.1:8080/api/...`

The service is built with Python and uses Yahoo Finance data to provide technical analysis for financial markets.