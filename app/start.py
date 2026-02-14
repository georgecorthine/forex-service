#!/usr/bin/env python3
import uvicorn
import subprocess
import sys
import time

if __name__ == "__main__":
    print("🚀 Starting Forex Intelligence Service...")

    # 1. Start the Telegram Bot as a background process
    # We use sys.executable to ensure the same Python environment is used
    bot_process = subprocess.Popen([sys.executable, "telegram_bot.py"])
    print(f"🤖 Telegram Bot started (PID: {bot_process.pid})")

    try:
        # 2. Run the FastAPI application (Blocking)
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    finally:
        # Ensure the bot process is killed when the server stops
        bot_process.terminate()
        bot_process.wait()
        print("✅ All services stopped.")