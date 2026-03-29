# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Forex Intelligence Service is a Python-based real-time forex trading signal generator that combines technical analysis (RSI) and fundamental analysis (news sentiment) to generate trading signals. Signals are delivered via both a REST API and a Telegram bot.

## Development Setup

### Installation

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r app/requirements.txt
```

### Environment Variables

Create a `.env` file in the `app/` directory with:

```
OANDA_API_TOKEN=<your-oanda-api-key>
OANDA_ACCOUNT_ID=<your-oanda-account-id>
TELEGRAM_BOT_TOKEN=<your-telegram-bot-token>
TELEGRAM_CHAT_ID=<your-telegram-chat-id>
```

Get `TELEGRAM_CHAT_ID` by sending a message to your bot, then visit:
`https://api.telegram.org/bot<your-bot-token>/getUpdates`

### Running the Service

```bash
# Start both FastAPI server and Telegram bot
cd app
./start.py

# Or run FastAPI server only
cd app
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Or run Telegram bot only
cd app
python telegram_bot.py
```

The FastAPI server runs on `http://localhost:8000` with interactive API docs at `http://localhost:8000/docs`.

### Docker

```bash
# Build image
docker build -t forex-service .

# Run container (must pass environment variables)
docker run -p 8000:8000 \
  -e OANDA_API_TOKEN=your_token \
  -e OANDA_ACCOUNT_ID=your_account \
  forex-service
```

### Deployment

GCP Cloud Build configuration is in [cloudbuild.yaml](cloudbuild.yaml). The service can be deployed to:
- Google Compute Engine (GCE) - Option 1 (currently commented out)
- Google Kubernetes Engine (GKE) - Option 2 (active)

## Architecture

### Core Components

1. **FastAPI Application** ([main.py](app/main.py))
   - REST API server with CORS middleware
   - Lifespan context manager handles startup/shutdown
   - Initializes database and starts trading engine on startup
   - Gracefully stops engine on shutdown

2. **Trading Engine** ([utils/engine.py](app/utils/engine.py))
   - Runs continuously via `asyncio` in background
   - Analyzes configured trading pairs every 60 seconds
   - Uses circuit breaker pattern (3 failure threshold per instrument)
   - Executes three-phase analysis: data collection, technical analysis (RSI), fundamental analysis (news sentiment)
   - Stores signals in database and updates global state

3. **Telegram Bot** ([telegram_bot.py](app/telegram_bot.py))
   - Separate process started by [start.py](app/start.py)
   - Sends trading signals to configured Telegram chat
   - Can run independently or alongside FastAPI

4. **Database Layer** ([database.py](app/database.py))
   - SQLite database with Peewee ORM
   - `db_wrapper` decorator handles connection lifecycle
   - `db_context` context manager for manual connection handling
   - Stores historical signals in `SignalHistory` model

### Key Modules

- **[config/config.py](app/config/config.py)**: Trading pair configuration with per-pair RSI thresholds and news queries
- **[models/model.py](app/models/model.py)**: Peewee database models and Pydantic API schemas
- **[api/routes.py](app/api/routes.py)**: REST API endpoints for signals, pair data, and engine control
- **[utils/oanda_client.py](app/utils/oanda_client.py)**: OANDA API client for forex price data
- **[utils/news_scraper.py](app/utils/news_scraper.py)**: News scraping and VADER sentiment analysis
- **[utils/indicators.py](app/utils/indicators.py)**: Technical indicators (RSI calculation)
- **[utils/store.py](app/utils/store.py)**: Global state dictionary for sharing data across components

### Data Flow

1. Trading engine loop fetches historical price data from OANDA for each configured instrument
2. RSI is calculated from price history (14-period default)
3. News sentiment is fetched and analyzed using VADER
4. Signal is confirmed only when RSI and news sentiment align:
   - **BUY**: RSI < oversold threshold (30) AND news sentiment > 0.05
   - **SELL**: RSI > overbought threshold (70) AND news sentiment < -0.05
5. Signal is saved to SQLite database and updated in global state
6. API exposes current signals via endpoints
7. Telegram bot (if running) notifies user of new signals

### State Management

Global state is stored in [utils/store.py](app/utils/store.py) with this structure:

```python
state = {
    "running": bool,              # Engine status
    "latest_signal": {            # Per-instrument data
        "EUR_USD": {
            "price": float,
            "rsi": float,
            "sentiment": str,     # "BUY (Confirmed by News)" | "SELL (Confirmed by News)" | "Neutral"
            "news_sentiment_score": float,
            "timestamp": str
        },
        ...
    },
    "errors": []                  # Error log
}
```

### Adding New Trading Pairs

Edit [config/config.py](app/config/config.py) and add to `TRADING_PAIRS` dictionary:

```python
"USD_CAD": {
    "rsi_length": 14,
    "overbought": 70,
    "oversold": 30,
    "news_query": "USD CAD forex news"
}
```

The engine will automatically pick up new pairs on restart.

### Database Schema

**SignalHistory** table (via Peewee ORM):
- `timestamp`: DateTimeField (auto, unique composite with instrument)
- `instrument`: CharField
- `sentiment`: CharField
- `price`: FloatField
- `rsi`: FloatField
- `news_sentiment_score`: FloatField

Database file: `app/forex_signals.db` (SQLite)

## API Endpoints

- `GET /api/` - Service health check and engine status
- `GET /api/pairs` - List configured trading pairs
- `GET /api/pairs/data` - Get analysis for all pairs
- `GET /api/pairs/signals` - Get only active BUY/SELL signals
- `GET /api/pair/{instrument}` - Get data for specific pair
- `GET /api/trade/{instrument}` - Get MT5 trade instructions (entry, SL, TP)
- `POST /api/config/rsi` - Update RSI thresholds for a pair
- `POST /api/control/start` - Start the trading engine
- `POST /api/control/stop` - Stop the trading engine

## Important Constants

- **RSI_PERIOD**: 14 (in [utils/engine.py](app/utils/engine.py))
- **POSITIVE_SENTIMENT_THRESHOLD**: 0.05
- **NEGATIVE_SENTIMENT_THRESHOLD**: -0.05
- **FAILURE_THRESHOLD**: 3 (circuit breaker)
- **Analysis Loop Interval**: 60 seconds

## Notes

- The service uses OANDA's practice environment by default (`OANDA_API_ENVIRONMENT = "practice"` in config)
- All forex prices use appropriate precision: 3 decimals for JPY pairs, 5 for others
- BeautifulSoup XML warnings are suppressed when parsing RSS feeds
- The trading engine runs asynchronously and can be controlled via API endpoints
- Each instrument analysis runs concurrently using `asyncio.create_task()`
