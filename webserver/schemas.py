from pydantic import BaseModel
from typing import List, Optional

class AccidentSchema(BaseModel):
    id: int
    season: str
    date: str
    state: str
    location: str
    description: str
    fatalities: int
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    class Config:
        from_attributes = True
        
class InvalidateCacheRequest(BaseModel):
    keys: Optional[List[str]] = None