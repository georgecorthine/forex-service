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

        return self._parse_candles(r.response, instrument, granularity)

    def get_history_range(self, instrument: str, from_time: str, to_time: str = None,
                          granularity: str = "H4"):
        """
        Fetches historical data for a date range. Uses 'from'/'to' params instead of 'count'.

        :param instrument: The currency pair (e.g., "EUR_USD").
        :param from_time: RFC3339 start time (e.g., "2023-01-01T00:00:00Z").
        :param to_time: RFC3339 end time. If None, fetches up to now.
        :param granularity: The timeframe.
        :return: A pandas DataFrame or None.
        """
        params = {
            "from": from_time,
            "granularity": granularity,
            "price": "M",
            "count": 5000,
        }
        if to_time:
            params["to"] = to_time
            del params["count"]

        r = instruments.InstrumentsCandles(instrument=instrument, params=params)

        try:
            self.client.request(r)
        except Exception as e:
            logger.error(f"OANDA API range request failed: {e}")
            return None

        return self._parse_candles(r.response, instrument, granularity)

    def _parse_candles(self, response, instrument, granularity):
        """Parse OANDA candle response into a DataFrame."""
        if not response.get("candles"):
            logger.warning(f"No candle data returned for {instrument} with granularity {granularity}.")
            return None

        records = []
        for candle in response["candles"]:
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
