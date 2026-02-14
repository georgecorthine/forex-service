from pydantic import BaseModel

class RSIUpdate(BaseModel):
    instrument: str
    overbought: float
    oversold: float