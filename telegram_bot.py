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
                
                display_pair = pair.replace("_", "\_")
                message += (
                    f"\n*{display_pair}* {icon}\n"
                    f"Price: `{info['price']}`\n"
                    f"RSI: `{info['rsi']:.1f}`\n"
                    f"Signal: _{info['sentiment']}_\n"
                )
            
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            await update.message.reply_text("❌ Error connecting to Forex API.")

async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetch detailed analysis for a specific pair."""
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /analyze <PAIR>\nExample: /analyze EUR_USD")
        return

    pair = context.args[0].upper()
    display_pair = pair.replace("_", "\_")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_URL}/pair/{pair}", timeout=10.0)
            
            if response.status_code == 404:
                await update.message.reply_text(f"❌ Pair *{display_pair}* not found.", parse_mode=ParseMode.MARKDOWN)
                return
            elif response.status_code == 503:
                await update.message.reply_text(f"⏳ Data for *{display_pair}* is not ready yet.", parse_mode=ParseMode.MARKDOWN)
                return
            
            response.raise_for_status()
            data = response.json()

            sentiment_icon = "⚪"
            if "BUY" in data['sentiment']: sentiment_icon = "🟢"
            if "SELL" in data['sentiment']: sentiment_icon = "🔴"

            news_section = ""
            if data.get('news'):
                news_section = "\n\n📰 *Recent News:*"
                for item in data['news'][:3]:
                    title = item.get('title', 'No Title').replace('[', '(').replace(']', ')')
                    link = item.get('link', '#')
                    news_section += f"\n• [{title}]({link})"

            message = (
                f"🔍 *Analysis for {display_pair}* {sentiment_icon}\n\n"
                f"💰 *Price:* `{data['price']}`\n"
                f"📈 *RSI:* `{data['rsi']:.2f}`\n"
                f"📢 *Sentiment:* {data['sentiment']}"
                f"{news_section}"
            )

            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

        except Exception as e:
            logger.error(f"Analyze command failed: {e}")
            await update.message.reply_text("❌ Failed to fetch analysis.")

async def trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get specific MT5 trade instructions."""
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /trade <PAIR>\nExample: /trade EUR_USD")
        return

    pair = context.args[0].upper()
    display_pair = pair.replace("_", "\_")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_URL}/trade/{pair}", timeout=10.0)
            if response.status_code != 200:
                await update.message.reply_text(f"❌ Could not generate trade for {pair}.")
                return
            
            data = response.json()
            
            if data["type"] == "WAIT":
                await update.message.reply_text(f"✋ *Hold Position*\nMarket is currently Neutral for {display_pair}.", parse_mode=ParseMode.MARKDOWN)
                return

            action_emoji = "🟢" if data["type"] == "BUY" else "🔴"
            
            message = (
                f"📱 *MT5 Trade Instruction: {display_pair}*\n\n"
                f"1️⃣ Open MT5 App > Quotes\n"
                f"2️⃣ Tap *{display_pair}* > Trade\n"
                f"3️⃣ Select: *Market Execution*\n\n"
                f"📋 *Enter these details:*\n"
                f"• Stop Loss: `{data['stop_loss']}`\n"
                f"• Take Profit: `{data['take_profit']}`\n\n"
                f"4️⃣ Tap {action_emoji} *{data['type']} by Market*"
            )
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Trade command failed: {e}")
            await update.message.reply_text("❌ Error fetching trade instructions.")

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
                    display_pair = pair.replace("_", "\_")
                    message = (
                        f"🚨 *Trade Alert: {display_pair}* 🚨\n\n"
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
    application.add_handler(CommandHandler("analyze", analyze))
    application.add_handler(CommandHandler("trade", trade))

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