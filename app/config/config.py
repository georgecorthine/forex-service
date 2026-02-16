import os
import sys

# --- OANDA Configuration ---
# Securely load credentials from environment variables
OANDA_API_TOKEN = os.getenv("OANDA_API_TOKEN")
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID")
OANDA_API_ENVIRONMENT = os.getenv("OANDA_ENVIRONMENT", "practice")  # Use "live" for real money

# --- Environment Variable Validation ---
REQUIRED_ENV_VARS = {
    "OANDA_API_TOKEN": OANDA_API_TOKEN,
    "OANDA_ACCOUNT_ID": OANDA_ACCOUNT_ID,
}

missing_vars = [var_name for var_name, var_value in REQUIRED_ENV_VARS.items() if not var_value]

if missing_vars:
    error_msg = (
        f"❌ CRITICAL: Missing required environment variables: {', '.join(missing_vars)}\n"
        f"Please set these variables before starting the application.\n"
        f"Example: export OANDA_API_TOKEN='your-token-here'"
    )
    print(error_msg, file=sys.stderr)
    raise EnvironmentError(error_msg)

# --- Trading Configuration / Data Model ---

# Global default granularity (can be overridden by env var or per-pair)
DEFAULT_GRANULARITY = os.getenv("DEFAULT_GRANULARITY", "D")  # D, H4, H1, etc.

# Define the instruments and their specific strategy parameters here.
# This allows you to tune the strategy for each pair independently.
TRADING_PAIRS = {
    "USD_CHF": {
        "granularity": os.getenv("USD_CHF_GRANULARITY", DEFAULT_GRANULARITY),
        "rsi_length": 14,
        "overbought": 70,
        "oversold": 30,
        "ma_period": 50,
        "use_trend_filter": False,
        "news_query": "USD CHF forex news"
    },
    "GBP_USD": {
        "granularity": os.getenv("GBP_USD_GRANULARITY", DEFAULT_GRANULARITY),
        "rsi_length": 14,
        "overbought": 70,
        "oversold": 30,
        "ma_period": 50,
        "use_trend_filter": False,
        "news_query": "GBP USD forex news"
    },
    # Removed pairs (poor performance on 1-year backtest):
    # EUR_JPY: -1.03% return, 29.4% win rate, 0.83 profit factor (LOSING)
    # EUR_USD: +0.47% return, 35.7% win rate, 1.11 profit factor (barely profitable)
    # USD_JPY: +0.47% return, 36.4% win rate, 1.14 profit factor (poor)
    # AUD_USD: +1.77% return, 34.7% win rate, 1.06 profit factor (poor)
}