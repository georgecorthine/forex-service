from pydantic import BaseModel, Field, RootModel
import peewee as pw
from database import db
import datetime
from typing import List, Dict

class PeeweeBaseModel(pw.Model):
    """A Peewee base model that uses our SQLite database."""
    class Meta:
        database = db

class SignalHistory(PeeweeBaseModel):
    """Represents a historical record of a generated signal."""
    timestamp = pw.DateTimeField(default=datetime.datetime.now, index=True)
    instrument = pw.CharField(index=True)
    sentiment = pw.CharField()
    price = pw.FloatField()

    rsi = pw.FloatField()
    news_sentiment_score = pw.FloatField(default=0.0)

    class Meta:
        database = db
        # Composite index for common queries (instrument + timestamp)
        indexes = (
            (('instrument', 'timestamp'), False),  # Non-unique composite index
        )

# --- Pydantic Models for API validation ---

class RSIUpdate(BaseModel):
    instrument: str = Field(..., example="EUR_USD")
    overbought: float = Field(..., example=70.0)
    oversold: float = Field(..., example=30.0)

# --- Pydantic Models for API Responses ---

class NewsItem(BaseModel):
    title: str = Field(..., example="Forex Market News")
    link: str = Field(..., example="https://example.com")
    pub_date: str = Field(..., example="2023-10-27T12:00:00Z")
    sentiment_score: float = Field(..., example=0.5)

class PairData(BaseModel):
    price: float = Field(..., example=1.05)
    rsi: float = Field(..., example=65.0)
    sentiment: str = Field(..., example="Neutral")
    news_sentiment_score: float = Field(..., example=0.1)
    timestamp: str = Field(..., example="2023-10-27T12:00:00Z")
    news: List[NewsItem] = Field(default=[], example=[
        {"title": "Forex Market News", "link": "https://example.com", "pub_date": "2023-10-27T12:00:00Z", "sentiment_score": 0.5}
    ])

class AllPairsData(RootModel[Dict[str, PairData]]):
    pass

class TradeInstruction(BaseModel):
    instrument: str = Field(..., example="EUR_USD")
    type: str = Field(..., example="BUY")
    entry: float = Field(..., example=1.05)
    stop_loss: float = Field(..., example=1.045)
    take_profit: float = Field(..., example=1.06)

class Signal(BaseModel):
    price: float = Field(..., example=1.05)
    rsi: float = Field(..., example=25.0)
    sentiment: str = Field(..., example="BUY (Confirmed by News)")
    news_sentiment_score: float = Field(..., example=0.6)
    timestamp: str = Field(..., example="2023-10-27T12:00:00Z")
    news: List[NewsItem] = Field(..., example=[
        {"title": "Positive News for EUR", "link": "https://example.com", "pub_date": "2023-10-27T12:00:00Z", "sentiment_score": 0.8}
    ])

class ActiveSignals(RootModel[Dict[str, Signal]]):
    pass