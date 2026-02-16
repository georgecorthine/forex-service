"""
/Users/georgecorthine/Documents/Projects/forex-service/api/routes.py
"""
from fastapi import APIRouter, HTTPException
from utils.store import state
from config.config import TRADING_PAIRS
from models.model import RSIUpdate, AllPairsData, ActiveSignals, PairData, TradeInstruction
from utils.engine import trading_engine_loop
from utils.risk_management import calculate_trade_levels
import asyncio
import os

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

@router.get("/api/pairs/data", response_model=AllPairsData)
async def get_all_pairs_data():
    """Return the latest analysis for all trading pairs."""
    # Ensure news is always present, even if it's an empty list
    for pair, data in state["latest_signal"].items():
        if 'news' not in data:
            data['news'] = []
    return state["latest_signal"]

@router.get("/api/pairs/signals", response_model=ActiveSignals)
async def get_active_signals():
    """Return only pairs with active Buy/Sell signals."""
    return {
        pair: data
        for pair, data in state["latest_signal"].items()
        if "BUY" in data["sentiment"] or "SELL" in data["sentiment"]
    }

@router.get("/api/pair/{instrument}", response_model=PairData)
async def get_pair_data(instrument: str):
    """Return the latest analysis for a specific trading pair."""
    if instrument not in TRADING_PAIRS:
        raise HTTPException(status_code=404, detail=f"Instrument '{instrument}' not found in configuration.")
    
    if instrument not in state["latest_signal"]:
        raise HTTPException(status_code=503, detail=f"Analysis for '{instrument}' is not ready yet.")
        
    return state["latest_signal"][instrument]

@router.get("/api/trade/{instrument}", response_model=TradeInstruction)
async def get_trade_instruction(instrument: str):
    """Generate specific OANDA trade instructions based on the latest signal with proper risk management."""
    if instrument not in state["latest_signal"]:
        raise HTTPException(status_code=404, detail="Instrument data not available.")

    data = state["latest_signal"][instrument]
    price = data["price"]
    sentiment = data["sentiment"]

    # Get account balance and risk settings from environment (with defaults)
    account_balance = float(os.getenv("ACCOUNT_BALANCE", "10000.0"))
    risk_percentage = float(os.getenv("RISK_PERCENTAGE", "1.0"))
    reward_ratio = float(os.getenv("REWARD_RATIO", "2.0"))

    # Determine precision (JPY pairs use 3 decimals, others 5)
    precision = 3 if "JPY" in instrument else 5

    trade_setup = {
        "instrument": instrument,
        "type": "WAIT",
        "entry": round(price, precision),
        "stop_loss": 0.0,
        "take_profit": 0.0
    }

    # Get ATR from state if available (for dynamic stops)
    atr = data.get("atr")

    if "BUY" in sentiment:
        levels = calculate_trade_levels(
            entry_price=price,
            trade_type="BUY",
            instrument=instrument,
            risk_percentage=risk_percentage,
            reward_ratio=reward_ratio,
            account_balance=account_balance,
            atr=atr,
        )
        trade_setup["type"] = "BUY"
        trade_setup["entry"] = round(levels["entry"], precision)
        trade_setup["stop_loss"] = levels["stop_loss"]
        trade_setup["take_profit"] = levels["take_profit"]

    elif "SELL" in sentiment:
        levels = calculate_trade_levels(
            entry_price=price,
            trade_type="SELL",
            instrument=instrument,
            risk_percentage=risk_percentage,
            reward_ratio=reward_ratio,
            account_balance=account_balance,
            atr=atr,
        )
        trade_setup["type"] = "SELL"
        trade_setup["entry"] = round(levels["entry"], precision)
        trade_setup["stop_loss"] = levels["stop_loss"]
        trade_setup["take_profit"] = levels["take_profit"]

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
