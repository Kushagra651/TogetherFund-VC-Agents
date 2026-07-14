from pydantic import BaseModel
from typing import Optional

class DDMemo(BaseModel):
    market: str
    competition: str
    founder: str
    traction: str
    red_flags: str
    verdict: str
    confidence: str  # High / Medium / Low
    sources: list[str]