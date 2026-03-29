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
    "GBP_USD": {
        "granularity": os.getenv("GBP_USD_GRANULARITY", "H4"),
        "rsi_length": 14,
        "overbought": 70,
        "oversold": 30,
        # Trend filter (EMA)
        "ema_period": 50,
        "use_trend_filter": True,
        # MACD confirmation
        "use_macd_filter": True,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        # ATR-based stops
        "atr_period": 14,
        "atr_sl_multiplier": 2.0,
        # RSI divergence
        "use_divergence": True,
        "divergence_lookback": 20,
        # Trailing stop
        "use_trailing_stop": True,
        "trailing_stop_atr_multiplier": 2.0,
        # Time-based exit (max H4 candles = ~3.3 days)
        "max_hold_candles": 30,
        # Regime detection
        "use_regime_filter": True,
        "adx_period": 14,
        "adx_trending_threshold": 25.0,
        "adx_ranging_threshold": 20.0,
        "atr_volatility_multiplier": 1.5,
        "atr_volatility_ma_length": 50,
        # Multi-timeframe confirmation
        "use_mtf_confirmation": True,
        "mtf_ema_period": 50,
        "news_query": "GBP USD forex news"
    },
    "USD_JPY": {
        "granularity": os.getenv("USD_JPY_GRANULARITY", "H4"),
        "rsi_length": 14,
        "overbought": 70,
        "oversold": 30,
        "ema_period": 50,
        "use_trend_filter": True,
        "use_macd_filter": True,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "atr_period": 14,
        "atr_sl_multiplier": 2.0,
        "use_divergence": True,
        "divergence_lookback": 20,
        "use_trailing_stop": True,
        "trailing_stop_atr_multiplier": 2.0,
        "max_hold_candles": 30,
        # Regime detection
        "use_regime_filter": True,
        "adx_period": 14,
        "adx_trending_threshold": 25.0,
        "adx_ranging_threshold": 20.0,
        "atr_volatility_multiplier": 1.5,
        "atr_volatility_ma_length": 50,
        # Multi-timeframe confirmation
        "use_mtf_confirmation": True,
        "mtf_ema_period": 50,
        "news_query": "USD JPY forex news"
    },
    "EUR_JPY": {
        "granularity": os.getenv("EUR_JPY_GRANULARITY", "H4"),
        "rsi_length": 14,
        "overbought": 70,
        "oversold": 30,
        "ema_period": 50,
        "use_trend_filter": True,
        "use_macd_filter": True,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "atr_period": 14,
        "atr_sl_multiplier": 2.0,
        "use_divergence": True,
        "divergence_lookback": 20,
        "use_trailing_stop": True,
        "trailing_stop_atr_multiplier": 2.0,
        "max_hold_candles": 30,
        # Regime detection
        "use_regime_filter": True,
        "adx_period": 14,
        "adx_trending_threshold": 25.0,
        "adx_ranging_threshold": 20.0,
        "atr_volatility_multiplier": 1.5,
        "atr_volatility_ma_length": 50,
        # Multi-timeframe confirmation
        "use_mtf_confirmation": True,
        "mtf_ema_period": 50,
        "news_query": "EUR JPY forex news"
    },
}
