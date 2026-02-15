# Forex Intelligence Service

This document provides a detailed explanation of the Forex Intelligence Service, a Python-based application designed to provide real-time forex trading signals.

---

## 1. Core Concepts

The service uses a combination of technical and fundamental analysis to generate trading signals. Understanding the following concepts is crucial to interpreting the signals correctly.

### 1.1. Relative Strength Index (RSI)

The Relative Strength Index (RSI) is a momentum indicator that measures the speed and change of price movements. The RSI oscillates between 0 and 100.

- **Overbought:** When the RSI is above a certain level (typically 70), the currency pair is considered overbought. This means it has risen in price too quickly and may be due for a correction (a price drop).
- **Oversold:** When the RSI is below a certain level (typically 30), the currency pair is considered oversold. This means it has fallen in price too quickly and may be due for a rebound (a price increase).

The service uses configurable overbought and oversold levels for each trading pair.

### 1.2. News Sentiment Score

The `news_sentiment_score` is a value from -1.0 (most negative) to 1.0 (most positive) that represents the average sentiment of recent news headlines for a specific currency pair.

- **Calculation:** The service scrapes Google News for headlines related to a currency pair. It then uses the VADER sentiment analysis tool to calculate a "compound" sentiment score for each headline. The `news_sentiment_score` is the average of these compound scores.
- **Purpose:** The news sentiment score acts as a **confirmation signal** for trade decisions that are initially suggested by the RSI.

---

## 2. How Signals are Generated

The service generates signals through a multi-phase process:

1.  **Technical Analysis (RSI):** The service first calculates the RSI for a currency pair. If the RSI is above the "overbought" threshold or below the "oversold" threshold, it generates a preliminary signal.

2.  **Fundamental Analysis (News Sentiment):** The service then calculates the `news_sentiment_score` for the same currency pair.

3.  **Signal Confirmation:** A final trading signal is generated only if the news sentiment confirms the RSI signal:
    - A **BUY** signal is generated if the RSI indicates the pair is "Oversold" AND the `news_sentiment_score` is positive (above 0.05).
    - A **SELL** signal is generated if the RSI indicates the pair is "Overbought" AND the `news_sentiment_score` is negative (below -0.05).
    - If the news sentiment does not confirm the RSI signal, the final signal is "Neutral."

All generated signals, including the RSI value and the news sentiment score, are stored in a local SQLite database for historical analysis.

---

## 3. System Architecture

The service is built with a modular architecture, with each component responsible for a specific task.

- **Data Engine:**
    - **Market Data:** Price data (Open, High, Low, Close, Volume) is fetched from the **OANDA API**.
    - **News Data:** News headlines are scraped from Google News using **BeautifulSoup**.

- **Analysis Layer:**
    - The core analysis is performed in Python using the **Pandas** library for data manipulation and RSI calculation.
    - Sentiment analysis is performed using the **VADER** library.

- **Application & Interface:**
    - The core logic is exposed through a **FastAPI** backend, which provides a REST API for interacting with the service.
    - A **Telegram Bot** serves as the primary user interface, delivering real-time trade alerts and allowing users to query the status of the service.
    - **Swagger UI** (provided by FastAPI) is used for system management, configuration, and manual API interaction.

- **Database:**
    - **SQLite** is used to store historical signal data. The `peewee` library is used as the ORM.
