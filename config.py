# Trading Configuration / Data Model

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