"""
/Users/georgecorthine/Documents/Projects/forex-service/api/routes.py
"""
from fastapi import APIRouter, HTTPException
from utils.store import state
from config.config import TRADING_PAIRS
from models.model import RSIUpdate
from utils.engine import trading_engine_loop
import asyncio

router = APIRouter()

@router.get("/api/")
async def status():
    """Check the health and status of the service."""
    return {
        "service": "online",
        "engine_running": state["running"],
        "latest_signal": state["latest_signal"]
    }

@router.get("/api/pairs")
async def get_pairs():
    """Return the list of configured trading pairs."""
    return list(TRADING_PAIRS.keys())

@router.get("/api/pairs/data")
async def get_all_pairs_data():
    """Return the latest analysis for all trading pairs."""
    return state["latest_signal"]

@router.get("/api/pairs/signals")
async def get_active_signals():
    """Return only pairs with active Buy/Sell signals."""
    return {
        pair: data
        for pair, data in state["latest_signal"].items()
        if "BUY" in data["sentiment"] or "SELL" in data["sentiment"]
    }

@router.get("/api/pair/{instrument}")
async def get_pair_data(instrument: str):
    """Return the latest analysis for a specific trading pair."""
    if instrument not in TRADING_PAIRS:
        raise HTTPException(status_code=404, detail=f"Instrument '{instrument}' not found in configuration.")
    
    if instrument not in state["latest_signal"]:
        raise HTTPException(status_code=503, detail=f"Analysis for '{instrument}' is not ready yet.")
        
    return state["latest_signal"][instrument]

@router.get("/api/trade/{instrument}")
async def get_trade_instruction(instrument: str):
    """Generate specific MT5 trade instructions based on the latest signal."""
    if instrument not in state["latest_signal"]:
        raise HTTPException(status_code=404, detail="Instrument data not available.")
    
    data = state["latest_signal"][instrument]
    price = data["price"]
    sentiment = data["sentiment"]
    
    # Determine precision (JPY pairs use 3 decimals, others 5)
    precision = 3 if "JPY" in instrument else 5
    
    trade_setup = {
        "instrument": instrument,
        "type": "WAIT",
        "entry": round(price, precision),
        "stop_loss": 0.0,
        "take_profit": 0.0
    }

    if "BUY" in sentiment:
        trade_setup["type"] = "BUY"
        trade_setup["stop_loss"] = round(price * 0.995, precision)  # 0.5% Risk
        trade_setup["take_profit"] = round(price * 1.01, precision) # 1.0% Reward
    elif "SELL" in sentiment:
        trade_setup["type"] = "SELL"
        trade_setup["stop_loss"] = round(price * 1.005, precision)
        trade_setup["take_profit"] = round(price * 0.99, precision)

    return trade_setup

@router.post("/api/config/rsi")
async def update_rsi_config(update: RSIUpdate):
    """Update RSI thresholds for a specific pair."""
    if update.instrument not in TRADING_PAIRS:
        raise HTTPException(status_code=404, detail=f"Instrument '{update.instrument}' not found.")
    
    TRADING_PAIRS[update.instrument]["overbought"] = update.overbought
    TRADING_PAIRS[update.instrument]["oversold"] = update.oversold
    
    return {"message": f"Updated {update.instrument} RSI thresholds to {update.overbought}/{update.oversold}"}

@router.post("/api/control/stop")
async def stop_engine():
    """Manually stop the analysis loop."""
    state["running"] = False
    return {"message": "Stopping engine..."}

@router.post("/api/control/start")
async def start_engine():
    """Manually restart the analysis loop if stopped."""
    if not state["running"]:
        state["running"] = True
        asyncio.create_task(trading_engine_loop())
        return {"message": "Engine started."}
    return {"message": "Engine is already running."}
