import asyncio
import logging
import os
import httpx
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

# --- Configuration ---
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# The URL of your local FastAPI service
API_URL = "http://localhost:8000/api"
CHECK_INTERVAL = 900  # Check every 15 minutes (in seconds)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("telegram_bot")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when the command /start is issued."""
    await update.message.reply_text(
        "🤖 *Forex Bot Active*\n\n"
        "I am monitoring the market for Buy/Sell signals.\n"
        "Use /status to see the current market snapshot.",
        parse_mode=ParseMode.MARKDOWN
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetch and show the current status of all pairs, regardless of signal."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_URL}/pairs/data", timeout=10.0)
            data = response.json()
            
            if not data:
                await update.message.reply_text("📉 No market data available yet. Engine might be warming up.")
                return

            message = "📊 *Market Snapshot*\n"
            for pair, info in data.items():
                # Add an icon based on sentiment
                icon = "⚪"
                if "BUY" in info['sentiment']: icon = "🟢"
                if "SELL" in info['sentiment']: icon = "🔴"
                
                message += (
                    f"\n*{pair}* {icon}\n"
                    f"Price: `{info['price']}`\n"
                    f"RSI: `{info['rsi']:.1f}`\n"
                    f"Signal: _{info['sentiment']}_\n"
                )
            
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            await update.message.reply_text("❌ Error connecting to Forex API.")

async def check_signals_job(context: ContextTypes.DEFAULT_TYPE):
    """Periodic job to check for signals and alert the CHAT_ID."""
    if not CHAT_ID:
        return

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_URL}/pairs/signals", timeout=10.0)
            signals = response.json()
            
            if signals:
                logger.info(f"Found signals: {list(signals.keys())}")
                for pair, data in signals.items():
                    message = (
                        f"🚨 *Trade Alert: {pair}* 🚨\n\n"
                        f"💰 *Price:* `{data['price']}`\n"
                        f"📈 *RSI:* `{data['rsi']:.2f}`\n"
                        f"📢 *Signal:* {data['sentiment']}\n"
                        f"📰 *News Items:* {len(data.get('news', []))}\n"
                    )
                    await context.bot.send_message(chat_id=CHAT_ID, text=message, parse_mode=ParseMode.MARKDOWN)
            else:
                logger.info("Checked signals: None found.")
        except Exception as e:
            logger.error(f"Signal check failed: {e}")

async def post_init(application: Application):
    """Send a startup message to confirm connectivity."""
    if CHAT_ID:
        await application.bot.send_message(chat_id=CHAT_ID, text="🚀 *Forex Bot Started*\nMonitoring for signals...", parse_mode=ParseMode.MARKDOWN)

def main():
    if not BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN is missing.")
        return

    # Create the Application
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # Add Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))

    # Add Job (Check every 15 mins)
    if CHAT_ID:
        application.job_queue.run_repeating(check_signals_job, interval=CHECK_INTERVAL, first=10)
    else:
        logger.warning("⚠️ TELEGRAM_CHAT_ID not set. Automatic alerts disabled.")

    # Run
    logger.info("🤖 Bot is polling...")
    application.run_polling()

if __name__ == "__main__":
    main()