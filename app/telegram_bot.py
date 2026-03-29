import asyncio
import logging
import os
import httpx
import datetime
from telegram import Update
from telegram import __version__ as TG_VER
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.ext import Defaults

# --- Configuration ---
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# The URL of your FastAPI service (can be configured via environment variable)
API_URL = os.getenv("API_URL", "http://localhost:8000/api")
CHECK_HOUR = int(os.getenv("CHECK_HOUR", "14"))  # Hour to check for signals (UTC)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("telegram_bot")

# Validation helper
def validate_pair_format(pair: str) -> bool:
    """Validate forex pair format (e.g., EUR_USD)."""
    if not pair:
        return False
    parts = pair.split("_")
    if len(parts) != 2:
        return False
    if len(parts[0]) != 3 or len(parts[1]) != 3:
        return False
    if not parts[0].isalpha() or not parts[1].isalpha():
        return False
    return True

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

                display_pair = pair.replace("_", "\\_")
                message += (
                    f"\n*{display_pair}* {icon}\n"
                    f"Price: `{info['price']}`\n"
                    f"RSI: `{info['rsi']:.1f}`\n"
                    f"News Sentiment: `{info['news_sentiment_score']:.3f}`\n"
                    f"Signal: _{info['sentiment']}_\n"
                )

            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        except httpx.RequestError as e:
            logger.error(f"Network error while fetching status: {e}")
            await update.message.reply_text("❌ Network error connecting to Forex API.")
        except Exception as e:
            logger.exception("Status check failed due to an unexpected error.")
            await update.message.reply_text("❌ Error connecting to Forex API.")

async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetch detailed analysis for a specific pair."""
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /analyze <PAIR>\nExample: /analyze EUR_USD")
        return

    pair = context.args[0].upper()

    # Validate pair format
    if not validate_pair_format(pair):
        await update.message.reply_text("❌ Invalid pair format. Use format: EUR_USD")
        return

    display_pair = pair.replace("_", "\\_")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_URL}/pair/{pair}", timeout=10)

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
                f"📰 *News Sentiment:* `{data['news_sentiment_score']:.3f}`\n"
                f"📢 *Sentiment:* {data['sentiment']}"
                f"{news_section}"
            )

            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} while fetching analysis for {pair}: {e}")
            await update.message.reply_text(f"❌ Error: HTTP {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logger.exception(f"Analyze command failed for {pair}: {e}")
            await update.message.reply_text("❌ Failed to fetch analysis.")

async def trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get specific OANDA trade instructions."""
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /trade <PAIR>\nExample: /trade EUR_USD")
        return

    pair = context.args[0].upper()

    # Validate pair format
    if not validate_pair_format(pair):
        await update.message.reply_text("❌ Invalid pair format. Use format: EUR_USD")
        return

    display_pair = pair.replace("_", "\\_")

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
                f"📱 *OANDA Trade Instruction: {display_pair}*\n\n"
                f"1. Open OANDA App > Tap 'Trade' > Search for '{display_pair}'\n"
                f"2. Select 'Market' Order\n\n"
                f"3. Configure your trade:\n"
                f"   • Units: *Set your desired trade size*\n"
                f"   • Stop Loss: `{data['stop_loss']}`\n"
                f"   • Take Profit: `{data['take_profit']}`\n\n"
                f"4. Tap {action_emoji} *{data['type']}*"
            )
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Trade command failed: {e}")
            await update.message.reply_text("❌ Error fetching trade instructions.")

async def set_rsi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Update RSI thresholds dynamically."""
    if not context.args or len(context.args) != 3:
        await update.message.reply_text("⚠️ Usage: /setrsi <PAIR> <OVERBOUGHT> <OVERSOLD>\nExample: /setrsi EUR_USD 75 25")
        return

    pair = context.args[0].upper()
    display_pair = pair.replace("_", "\\_")

    try:
        overbought = int(context.args[1])
        oversold = int(context.args[2])

        # Validate RSI ranges
        if not (0 <= oversold <= 100):
            await update.message.reply_text("❌ Oversold value must be between 0-100")
            return
        if not (0 <= overbought <= 100):
            await update.message.reply_text("❌ Overbought value must be between 0-100")
            return
        if oversold >= overbought:
            await update.message.reply_text("❌ Oversold must be less than overbought")
            return

    except ValueError:
        await update.message.reply_text("❌ Thresholds must be integers.")
        return

    async with httpx.AsyncClient() as client:
        try:
            payload = {
                "instrument": pair,
                "overbought": overbought,
                "oversold": oversold
            }
            response = await client.post(f"{API_URL}/config/rsi", json=payload, timeout=10.0)
            
            if response.status_code == 404:
                await update.message.reply_text(f"❌ Pair *{display_pair}* not found.", parse_mode=ParseMode.MARKDOWN)
                return

            response.raise_for_status()
            await update.message.reply_text(f"✅ Updated *{display_pair}* thresholds:\nOverbought: `{overbought}`\nOversold: `{oversold}`", parse_mode=ParseMode.MARKDOWN)
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} while setting RSI for {pair}: {e}")
            await update.message.reply_text(f"❌ Error: HTTP {e.response.status_code} - {e.response.text}")

        except Exception as e:
            logger.error(f"Set RSI command failed: {e}")
            await update.message.reply_text("❌ Failed to update configuration.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all available commands."""
    message = (
        "🤖 *Forex Bot Commands*\n\n"
        "🔹 /start - Initialize the bot\n"
        "🔹 /status - View market snapshot for all pairs\n"
        "🔹 /analyze <PAIR> - Detailed analysis (RSI, Sentiment, News)\n"
        "🔹 /trade <PAIR> - Get OANDA entry/exit instructions\n"
        "🔹 /setrsi <PAIR> <OB> <OS> - Update RSI thresholds\n"
        "    Example: `/setrsi EUR_USD 75 25`\n"
        "🔹 /example <COMMAND> - Show example output for a command\n"
        "    Example: `/example analyze`\n"
        "🔹 /help - Show this list"
    )
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

async def example(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show example data for different commands."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ Usage: /example <COMMAND>\n"
            "Example: /example analyze\n"
            "Available commands: status, analyze, trade, setrsi, signal"
        )
        return

    command = context.args[0].lower()

    if command == "status":
        message = (
            '📊 *Market Snapshot*\n\n'
            '*EUR\\_USD* 🟢\n'
            'Price: `1.05`\n'
            'RSI: `25.0`\n'
            'News Sentiment: `0.600`\n'
            'Signal: _BUY (Confirmed by News)_\n\n'
            '*GBP\\_USD* 🔴\n'
            'Price: `1.25`\n'
            'RSI: `75.0`\n'
            'News Sentiment: `-0.500`\n'
            'Signal: _SELL (Confirmed by News)_\n'
        )
    elif command == "analyze":
        message = (
            '🔍 *Analysis for EUR\\_USD* 🟢\n\n'
            '💰 *Price:* `1.05`\n'
            '📈 *RSI:* `25.00`\n'
            '📰 *News Sentiment:* `0.600`\n'
            '📢 *Sentiment:* BUY (Confirmed by News)\n\n'
            '📰 *Recent News:*\n'
            '• [Positive News for EUR](https://example.com)'
        )
    elif command == "trade":
        message = (
            "📱 *OANDA Trade Instruction: EUR\\_USD*\n\n"
            "1. Open OANDA App > Tap 'Trade' > Search for 'EUR\\_USD'\n"
            "2. Select 'Market' Order\n\n"
            "3. Configure your trade:\n"
            "   • Units: *Set your desired trade size*\n"
            "   • Stop Loss: `1.045`\n"
            "   • Take Profit: `1.06`\n\n"
            "4. Tap 🟢 *BUY*"
        )
    elif command == "setrsi":
        message = '✅ Updated *EUR\\_USD* thresholds:\nOverbought: `75`\nOversold: `25`'
    elif command == "signal":
        message = (
            '🚨 *Trade Alert: EUR\\_USD* 🚨\n\n'
            '💰 *Price:* `1.05`\n'
            '📈 *RSI:* `25.00`\n'
            '📰 *News Sentiment:* `0.600`\n'
            '📢 *Signal:* BUY (Confirmed by News)\n\n'
            '🤔 *Reasoning:* RSI is oversold and news sentiment is positive.'
        )
    else:
        message = f"Unknown example command: {command}"

    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


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
                    display_pair = pair.replace("_", "\\_")
                    
                    reasoning = ""
                    if "BUY" in data["sentiment"]:
                        reasoning = "RSI is oversold and news sentiment is positive."
                    elif "SELL" in data["sentiment"]:
                        reasoning = "RSI is overbought and news sentiment is negative."

                    message = (
                        f"🚨 *Trade Alert: {display_pair}* 🚨\n\n"
                        f"💰 *Price:* `{data['price']}`\n"
                        f"📈 *RSI:* `{data['rsi']:.2f}`\n"
                        f"📰 *News Sentiment:* `{data['news_sentiment_score']:.3f}`\n"
                        f"📢 *Signal:* {data['sentiment']}\n\n"
                        f"🤔 *Reasoning:* {reasoning}"
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

    # Check if telegram package version is suitable
    if TG_VER < "20.0":
        raise EnvironmentError(
            "This example is not compatible with your current Telegram Bot "
            f"API version {TG_VER}. Please upgrade to version 20.0 or higher."
        )

    # Create the Application with defaults and post_init
    defaults = Defaults(parse_mode=ParseMode.MARKDOWN)
    application = Application.builder().token(BOT_TOKEN).defaults(defaults).post_init(post_init).build()

    # Add Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("analyze", analyze))
    application.add_handler(CommandHandler("trade", trade))
    application.add_handler(CommandHandler("setrsi", set_rsi))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("example", example))

    # Add Job (Check every 15 mins)
    if CHAT_ID:
        application.job_queue.run_daily(check_signals_job, time=datetime.time(hour=CHECK_HOUR, minute=0, second=0))
    else:
        logger.warning("⚠️ TELEGRAM_CHAT_ID not set. Automatic alerts disabled.")

    # Run
    logger.info("🤖 Bot is polling...")
    application.run_polling()


if __name__ == "__main__":
    main()