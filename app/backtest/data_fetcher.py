"""
Data fetcher for backtesting - retrieves historical data from OANDA.
"""
import pandas as pd
import logging
from datetime import datetime, timedelta
from utils.oanda_client import OandaClient

logger = logging.getLogger("backtest")


class BacktestDataFetcher:
    """Fetches historical data for backtesting."""

    def __init__(self):
        """Initialize the data fetcher with OANDA client."""
        try:
            self.client = OandaClient()
            logger.info("OANDA client initialized for backtesting")
        except Exception as e:
            logger.error(f"Failed to initialize OANDA client: {e}")
            self.client = None

    def fetch_data(self,
                   instrument: str,
                   granularity: str = "D",
                   count: int = 5000) -> pd.DataFrame:
        """
        Fetch historical data for backtesting.

        Args:
            instrument: Trading pair (e.g., "EUR_USD")
            granularity: Candle granularity (D=Daily, H4=4-hour, H1=1-hour, M15=15-min)
            count: Number of candles to fetch (max 5000)

        Returns:
            DataFrame with OHLC data
        """
        if not self.client:
            raise ValueError("OANDA client not available. Check credentials.")

        logger.info(f"Fetching {count} {granularity} candles for {instrument}")

        data = self.client.get_history(
            instrument=instrument,
            count=min(count, 5000),  # OANDA max
            granularity=granularity
        )

        if data is None or data.empty:
            raise ValueError(f"No data returned for {instrument}")

        logger.info(f"Fetched {len(data)} candles from {data.index[0]} to {data.index[-1]}")

        return data

    def fetch_multiple_instruments(self,
                                   instruments: list,
                                   granularity: str = "D",
                                   count: int = 5000) -> dict:
        """
        Fetch data for multiple instruments.

        Args:
            instruments: List of trading pairs
            granularity: Candle granularity
            count: Number of candles per instrument

        Returns:
            Dictionary mapping instrument -> DataFrame
        """
        data_dict = {}

        for instrument in instruments:
            try:
                data = self.fetch_data(instrument, granularity, count)
                data_dict[instrument] = data
            except Exception as e:
                logger.error(f"Failed to fetch data for {instrument}: {e}")

        return data_dict

    def save_to_csv(self, data: pd.DataFrame, instrument: str, directory: str = "backtest/data"):
        """Save data to CSV for later use."""
        import os
        os.makedirs(directory, exist_ok=True)

        filename = f"{directory}/{instrument}_{datetime.now().strftime('%Y%m%d')}.csv"
        data.to_csv(filename)
        logger.info(f"Saved data to {filename}")

        return filename

    def load_from_csv(self, filename: str) -> pd.DataFrame:
        """Load data from CSV."""
        data = pd.read_csv(filename, index_col=0, parse_dates=True)
        logger.info(f"Loaded {len(data)} candles from {filename}")
        return data
