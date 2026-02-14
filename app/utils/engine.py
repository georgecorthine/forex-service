"""
/Users/georgecorthine/Documents/Projects/forex-service/utils/engine.py
"""
import asyncio
import logging
from utils.store import state
from config.config import TRADING_PAIRS
from utils.indicators import calculate_rsi
from utils.yfinance_client import YFinanceClient
from utils.news_scraper import NewsScraper

logger = logging.getLogger("forex_service")

# Initialize Clients
yfinance_client = YFinanceClient()
news_scraper = NewsScraper()

async def trading_engine_loop():
    """
    The core loop that runs 24/5 (conceptually).
    It gathers data, analyzes it, and generates signals.
    """
    logger.info("Trading Engine started.")
    while state["running"]:
        try:
            for instrument, config in TRADING_PAIRS.items():
                # --- Phase 1: Data Collection ---
                # Fetch the last day of 5-minute candles to ensure we have enough data for RSI
                history = await yfinance_client.get_history(instrument, period="1d", interval="5m")
                
                if history is not None and not history.empty:
                    # Get the latest close price
                    current_price = history["Close"].iloc[-1]
                    
                    # --- Phase 2: Analysis ---
                    # Use the specific RSI length from our config
                    rsi = calculate_rsi(history, length=config["rsi_length"])
                    
                    # Interpret the RSI value using config thresholds
                    sentiment = "Neutral"
                    if rsi > config["overbought"]:
                        sentiment = "Overbought (Potential SELL)"
                    elif rsi < config["oversold"]:
                        sentiment = "Oversold (Potential BUY)"
                    
                    # --- Phase 3: News Gathering ---
                    # Scrape news relevant to this pair
                    news_items = await news_scraper.get_news(config.get("news_query", f"{instrument} forex news"))
                    
                    logger.info(f"Analysis [{instrument}]: Price={current_price:.5f} | RSI={rsi:.2f} | Sentiment={sentiment} | News Items={len(news_items)}")
                    
                    # Update global state so we can see it via API/Swagger
                    state["latest_signal"][instrument] = {
                        "price": current_price,
                        "rsi": rsi,
                        "sentiment": sentiment,
                        "timestamp": str(history.index[-1]),
                        "news": news_items
                    }
            
            # Wait for the next tick/interval (e.g., 60 seconds)
            await asyncio.sleep(60)
            
        except Exception as e:
            logger.error(f"Error in trading loop: {e}")
            state["errors"].append(str(e))
            await asyncio.sleep(60) # Prevent rapid error loops
