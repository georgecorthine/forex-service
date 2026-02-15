import logging
import pandas as pd
from oandapyV20 import API
import oandapyV20.endpoints.instruments as instruments
from config.config import OANDA_API_TOKEN, OANDA_API_ENVIRONMENT

logger = logging.getLogger("forex_service")

class OandaClient:
    def __init__(self):
        """Initializes the OANDA API client."""
        if not OANDA_API_TOKEN:
            raise ValueError("OANDA_API_TOKEN is not set. Please set the environment variable.")
        
        self.client = API(access_token=OANDA_API_TOKEN, environment=OANDA_API_ENVIRONMENT)
        logger.info("OANDA client initialized for {} environment.".format(OANDA_API_ENVIRONMENT))

    def get_history(self, instrument: str, count: int = 250, granularity: str = "M5"):
        """
        Fetches historical OHLC data for the instrument from OANDA.
        
        :param instrument: The currency pair (e.g., "EUR_USD").
        :param count: The number of candles to retrieve.
        :param granularity: The timeframe (e.g., "M5" for 5 minutes).
        :return: A pandas DataFrame or None.
        """
        params = {
            "count": count,
            "granularity": granularity,
            "price": "M",  # Midpoint candles
        }
        
        r = instruments.InstrumentsCandles(instrument=instrument, params=params)
        
        try:
            self.client.request(r)
        except Exception as e:
            logger.error(f"OANDA API request failed: {e}")
            return None

        if not r.response.get("candles"):
            logger.warning(f"No candle data returned for {instrument} with granularity {granularity}.")
            return None

        # Parse the response into a pandas DataFrame
        records = []
        for candle in r.response["candles"]:
            records.append({
                "time": pd.to_datetime(candle["time"]),
                "Open": float(candle["mid"]["o"]),
                "High": float(candle["mid"]["h"]),
                "Low": float(candle["mid"]["l"]),
                "Close": float(candle["mid"]["c"]),
                "volume": int(candle["volume"]),
            })
        
        df = pd.DataFrame(records)
        df.set_index("time", inplace=True)
        
        return df

if __name__ == '__main__':
    # Example usage for testing
    logging.basicConfig(level=logging.INFO)
    
    # Ensure environment variables are set before running this test
    if not OANDA_API_TOKEN:
        print("Please set OANDA_API_TOKEN and OANDA_ACCOUNT_ID environment variables for testing.")
    else:
        client = OandaClient()
        df = client.get_history("EUR_USD")
        if df is not None:
            print("Successfully fetched data for EUR_USD:")
            print(df.tail())
