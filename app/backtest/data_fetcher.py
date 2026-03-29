"""
Data fetcher for backtesting - retrieves historical data from OANDA.
"""
import pandas as pd
import logging
from datetime import datetime, timedelta
from utils.oanda_client import OandaClient

logger = logging.getLogger("backtest")

# Approximate candle durations for pagination calculations
GRANULARITY_HOURS = {
    "M1": 1/60, "M5": 5/60, "M15": 0.25, "M30": 0.5,
    "H1": 1, "H2": 2, "H4": 4, "H8": 8, "H12": 12,
    "D": 24, "W": 168, "M": 720,
}


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
        Fetch historical data for backtesting. Automatically paginates if count > 5000.

        Args:
            instrument: Trading pair (e.g., "EUR_USD")
            granularity: Candle granularity (D=Daily, H4=4-hour, H1=1-hour, M15=15-min)
            count: Number of candles to fetch

        Returns:
            DataFrame with OHLC data
        """
        if not self.client:
            raise ValueError("OANDA client not available. Check credentials.")

        if count <= 5000:
            logger.info(f"Fetching {count} {granularity} candles for {instrument}")
            data = self.client.get_history(
                instrument=instrument,
                count=count,
                granularity=granularity
            )
            if data is None or data.empty:
                raise ValueError(f"No data returned for {instrument}")
            logger.info(f"Fetched {len(data)} candles from {data.index[0]} to {data.index[-1]}")
            return data

        # Paginated fetch for >5000 candles
        return self._fetch_paginated(instrument, granularity, count)

    def _fetch_paginated(self, instrument: str, granularity: str, count: int) -> pd.DataFrame:
        """
        Fetch more than 5000 candles by paginating backwards.
        Uses 'to' + 'count' per chunk, stepping back via the oldest timestamp returned.
        """
        logger.info(f"Paginated fetch: {count} {granularity} candles for {instrument}")

        all_chunks = []
        # Start from now, work backwards
        to_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        remaining = count
        max_iterations = 20  # Safety limit

        for _ in range(max_iterations):
            chunk_size = min(remaining, 5000)

            logger.info(f"  Fetching {chunk_size} candles ending at {to_time}")

            chunk = self.client.get_history_range(
                instrument=instrument,
                from_time=None,
                to_time=to_time,
                granularity=granularity,
                count=chunk_size,
            )

            if chunk is None or chunk.empty:
                logger.warning(f"  No data for chunk ending {to_time}, stopping pagination")
                break

            all_chunks.append(chunk)
            remaining -= len(chunk)

            logger.info(f"  Got {len(chunk)} candles, {remaining} remaining")

            if remaining <= 0:
                break

            # Use the oldest candle's timestamp as the next 'to' boundary
            oldest_time = chunk.index.min()
            to_time = oldest_time.strftime("%Y-%m-%dT%H:%M:%SZ")

            # If we got significantly fewer than requested, we've hit the start of available data
            if len(chunk) < chunk_size * 0.8:
                logger.info(f"  Received fewer candles than requested, likely reached start of available data")
                break

        if not all_chunks:
            raise ValueError(f"No data returned for {instrument} (paginated)")

        # Combine chunks (oldest first) and deduplicate
        all_chunks.reverse()
        data = pd.concat(all_chunks)
        data = data[~data.index.duplicated(keep='first')]
        data.sort_index(inplace=True)

        # Trim to requested count (keep most recent)
        if len(data) > count:
            data = data.iloc[-count:]

        logger.info(f"Paginated fetch complete: {len(data)} candles from {data.index[0]} to {data.index[-1]}")
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
