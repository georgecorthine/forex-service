from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging
import os
import warnings
from bs4 import XMLParsedAsHTMLWarning
from yfinance_client import YFinanceClient
from indicators import calculate_rsi
from news_scraper import NewsScraper
from config import TRADING_PAIRS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("forex_service")

# Suppress XMLParsedAsHTMLWarning from BeautifulSoup when parsing RSS feeds
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# Global state to track the service status
state = {
    "running": False,
    "latest_signal": {},
    "errors": []
}

# Initialize Yahoo Finance Client (No credentials needed)
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

            # --- Phase 3: Storage/Alerts (Placeholder) ---
            # if signal:
            #     await telegram_bot.send(signal)
            
            # logger.info("Heartbeat: Market analyzed. No signals yet.")
            
            # Wait for the next tick/interval (e.g., 60 seconds)
            await asyncio.sleep(60)
            
        except Exception as e:
            logger.error(f"Error in trading loop: {e}")
            state["errors"].append(str(e))
            await asyncio.sleep(60) # Prevent rapid error loops

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup: Start the trading loop
    state["running"] = True
    
    loop_task = asyncio.create_task(trading_engine_loop())
    yield
    # Shutdown: Stop the loop gracefully
    state["running"] = False
    loop_task.cancel()
    try:
        await loop_task
    except asyncio.CancelledError:
        pass
    logger.info("Trading Engine stopped.")

app = FastAPI(
    title="Forex Intelligence Service",
    description="Automated Forex analysis and signaling engine.",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (for development)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/")
async def status():
    """Check the health and status of the service."""
    return {
        "service": "online",
        "engine_running": state["running"],
        "latest_signal": state["latest_signal"]
    }

@app.get("/api/pairs")
async def get_pairs():
    """Return the list of configured trading pairs."""
    return list(TRADING_PAIRS.keys())

@app.get("/api/pairs/data")
async def get_all_pairs_data():
    """Return the latest analysis for all trading pairs."""
    return state["latest_signal"]

@app.get("/api/pairs/signals")
async def get_active_signals():
    """Return only pairs with active Buy/Sell signals."""
    return {
        pair: data
        for pair, data in state["latest_signal"].items()
        if "BUY" in data["sentiment"] or "SELL" in data["sentiment"]
    }

@app.get("/api/pair/{instrument}")
async def get_pair_data(instrument: str):
    """Return the latest analysis for a specific trading pair."""
    if instrument not in TRADING_PAIRS:
        raise HTTPException(status_code=404, detail=f"Instrument '{instrument}' not found in configuration.")
    
    if instrument not in state["latest_signal"]:
        raise HTTPException(status_code=503, detail=f"Analysis for '{instrument}' is not ready yet.")
        
    return state["latest_signal"][instrument]

@app.post("/api/control/stop")
async def stop_engine():
    """Manually stop the analysis loop."""
    state["running"] = False
    return {"message": "Stopping engine..."}

@app.post("/api/control/start")
async def start_engine():
    """Manually restart the analysis loop if stopped."""
    if not state["running"]:
        state["running"] = True
        asyncio.create_task(trading_engine_loop())
        return {"message": "Engine started."}
    return {"message": "Engine is already running."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)