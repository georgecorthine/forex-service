# Trading Configuration / Data Model

# Define the instruments and their specific strategy parameters here.
# This allows you to tune the strategy for each pair independently.
TRADING_PAIRS = {
    "EUR_USD": {
        "rsi_length": 14,
        "overbought": 70,
        "oversold": 30
    },
    "GBP_USD": {
        "rsi_length": 14,
        "overbought": 70,
        "oversold": 30
    },
    "USD_JPY": {
        "rsi_length": 14,
        "overbought": 70,
        "oversold": 30
    },
    "AUD_USD": {
        "rsi_length": 14,
        "overbought": 70,
        "oversold": 30
    }
}