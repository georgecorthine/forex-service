"""
/Users/georgecorthine/Documents/Projects/forex-service/utils/engine.py
"""
from collections import defaultdict
import asyncio
import logging
from utils.store import state, state_lock
from config.config import TRADING_PAIRS
from utils.indicators import (
    calculate_rsi, calculate_rsi_series, calculate_ema,
    calculate_atr, calculate_atr_series, calculate_macd,
    detect_rsi_divergence, calculate_adx, detect_regime,
)
from utils.oanda_client import OandaClient
from utils.news_scraper import NewsScraper
from models.model import SignalHistory
from database import db_wrapper

logger = logging.getLogger("forex_service")

# --- Sentiment Confirmation Thresholds ---
POSITIVE_SENTIMENT_THRESHOLD = 0.05
NEGATIVE_SENTIMENT_THRESHOLD = -0.05

# circuit breaker
FAILURE_THRESHOLD = 3
instrument_failures = defaultdict(int)

# Initialize Clients
try:
    oanda_client = OandaClient()
except ValueError as e:
    logger.error(f"Failed to initialize OandaClient: {e}")
    oanda_client = None

news_scraper = NewsScraper()

@db_wrapper
def _save_signal_sync(instrument: str, sentiment: str, price: float, rsi: float, news_score: float):
    """Synchronous function to save a signal record to the database."""
    SignalHistory.create(
        instrument=instrument,
        sentiment=sentiment,
        price=price,
        rsi=rsi,
        news_sentiment_score=news_score
    )
    logger.info(f"Saved signal for {instrument} to database.")

async def trading_engine_loop():
    """
    The core loop that runs 24/5 (conceptually).
    It gathers data, analyzes it, and generates signals.
    """
    logger.info("Trading Engine started.")

    if not oanda_client:
        logger.error("OANDA client is not available. Trading engine cannot start.")
        state["running"] = False
        return

    loop = asyncio.get_running_loop()

    while state["running"]:
        try:
            for instrument, config in TRADING_PAIRS.items():
                if instrument_failures[instrument] < FAILURE_THRESHOLD:
                    asyncio.create_task(analyze_instrument(instrument,config,loop))
                else:
                    logger.warning(
                        f"Skipping {instrument} due to too many recent failures"
                    )

            await asyncio.sleep(60)

        except Exception as e:
            logger.error(f"Error in trading loop: {e}")
            async with state_lock:
                state["errors"].append(str(e))
                state["error_counts"]["trading_loop"] += 1
            await asyncio.sleep(60) # Prevent rapid error loops

async def analyze_instrument(instrument:str, config:dict, loop):
     # --- Phase 1: Data Collection ---
    history = None
    try:
        history = await loop.run_in_executor(
            None, oanda_client.get_history, instrument, 250, config.get("granularity", "D")
        )

        if history is not None and not history.empty:
            current_price = history["Close"].iloc[-1]
            rsi_period = config.get("rsi_length", 14)

            # --- Phase 2: Technical Analysis ---
            rsi = calculate_rsi(history, length=rsi_period)
            atr = calculate_atr(history, length=config.get("atr_period", 14))
            ema = calculate_ema(history, length=config.get("ema_period", 50))

            # MACD
            macd_data = None
            if config.get("use_macd_filter", True):
                macd_data = calculate_macd(
                    history,
                    fast=config.get("macd_fast", 12),
                    slow=config.get("macd_slow", 26),
                    signal=config.get("macd_signal", 9),
                )

            # RSI Divergence
            divergence = "none"
            if config.get("use_divergence", True):
                rsi_series = calculate_rsi_series(history, length=rsi_period)
                divergence = detect_rsi_divergence(
                    history, rsi_series,
                    lookback=config.get("divergence_lookback", 20),
                )

            # --- Phase 2b: Regime Detection ---
            regime = "neutral"
            if config.get("use_regime_filter", True):
                adx_data = calculate_adx(history, length=config.get("adx_period", 14))
                atr_series = calculate_atr_series(history, length=config.get("atr_period", 14))
                if adx_data is not None and len(atr_series.dropna()) > 0:
                    regime = detect_regime(
                        adx_value=adx_data["adx"],
                        atr_series=atr_series,
                        adx_trending_threshold=config.get("adx_trending_threshold", 25.0),
                        adx_ranging_threshold=config.get("adx_ranging_threshold", 20.0),
                        atr_volatility_multiplier=config.get("atr_volatility_multiplier", 1.5),
                        atr_ma_length=config.get("atr_volatility_ma_length", 50),
                    )

            # --- Phase 2c: Multi-Timeframe Confirmation ---
            daily_trend = "neutral"
            if config.get("use_mtf_confirmation", True):
                daily_history = await loop.run_in_executor(
                    None, oanda_client.get_history, instrument, 100, "D"
                )
                if daily_history is not None and not daily_history.empty:
                    daily_ema = calculate_ema(daily_history, length=config.get("mtf_ema_period", 50))
                    if daily_ema is not None:
                        daily_close = daily_history["Close"].iloc[-1]
                        daily_trend = "bullish" if daily_close > daily_ema else "bearish"

            # --- Phase 2d: Signal Generation ---
            base_sentiment = "Neutral"
            if rsi > config["overbought"]:
                base_sentiment = "Overbought"
            elif rsi < config["oversold"]:
                base_sentiment = "Oversold"

            use_trend = config.get("use_trend_filter", True)
            use_macd = config.get("use_macd_filter", True)

            in_uptrend = current_price > ema if (use_trend and ema is not None) else True
            in_downtrend = current_price < ema if (use_trend and ema is not None) else True

            # MACD momentum confirmation
            macd_ok_buy = True
            macd_ok_sell = True
            if use_macd and macd_data is not None:
                macd_ok_buy = (macd_data["histogram"] > 0 or
                               macd_data["histogram"] > macd_data["prev_histogram"])
                macd_ok_sell = (macd_data["histogram"] < 0 or
                                macd_data["histogram"] < macd_data["prev_histogram"])

            PULLBACK_BUY_THRESHOLD = 45
            PULLBACK_SELL_THRESHOLD = 55

            tech_signal = "Neutral"

            # High volatility: skip all signals
            if regime == "high_volatility":
                tech_signal = "Neutral"
            else:
                # Mode 1: Trend pullback — only in trending or neutral regimes
                if use_trend and ema is not None and regime != "ranging":
                    if in_uptrend and rsi < PULLBACK_BUY_THRESHOLD and macd_ok_buy:
                        if daily_trend != "bearish":
                            tech_signal = "BUY"
                    if tech_signal == "Neutral" and in_downtrend and rsi > PULLBACK_SELL_THRESHOLD and macd_ok_sell:
                        if daily_trend != "bullish":
                            tech_signal = "SELL"

                # Mode 2: RSI extreme without trend filter
                if tech_signal == "Neutral" and not use_trend:
                    if rsi < config["oversold"] and macd_ok_buy:
                        if daily_trend != "bearish":
                            tech_signal = "BUY"
                    elif rsi > config["overbought"] and macd_ok_sell:
                        if daily_trend != "bullish":
                            tech_signal = "SELL"

                # Mode 3: RSI divergence
                if tech_signal == "Neutral" and config.get("use_divergence", True):
                    if divergence == "bullish" and macd_ok_buy:
                        if daily_trend != "bearish":
                            tech_signal = "BUY"
                    elif divergence == "bearish" and macd_ok_sell:
                        if daily_trend != "bullish":
                            tech_signal = "SELL"

            # --- Phase 3: Fundamental Analysis (News Sentiment) ---
            news_items, avg_sentiment = await news_scraper.get_news(config.get("news_query", f"{instrument} forex news"))

            # --- Phase 4: News Confirmation ---
            final_sentiment = "Neutral"
            if tech_signal == "BUY" and avg_sentiment > POSITIVE_SENTIMENT_THRESHOLD:
                final_sentiment = "BUY (Confirmed by News)"
            elif tech_signal == "SELL" and avg_sentiment < NEGATIVE_SENTIMENT_THRESHOLD:
                final_sentiment = "SELL (Confirmed by News)"

            ema_str = f"{ema:.5f}" if ema else "N/A"
            atr_str = f"{atr:.5f}" if atr else "N/A"
            macd_str = f"{macd_data['histogram']:.6f}" if macd_data else "N/A"

            logger.info(
                f"Analysis [{instrument}]: Price={current_price:.5f} | RSI={rsi:.2f} ({base_sentiment}) | "
                f"EMA={ema_str} | ATR={atr_str} | "
                f"MACD hist={macd_str} | "
                f"Divergence={divergence} | Regime={regime} | DailyTrend={daily_trend} | "
                f"News={avg_sentiment:.3f} | Signal: {final_sentiment}"
            )

            # Update global state with lock
            async with state_lock:
                state["latest_signal"][instrument] = {
                    "price": current_price,
                    "rsi": rsi,
                    "ema": ema,
                    "atr": atr,
                    "macd": macd_data,
                    "divergence": divergence,
                    "regime": regime,
                    "daily_trend": daily_trend,
                    "sentiment": final_sentiment,
                    "news_sentiment_score": avg_sentiment,
                    "timestamp": str(history.index[-1]) if history is not None and not history.empty else None,
                }

            _save_signal_sync(instrument, final_sentiment, current_price, rsi, avg_sentiment)
    except Exception as e:
        logger.exception(f"Error analyzing instrument {instrument}: {e}")
        async with state_lock:
            state["errors"].append(f"{instrument}: {str(e)}")
            state["error_counts"][instrument] += 1
        instrument_failures[instrument] += 1
    finally:
        await asyncio.sleep(60)
