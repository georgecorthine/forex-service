import yfinance as yf
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger("forex_service")

class YFinanceClient:
    def __init__(self):
        pass

    async def get_current_price(self, instrument: str):
        """
        Fetches the latest price using yfinance (Yahoo Finance).
        Instrument expected format: "EUR_USD" -> converts to "EURUSD=X"
        """
        loop = asyncio.get_running_loop()
        
        # Convert our internal format "EUR_USD" to Yahoo's format "EURUSD=X"
        symbol = instrument.replace("_", "") + "=X"
        
        try:
            # yfinance is a blocking library, so we run it in a separate thread
            # to ensure we don't freeze the FastAPI server.
            def fetch_price():
                ticker = yf.Ticker(symbol)
                # fast_info provides the latest available price efficiently
                return ticker.fast_info.last_price

            price = await loop.run_in_executor(None, fetch_price)
            
            if price:
                return {
                    "instrument": instrument,
                    "bid": price, # Yahoo provides a single 'last' price, not a spread
                    "ask": price,
                    "time": datetime.now().isoformat()
                }
            return None
            
        except Exception as e:
            logger.error(f"YFinance Error for {symbol}: {e}")
            return None

    async def get_history(self, instrument: str, period: str = "1d", interval: str = "5m"):
        """
        Fetches historical OHLC data for the instrument.
        Default: Last 1 day of 5-minute candles.
        """
        loop = asyncio.get_running_loop()
        symbol = instrument.replace("_", "") + "=X"
        
        def fetch_data():
            ticker = yf.Ticker(symbol)
            # Fetch history (returns a Pandas DataFrame)
            return ticker.history(period=period, interval=interval)

        try:
            return await loop.run_in_executor(None, fetch_data)
        except Exception as e:
            logger.error(f"YFinance History Error for {symbol}: {e}")
            return None