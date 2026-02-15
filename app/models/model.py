from pydantic import BaseModel
import peewee as pw
from database import db
import datetime

class PeeweeBaseModel(pw.Model):
    """A Peewee base model that uses our SQLite database."""
    class Meta:
        database = db

class SignalHistory(PeeweeBaseModel):
    """Represents a historical record of a generated signal."""
    timestamp = pw.DateTimeField(default=datetime.datetime.now)
    instrument = pw.CharField()
    sentiment = pw.CharField()
    price = pw.FloatField()
    rsi = pw.FloatField()
    news_sentiment_score = pw.FloatField(default=0.0)

# --- Pydantic Models for API validation ---

class RSIUpdate(BaseModel):
    instrument: str
    overbought: float
    oversold: float