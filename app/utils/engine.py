"""
/Users/georgecorthine/Documents/Projects/forex-service/utils/engine.py
"""
from collections import defaultdict
import asyncio
import logging
from utils.store import state
from config.config import TRADING_PAIRS
from utils.indicators import calculate_rsi
from utils.oanda_client import OandaClient
from utils.news_scraper import NewsScraper
from models.model import SignalHistory
from database import db_wrapper

logger = logging.getLogger("forex_service")

RSI_PERIOD = 14
# --- Sentiment Confirmation Thresholds ---
# News is considered positive if the avg score is above this value
POSITIVE_SENTIMENT_THRESHOLD = 0.05
# News is considered negative if the avg score is below this value
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
                
            # tasks = [analyze_instrument(instrument, config, loop) for instrument, config in TRADING_PAIRS.items()]
            # await asyncio.gather(*tasks)

            await asyncio.sleep(60)

        except Exception as e:
            logger.error(f"Error in trading loop: {e}")
            state["errors"].append(str(e))
            await asyncio.sleep(60) # Prevent rapid error loops

async def analyze_instrument(instrument:str, config:dict, loop):
     # --- Phase 1: Data Collection ---
    history = None  # Initialize history to None
    try:
        history = await loop.run_in_executor(
            None, oanda_client.get_history, instrument, 250, "D"
        )

        if history is not None and not history.empty:
            current_price = history["Close"].iloc[-1]
          
            # --- Phase 2: Technical Analysis (RSI) ---
            rsi = calculate_rsi(history, length=RSI_PERIOD)
          
            base_sentiment = "Neutral"
            if rsi > config["overbought"]:
              base_sentiment = "Overbought"
            elif rsi < config["oversold"]:
              base_sentiment = "Oversold"

          # --- Phase 3: Fundamental Analysis (News Sentiment) ---
            news_items, avg_sentiment = await news_scraper.get_news(config.get("news_query", f"{instrument} forex news"))

          # --- Phase 4: Signal Confirmation ---
            final_sentiment = "Neutral"
            if base_sentiment == "Overbought" and avg_sentiment < NEGATIVE_SENTIMENT_THRESHOLD:
              final_sentiment = "SELL (Confirmed by News)"
            elif base_sentiment == "Oversold" and avg_sentiment > POSITIVE_SENTIMENT_THRESHOLD:
              final_sentiment = "BUY (Confirmed by News)"

            logger.info(f"Analysis [{instrument}]: Price={current_price:.5f} | RSI={rsi:.2f} (Sentiment: {base_sentiment}) | News Score={avg_sentiment:.3f} | Final Signal: {final_sentiment}")

            # Update global state so we can see it via API/Swagger
            state["latest_signal"][instrument] = {
                "price": current_price,
                "rsi": rsi,
                "sentiment": final_sentiment,
                "news_sentiment_score": avg_sentiment,
                "timestamp": str(history.index[-1]) if history is not None and not history.empty else None,  # Ensure index exists
            }
            _save_signal_sync(instrument, final_sentiment, current_price, rsi, avg_sentiment)
    except Exception as e:
        logger.exception(f"Error analyzing instrument {instrument}: {e}")
        state["errors"].append(str(e))
        instrument_failures[instrument] += 1
    finally:
        await asyncio.sleep(60)
