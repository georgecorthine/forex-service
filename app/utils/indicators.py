import pandas as pd
import numpy as np


def calculate_rsi(df: pd.DataFrame, length: int = 14) -> float:
    """
    Calculates the Relative Strength Index (RSI) using Wilder's Smoothing.
    Returns the most recent RSI value.
    """
    if df.empty or "Close" not in df.columns:
        return None

    close = df["Close"]
    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1/length, min_periods=length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/length, min_periods=length, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi_series = 100 - (100 / (1 + rs))

    return rsi_series.iloc[-1]


def calculate_rsi_series(df: pd.DataFrame, length: int = 14) -> pd.Series:
    """
    Calculates the full RSI series for divergence detection.
    """
    if df.empty or "Close" not in df.columns:
        return pd.Series(dtype=float)

    close = df["Close"]
    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1/length, min_periods=length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/length, min_periods=length, adjust=False).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calculate_sma(df: pd.DataFrame, length: int = 200) -> float:
    """
    Calculates the Simple Moving Average (SMA).
    Returns the most recent SMA value.
    """
    if df.empty or "Close" not in df.columns:
        return None

    if len(df) < length:
        return None

    sma = df["Close"].rolling(window=length).mean()
    return sma.iloc[-1]


def calculate_ema(df: pd.DataFrame, length: int = 50) -> float:
    """
    Calculates the Exponential Moving Average (EMA).
    Returns the most recent EMA value.
    """
    if df.empty or "Close" not in df.columns:
        return None

    if len(df) < length:
        return None

    ema = df["Close"].ewm(span=length, adjust=False).mean()
    return ema.iloc[-1]


def calculate_atr(df: pd.DataFrame, length: int = 14) -> float:
    """
    Calculates the Average True Range (ATR).
    Returns the most recent ATR value.
    """
    if df.empty or len(df) < length + 1:
        return None

    for col in ("High", "Low", "Close"):
        if col not in df.columns:
            return None

    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.ewm(alpha=1/length, min_periods=length, adjust=False).mean()

    return atr.iloc[-1]


def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26,
                   signal: int = 9) -> dict:
    """
    Calculates MACD line, signal line, and histogram.
    Returns dict with the most recent values.
    """
    if df.empty or "Close" not in df.columns:
        return None

    if len(df) < slow + signal:
        return None

    close = df["Close"]
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()

    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    return {
        "macd": macd_line.iloc[-1],
        "signal": signal_line.iloc[-1],
        "histogram": histogram.iloc[-1],
        "prev_histogram": histogram.iloc[-2] if len(histogram) >= 2 else 0.0,
    }


def detect_rsi_divergence(df: pd.DataFrame, rsi_series: pd.Series,
                          lookback: int = 20) -> str:
    """
    Detects bullish or bearish RSI divergence over the lookback window.

    Bullish divergence: price makes lower low, RSI makes higher low.
    Bearish divergence: price makes higher high, RSI makes lower high.

    Returns: "bullish", "bearish", or "none"
    """
    if df.empty or len(df) < lookback + 2 or len(rsi_series) < lookback + 2:
        return "none"

    close = df["Close"].iloc[-(lookback + 1):]
    rsi = rsi_series.iloc[-(lookback + 1):]

    # Drop NaN values from RSI
    valid = rsi.notna()
    close = close[valid]
    rsi = rsi[valid]

    if len(close) < 5:
        return "none"

    # Find local lows and highs using a simple 2-bar comparison
    price_vals = close.values
    rsi_vals = rsi.values

    # Find local minima for bullish divergence
    lows = []
    for i in range(1, len(price_vals) - 1):
        if price_vals[i] < price_vals[i - 1] and price_vals[i] < price_vals[i + 1]:
            lows.append((i, price_vals[i], rsi_vals[i]))

    if len(lows) >= 2:
        prev_low = lows[-2]
        curr_low = lows[-1]
        # Price lower low but RSI higher low = bullish divergence
        if curr_low[1] < prev_low[1] and curr_low[2] > prev_low[2]:
            return "bullish"

    # Find local maxima for bearish divergence
    highs = []
    for i in range(1, len(price_vals) - 1):
        if price_vals[i] > price_vals[i - 1] and price_vals[i] > price_vals[i + 1]:
            highs.append((i, price_vals[i], rsi_vals[i]))

    if len(highs) >= 2:
        prev_high = highs[-2]
        curr_high = highs[-1]
        # Price higher high but RSI lower high = bearish divergence
        if curr_high[1] > prev_high[1] and curr_high[2] < prev_high[2]:
            return "bearish"

    return "none"
