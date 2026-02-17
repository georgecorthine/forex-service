# Forex Intelligence Service

This document provides a detailed explanation of the Forex Intelligence Service, a Python-based application designed to provide real-time forex trading signals using a multi-indicator strategy.

---

## 1. Core Concepts

The service uses a combination of technical indicators and fundamental analysis (news sentiment) to generate trading signals. The strategy employs a multi-indicator confluence approach where multiple independent signals must agree before a trade is generated.

### 1.1. Technical Indicators

The service calculates the following indicators for each currency pair (`app/utils/indicators.py`):

- **RSI (Relative Strength Index):** Momentum oscillator (0-100). Used as a pullback detector within trends, not a standalone reversal signal. Configurable period (default: 14).
- **EMA (Exponential Moving Average):** Trend filter. Price above EMA = uptrend, below = downtrend. Default period: 50.
- **MACD (Moving Average Convergence Divergence):** Momentum confirmation. Uses histogram direction to confirm trade signals. Default: 12/26/9.
- **ATR (Average True Range):** Volatility measure for dynamic stop-loss placement. Default period: 14, SL multiplier: 2.0.
- **RSI Divergence:** Detects when price and RSI move in opposite directions, signaling potential reversals. Configurable lookback window (default: 20 bars).

### 1.2. News Sentiment Score

The `news_sentiment_score` is a value from -1.0 (most negative) to 1.0 (most positive) that represents the average sentiment of recent news headlines for a specific currency pair.

- **Calculation:** The service scrapes Google News for headlines related to a currency pair. It then uses the VADER sentiment analysis tool to calculate a "compound" sentiment score for each headline. The `news_sentiment_score` is the average of these compound scores.
- **Purpose:** The news sentiment score acts as the **final confirmation layer** for live trading signals. A technical signal must be confirmed by aligned news sentiment before becoming actionable.

---

## 2. How Signals are Generated

The live engine (`app/utils/engine.py`) generates signals through a multi-phase process:

### Phase 1: Data Collection
The service fetches 250 candles of OHLC data from OANDA at the pair's configured granularity (default: H4).

### Phase 2: Technical Analysis
All indicators are calculated from the price data: RSI, EMA, ATR, MACD, and RSI divergence.

### Phase 3: Signal Generation (3-Mode System)

**Mode 1 — Trend Pullback (primary):**
- BUY: Price > EMA(50) (uptrend) + RSI < 45 (pullback) + MACD confirms
- SELL: Price < EMA(50) (downtrend) + RSI > 55 (pullback) + MACD confirms

**Mode 2 — RSI Extreme (fallback, only when trend filter is off):**
- BUY: RSI < 30 + MACD confirms
- SELL: RSI > 70 + MACD confirms

**Mode 3 — RSI Divergence:**
- BUY: Bullish divergence (price lower low, RSI higher low) + MACD confirms
- SELL: Bearish divergence (price higher high, RSI lower high) + MACD confirms

**MACD Confirmation:** Buy OK if histogram > 0 or turning upward. Sell OK if histogram < 0 or turning downward.

### Phase 4: News Confirmation
A technical signal is only promoted to a final signal if news sentiment aligns:
- BUY requires `news_sentiment_score > 0.05`
- SELL requires `news_sentiment_score < -0.05`
- Otherwise the signal remains "Neutral"

All generated signals are stored in a local SQLite database for historical analysis.

### Trade Execution
When a confirmed signal is generated, the `/api/trade/{instrument}` endpoint calculates trade levels using ATR-based dynamic stops (`app/utils/risk_management.py`), returning entry price, stop-loss, take-profit, and position size.

---

## 3. Configuration

Each currency pair has independent strategy parameters (`app/config/config.py`):

```python
{
    "granularity": "H4",           # Timeframe (H4, H1, D, etc.)
    "rsi_length": 14,              # RSI calculation period
    "overbought": 70,              # RSI overbought level
    "oversold": 30,                # RSI oversold level
    "ema_period": 50,              # EMA trend filter period
    "use_trend_filter": True,      # Enable/disable EMA trend filter
    "use_macd_filter": True,       # Enable/disable MACD confirmation
    "macd_fast": 12,               # MACD fast EMA period
    "macd_slow": 26,               # MACD slow EMA period
    "macd_signal": 9,              # MACD signal line period
    "atr_period": 14,              # ATR calculation period
    "atr_sl_multiplier": 2.0,      # Stop-loss = ATR * this multiplier
    "use_divergence": True,        # Enable/disable RSI divergence detection
    "divergence_lookback": 20,     # Bars to look back for divergence
    "use_trailing_stop": True,     # Enable trailing stops (backtest only)
    "trailing_stop_atr_multiplier": 2.0,  # Trailing stop distance
    "max_hold_candles": 30,        # Time exit after N candles (backtest only)
    "news_query": "USD CHF forex news"  # News search query
}
```

**Active pairs:** USD_CHF, GBP_USD, EUR_USD, USD_JPY, AUD_USD, EUR_JPY

---

## 4. Backtesting

The backtesting system (`app/backtest/`) allows validation of the strategy against historical data.

### Running Backtests
```bash
cd app/
python -m backtest.run_backtest                    # All pairs, 1 year
python -m backtest.run_backtest USD_CHF            # Single pair
python -m backtest.run_backtest --years 3          # 3 years of data
python -m backtest.run_backtest --years 3 -g H4    # Explicit granularity
```

### Parameter Optimization
```bash
python -m backtest.optimize USD_CHF --years 1.5 --top 5
```
Tests EMA periods (20/50/100), pullback thresholds, and ATR multipliers across 18 combinations, ranked by composite score.

### Backtest Features
- Multi-indicator signal generation matching the live engine (minus news sentiment)
- ATR-based dynamic stops with fallback to fixed percentage
- Trailing stops that activate after 1:1 R:R in favor
- Time-based exits after `max_hold_candles`
- Exit reason tracking (SL, TP, TRAILING, TIME, CLOSE)
- Annualized Sharpe ratio
- Paginated data fetching for >5000 candles (multi-year backtests)
- Results saved to `app/backtest/test_results/`

---

## 5. System Architecture

The service is built with a modular architecture:

- **Data Engine:**
    - **Market Data:** OHLC price data fetched from the **OANDA API** (supports paginated fetching for large datasets)
    - **News Data:** News headlines scraped from Google News using **BeautifulSoup**

- **Analysis Layer (`app/utils/`):**
    - **`indicators.py`** — RSI, EMA, ATR, MACD, RSI divergence calculations using **Pandas**
    - **`risk_management.py`** — ATR-based dynamic stop-loss/take-profit with position sizing
    - **`engine.py`** — Live trading engine: multi-indicator signal generation + news confirmation

- **Backtesting (`app/backtest/`):**
    - **`backtest_engine.py`** — Full strategy simulation with trailing stops, time exits, exit tracking
    - **`data_fetcher.py`** — Historical data retrieval with automatic pagination
    - **`run_backtest.py`** — CLI runner with multi-instrument and multi-year support
    - **`results_analyzer.py`** — Performance metrics, assessment, CSV export
    - **`optimize.py`** — Parameter grid search optimization

- **Application & Interface:**
    - **FastAPI** backend with REST API (`app/api/routes.py`)
    - **Telegram Bot** for real-time trade alerts
    - **Swagger UI** for system management and configuration

- **Database:**
    - **SQLite** with **peewee** ORM for historical signal storage

---

## 6. API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/` | Health check |
| GET | `/api/pairs` | List configured pairs |
| GET | `/api/pairs/data` | All pair data with latest signals |
| GET | `/api/pairs/signals` | Active (non-neutral) signals only |
| GET | `/api/pair/{instrument}` | Single pair data |
| POST | `/api/trade/{instrument}` | Generate trade instruction with entry/SL/TP |
| POST | `/api/config/rsi` | Update RSI config for a pair |
| POST | `/api/control/stop` | Stop trading engine |
| POST | `/api/control/start` | Start trading engine |
