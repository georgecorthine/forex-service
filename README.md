# Forex Intelligence Service

## Overview

This project is a Python-based service that provides real-time forex trading signals. It uses a combination of technical analysis (RSI) and fundamental analysis (news sentiment) to generate signals, which are then sent to the user via a Telegram bot.

The service is designed to be a "set it and forget it" tool for forex traders who want to be alerted to potential trading opportunities without having to constantly monitor the markets themselves.

## Features

- **Real-time Signal Generation:** The service continuously monitors the forex markets and generates signals in real time.
- **RSI-Based Technical Analysis:** Uses the Relative Strength Index (RSI) to identify overbought and oversold conditions.
- **News-Based Sentiment Analysis:** Uses news sentiment to confirm RSI signals and avoid false positives.
- **Telegram Bot Integration:** Delivers trading signals directly to your Telegram account.
- **REST API:** Provides a FastAPI-based REST API for interacting with the service and retrieving data.
- **Database Storage:** Stores all generated signals in a local SQLite database for historical analysis.

## Tech Stack

- **Language:** Python 3
- **Backend Framework:** FastAPI
- **Data Provider:** OANDA API
- **Telegram Bot:** `python-telegram-bot`
- **Data Manipulation:** Pandas
- **Sentiment Analysis:** VADER
- **Database:** SQLite with Peewee ORM

## Getting Started

### 1. Prerequisites

- Python 3.10+
- An OANDA account (demo or live) with an API key.
- A Telegram account and a Telegram bot token.

### 2. Installation

1.  Clone this repository:
    ```bash
    git clone https://github.com/georgecorthine/forex-service.git
    cd forex-service
    ```

2.  Create a virtual environment and install the dependencies:
    ```bash
    python -m venv venv
    source venv/bin/activate
    pip install -r app/requirements.txt
    ```

### 3. Configuration

The service is configured using environment variables. Create a `.env` file in the `app` directory and add the following variables:

```
OANDA_API_KEY=<your-oanda-api-key>
OANDA_ACCOUNT_ID=<your-oanda-account-id>
OANDA_ENVIRONMENT=practice  # or "live"
TELEGRAM_BOT_TOKEN=<your-telegram-bot-token>
TELEGRAM_CHAT_ID=<your-telegram-chat-id>
```

You can get your `TELEGRAM_CHAT_ID` by sending a message to your bot and then visiting `https://api.telegram.org/bot<your-bot-token>/getUpdates`.

### 4. Running the Service

To run the service, simply execute the `start.py` script from within the `app` directory:

```bash
cd app
./start.py
```

The service will start, and you will see output in your console. The FastAPI server will be running on `http://localhost:8000`, and the Telegram bot will start polling for messages.

You can access the API documentation at `http://localhost:8000/docs`.

## Disclaimer

**Trading involves significant risk.** This software is for educational and analytical purposes only. Always backtest strategies and use a demo account before risking real capital.
