from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging
import warnings
import os
from bs4 import XMLParsedAsHTMLWarning
from utils.store import state
from utils.engine import trading_engine_loop
from api.routes import router
from database import initialize_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("forex_service")

# Suppress XMLParsedAsHTMLWarning from BeautifulSoup when parsing RSS feeds
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup: Initialize database and start the trading loop
    logger.info("Initializing database...")
    initialize_db()
    
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

# Configure CORS - use environment variable for allowed origins
# Set ALLOWED_ORIGINS="http://localhost:3000,https://yourdomain.com" in production
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the API routes
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)