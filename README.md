# Forex Intelligence Service

## Overview

This project is a Python-based service that provides real-time forex trading signals. It uses a combination of technical analysis (RSI) and fundamental analysis (news sentiment) to generate signals, which are then sent to the user via a Telegram bot.

The service is designed to be a "set it and forget it" tool for forex traders who want to be alerted to potential trading opportunities without having to constantly monitor the markets themselves.

## Features

- **Real-time Signal Generation:** The service continuously monitors the forex markets and generates signals in real time.
- **RSI-Based Technical Analysis:** Uses the Relative Strength Index (RSI) to identify overbought and oversold conditions.
- **News-Based Sentiment Analysis:** Uses news sentiment to confirm RSI signals and avoid false positives.
- **Telegram Bot Integration:** Delivers trading signals directly to your Telegram account.
- **REST API:** Provides a FastAPI-based REST API for interacting with the service and retrieving data.
- **Database Storage:** Stores all generated signals in a local SQLite database for historical analysis.

## Tech Stack

- **Language:** Python 3
- **Backend Framework:** FastAPI
- **Data Provider:** OANDA API
- **Telegram Bot:** `python-telegram-bot`
- **Data Manipulation:** Pandas
- **Sentiment Analysis:** VADER
- **Database:** SQLite with Peewee ORM

## Getting Started

### 1. Prerequisites

- Python 3.10+
- An OANDA account (demo or live) with an API key.
- A Telegram account and a Telegram bot token.

### 2. Installation

1.  Clone this repository:
    ```bash
    git clone https://github.com/georgecorthine/forex-service.git
    cd forex-service
    ```

2.  Create a virtual environment and install the dependencies:
    ```bash
    python -m venv venv
    source venv/bin/activate
    pip install -r app/requirements.txt
    ```

### 3. Configuration

The service is configured using environment variables. Set these variables in your environment before running the application.

#### Required Environment Variables

```bash
# OANDA API Configuration (Get from: https://www.oanda.com/account/tpa/personal_token)
export OANDA_API_TOKEN=<your-oanda-api-token>
export OANDA_ACCOUNT_ID=<your-oanda-account-id>

# Telegram Bot Configuration (Create bot: https://t.me/BotFather)
export TELEGRAM_BOT_TOKEN=<your-telegram-bot-token>
export TELEGRAM_CHAT_ID=<your-telegram-chat-id>
```

**Note:** The application will fail to start with a clear error message if required variables are missing.

#### Optional Environment Variables

```bash
# OANDA environment: "practice" for demo, "live" for real trading (default: practice)
export OANDA_ENVIRONMENT=practice

# CORS allowed origins - comma-separated list (default: http://localhost:3000)
export ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com

# API URL for Telegram bot to connect (default: http://localhost:8000/api)
export API_URL=http://localhost:8000/api

# Hour (UTC) to check for signals (default: 14 = 2 PM UTC)
export CHECK_HOUR=14

# Risk Management Settings
export ACCOUNT_BALANCE=10000.0    # Your account balance in USD (default: 10000)
export RISK_PERCENTAGE=1.0        # Percentage of account to risk per trade (default: 1.0%)
export REWARD_RATIO=2.0           # Reward-to-risk ratio for take profit (default: 2.0)
```

**Getting your Telegram Chat ID:**
1. Send a message to your bot
2. Visit `https://api.telegram.org/bot<your-bot-token>/getUpdates`
3. Look for the `chat.id` field in the response

### 4. Running the Service

#### Option A: Local Development

To run the service locally, execute the `start.py` script from within the `app` directory:

```bash
cd app
./start.py
```

The service will start, and you will see output in your console. The FastAPI server will be running on `http://localhost:8000`, and the Telegram bot will start polling for messages.

You can access the API documentation at `http://localhost:8000/docs`.

#### Option B: Docker

Build and run the service using Docker:

```bash
# Build the Docker image
docker build -t forex-service .

# Run the container with environment variables
docker run -d \
  --name forex-service \
  -p 8000:8000 \
  -e OANDA_API_TOKEN=your-token \
  -e OANDA_ACCOUNT_ID=your-account-id \
  -e OANDA_ENVIRONMENT=practice \
  -e TELEGRAM_BOT_TOKEN=your-bot-token \
  -e TELEGRAM_CHAT_ID=your-chat-id \
  -e ALLOWED_ORIGINS=http://localhost:3000 \
  forex-service
```

**Note:** The Dockerfile only starts the FastAPI service. To run the Telegram bot in the same container, you'll need to modify the CMD or use a process manager like `supervisord`.

#### Option C: Google Cloud Platform (GKE)

The service includes Cloud Build configuration for deployment to Google Kubernetes Engine. See [documentation/gcp.md](documentation/gcp.md) for detailed deployment instructions.

### 5. Backtesting

**⚠️ CRITICAL: Run backtests before demo trading!**

Validate your strategy on historical data:

```bash
cd app

# Test single instrument
python -m backtest.run_backtest EUR_USD

# Test all instruments
python -m backtest.run_backtest
```

**Approval Criteria:**
- Win Rate ≥ 50%
- Profit Factor ≥ 1.5
- Sharpe Ratio ≥ 0.5
- Max Drawdown ≤ 20%
- Positive total returns

See [app/backtest/README.md](app/backtest/README.md) for detailed documentation.

## Features & Improvements

### Risk Management

The service includes professional-grade risk management:

- **Position Sizing**: Automatically calculates position size based on account balance and risk percentage
- **Pip Value Calculation**: Handles both standard pairs and JPY pairs correctly
- **Stop Loss & Take Profit**: Dynamic calculation based on configurable reward-to-risk ratio
- **Risk Validation**: Enforces risk limits between 0.1% - 5% per trade

**Example:**
- Account Balance: $10,000
- Risk per Trade: 1% = $100
- Stop Loss: 50 pips
- Position Size: Automatically calculated to risk exactly $100

### Safety & Reliability

- **Memory Leak Prevention**: Error tracking uses bounded queue (max 100 errors)
- **Race Condition Protection**: Thread-safe state updates with async locks
- **Input Validation**: All user inputs validated before processing
- **Retry Logic**: News fetching includes 3 retry attempts with exponential backoff
- **Database Optimization**: Indexed queries for fast historical analysis

## API Endpoints

The FastAPI service provides the following endpoints (view full documentation at `http://localhost:8000/docs`):

- `GET /api/` - Service health and status
- `GET /api/pairs` - List configured trading pairs
- `GET /api/pairs/data` - Latest analysis for all pairs
- `GET /api/pairs/signals` - Only pairs with active BUY/SELL signals
- `GET /api/pair/{instrument}` - Detailed analysis for specific pair
- `GET /api/trade/{instrument}` - Generate trade instructions with stop-loss/take-profit
- `POST /api/config/rsi` - Update RSI thresholds for a pair
- `POST /api/control/start` - Start the trading engine
- `POST /api/control/stop` - Stop the trading engine

## Telegram Bot Commands

- `/start` - Initialize the bot
- `/status` - View market snapshot for all pairs
- `/analyze <PAIR>` - Get detailed analysis (e.g., `/analyze EUR_USD`)
- `/trade <PAIR>` - Get OANDA entry/exit instructions
- `/setrsi <PAIR> <OB> <OS>` - Update RSI thresholds (e.g., `/setrsi EUR_USD 75 25`)
- `/help` - Show command list
- `/example <COMMAND>` - Show example output

## Troubleshooting

### Application won't start
- **Error: "Missing required environment variables"**
  - Ensure `OANDA_API_TOKEN` and `OANDA_ACCOUNT_ID` are set
  - Check for typos in variable names (e.g., `OANDA_API_TOKEN` not `OANDA_API_KEY`)

### Telegram bot not responding
- Verify `TELEGRAM_BOT_TOKEN` is correct
- Check that `API_URL` points to the running FastAPI service
- Ensure the FastAPI service is running and accessible

### Docker build fails
- Verify all files are in the correct locations (`app/` directory)
- Check that `app/requirements.txt` exists
- Run `docker build --no-cache -t forex-service .` to rebuild from scratch

### CORS errors in browser
- Set `ALLOWED_ORIGINS` to include your frontend URL
- Use comma-separated list for multiple origins: `http://localhost:3000,https://yourdomain.com`

## Security

This service implements several security best practices:

- **Environment Variable Validation:** Required credentials are validated on startup - the app fails fast with clear error messages if credentials are missing
- **CORS Configuration:** Cross-Origin Resource Sharing is configurable via `ALLOWED_ORIGINS` environment variable (defaults to localhost)
- **No Hardcoded Credentials:** All sensitive configuration is managed through environment variables
- **Practice Mode Default:** OANDA API defaults to practice environment to prevent accidental real-money trading

**Production Recommendations:**
- Use a secrets management service (e.g., Google Secret Manager, AWS Secrets Manager)
- Set `ALLOWED_ORIGINS` to your specific domain(s) only
- Enable HTTPS/TLS for all external communications
- Regularly rotate API tokens and credentials
- Monitor API usage and set up alerts for unusual activity

## Disclaimer

**Trading involves significant risk.** This software is for educational and analytical purposes only. Always backtest strategies and use a demo account before risking real capital.
