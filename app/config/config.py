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

# Define the instruments and their specific strategy parameters here.
# This allows you to tune the strategy for each pair independently.
TRADING_PAIRS = {
    "EUR_USD": {
        "rsi_length": 14,
        "overbought": 70,
        "oversold": 30,
        "news_query": "EUR USD forex news"
    },
    "GBP_USD": {
        "rsi_length": 14,
        "overbought": 70,
        "oversold": 30,
        "news_query": "GBP USD forex news"
    },
    "USD_JPY": {
        "rsi_length": 14,
        "overbought": 70,
        "oversold": 30,
        "news_query": "USD JPY forex news"
    },
    "AUD_USD": {
        "rsi_length": 14,
        "overbought": 70,
        "oversold": 30,
        "news_query": "AUD USD forex news"
    }
}