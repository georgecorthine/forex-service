import asyncio
import logging
import os
import httpx
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

# --- Configuration ---
# Get these from @BotFather and your own Telegram account
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID_HERE")

# The URL of your local FastAPI service
API_URL = "http://localhost:8000/api/pairs/signals"
CHECK_INTERVAL = 900  # Check every 15 minutes (in seconds)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("telegram_bot")

async def fetch_signals():
    """Fetch active signals from the local Forex Service API."""
    async with httpx.AsyncClient() as client:
        try:
            # We use a timeout because the local server might be busy
            response = await client.get(API_URL, timeout=10.0)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            logger.error(f"Could not connect to Forex Service: {e}")
            return {}
        except httpx.HTTPStatusError as e:
            logger.error(f"API returned error: {e}")
            return {}

async def send_alert(bot: Bot, pair: str, data: dict):
    """Format and send a trade alert message."""
    # Create a formatted message using Markdown
    message = (
        f"🚨 *Trade Alert: {pair}* 🚨\n\n"
        f"💰 *Price:* `{data['price']}`\n"
        f"📈 *RSI:* `{data['rsi']:.2f}`\n"
        f"📢 *Signal:* {data['sentiment']}\n"
        f"📰 *News Items:* {len(data.get('news', []))}\n"
    )
    
    try:
        await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Sent alert for {pair}")
    except TelegramError as e:
        logger.error(f"Failed to send Telegram message: {e}")

async def main():
    """Main loop to check for signals and send alerts."""
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or CHAT_ID == "YOUR_CHAT_ID_HERE":
        logger.error("❌ Configuration missing! Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.")
        return

    bot = Bot(token=BOT_TOKEN)
    logger.info("🤖 Telegram Bot Alert Service started. Monitoring signals...")

    while True:
        signals = await fetch_signals()
        
        if signals:
            logger.info(f"Found {len(signals)} active signals.")
            for pair, data in signals.items():
                await send_alert(bot, pair, data)
        else:
            logger.info("No active signals found. Waiting...")

        await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")