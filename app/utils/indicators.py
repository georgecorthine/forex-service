import pandas as pd

def calculate_rsi(df: pd.DataFrame, length: int = 14) -> float:
    """
    Calculates the Relative Strength Index (RSI) for the given dataframe using pure Pandas.
    Returns the most recent RSI value.
    """
    if df.empty or "Close" not in df.columns:
        return None

    # Get the Close price series
    close = df["Close"]

    # Calculate price changes
    delta = close.diff()

    # Separate gains and losses
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)

    # Calculate Exponential Moving Average (EMA) using Wilder's Smoothing method
    # alpha = 1/length is the standard for RSI
    avg_gain = gain.ewm(alpha=1/length, min_periods=length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/length, min_periods=length, adjust=False).mean()

    # Calculate RS and RSI
    rs = avg_gain / avg_loss
    rsi_series = 100 - (100 / (1 + rs))

    # Return the latest calculated value
    return rsi_series.iloc[-1]


def calculate_sma(df: pd.DataFrame, length: int = 200) -> float:
    """
    Calculates the Simple Moving Average (SMA) for the given dataframe.
    Returns the most recent SMA value.

    Args:
        df: DataFrame with 'Close' column
        length: Period for SMA calculation

    Returns:
        Most recent SMA value or None if insufficient data
    """
    if df.empty or "Close" not in df.columns:
        return None

    if len(df) < length:
        return None

    # Calculate SMA
    sma = df["Close"].rolling(window=length).mean()

    # Return the latest calculated value
    return sma.iloc[-1]