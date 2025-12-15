from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class DoveEventOut(BaseModel):
    id: int
    timestamp: datetime
    species: str
    confidence: float
    audio_path: str

    class Config:
        from_attributes = True


class DailyStatsOut(BaseModel):
    date: str
    total_calls: int
    first_call_time: Optional[datetime]
    peak_start: Optional[datetime]
    peak_end: Optional[datetime]
    peak_count: int
    bins: List[dict]




