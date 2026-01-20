from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
import logging
import os
from yfinance_client import YFinanceClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("forex_service")

# Global state to track the service status
state = {
    "running": False,
    "latest_signal": {},
    "errors": []
}

# Initialize Yahoo Finance Client (No credentials needed)
yfinance_client = YFinanceClient()

async def trading_engine_loop():
    """
    The core loop that runs 24/5 (conceptually).
    It gathers data, analyzes it, and generates signals.
    """
    logger.info("Trading Engine started.")
    while state["running"]:
        try:
            # --- Phase 1: Data Collection ---
            price_data = await yfinance_client.get_current_price("EUR_USD")
            
            if price_data:
                logger.info(f"Market Data: {price_data}")
                # Update global state so we can see it at http://localhost:8000/
                state["latest_signal"] = {"current_price": price_data}

            # --- Phase 2: Analysis (Placeholder) ---
            # signal = strategy.analyze(prices, news)
            
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

@app.get("/")
async def status():
    """Check the health and status of the service."""
    return {
        "service": "online",
        "engine_running": state["running"],
        "latest_signal": state["latest_signal"]
    }

@app.post("/control/stop")
async def stop_engine():
    """Manually stop the analysis loop."""
    state["running"] = False
    return {"message": "Stopping engine..."}

@app.post("/control/start")
async def start_engine():
    """Manually restart the analysis loop if stopped."""
    if not state["running"]:
        state["running"] = True
        asyncio.create_task(trading_engine_loop())
        return {"message": "Engine started."}
    return {"message": "Engine is already running."}