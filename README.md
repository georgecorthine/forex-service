# Python Forex Intelligence Service

## Overview
This project aims to build a robust, automated Forex analysis service. It leverages Python to combine quantitative market data (price action) with qualitative data (news sentiment) to generate actionable trading signals.

This service utilizes a **Telegram Bot** to deliver real-time trade tips and alerts directly to the user. System management and API interaction are handled via **Swagger UI** provided by FastAPI. The system is designed to run 24/5, mirroring the Forex market hours.

## Architecture

The service is built upon four distinct phases:

### Phase 1: The Data Engine (Gathering)
Responsible for ingesting raw data from multiple sources.
- **Market Data:** Real-time ticks and historical candles via PuPrime (MetaTrader 5).
- **News Events:** Scraping high-impact economic events (e.g., CPI, Interest Rates) from economic calendars using BeautifulSoup or Selenium.

### Phase 2: The Analysis Layer (The Brain)
Processes raw data into technical indicators.
- **Trend Analysis:** Moving Averages (EMA).
- **Momentum:** Relative Strength Index (RSI).
- **Volatility:** Average True Range (ATR) for risk management.
- **Libraries:** Pandas-TA, TA-Lib.

### Phase 3: News Sentiment & Impact
Bridges the gap between market movements and public sentiment.
- **Sentiment Scoring:** Analyzes headlines using VADER or TextBlob.
- **Impact Mapping:** Correlates keywords (e.g., "Rate Hike") with potential market impact.
- **LLM Integration:** Summarizes market sentiment using LLM APIs.

### Phase 4: Storage & Orchestration
Ensures continuous operation and data persistence.
- **Database:** PostgreSQL or InfluxDB for time-series data.
- **Scheduler:** Prefect or Apache Airflow for task orchestration.
- **Alerts:** Real-time trade tips sent via **Telegram Bot**.
- **Management:** API interaction via **Swagger UI**.

## Tech Stack
- **Language:** Python
- **Backend Framework:** FastAPI (with Swagger UI)
- **Interface:** Telegram Bot
- **Data Manipulation:** Pandas, NumPy
- **Visualization:** Matplotlib, Plotly
- **Machine Learning:** Scikit-Learn, TensorFlow/PyTorch (LSTMs)
- **Scraping:** BeautifulSoup, Selenium/Playwright
- **APIs:** MetaTrader 5 (requires Windows), yfinance

## Roadmap

| Sprint | Focus | Objective |
| --- | --- | --- |
| **Week 1** | Environment | Setup Python environment and connect to Broker API (Demo). |
| **Week 2** | Scraper | Build the news scraper for Economic Calendars. |
| **Week 3** | Analysis | Implement technical indicators and sentiment logic. |
| **Week 4** | Integration | Connect logic to Telegram bot for real-time alerts. |

## Disclaimer
**Trading involves significant risk.** This software is for educational and analytical purposes only. Always backtest strategies using libraries like `Backtrader` before deploying capital.

---
*Based on the project plan outlined in `plan.md`.*