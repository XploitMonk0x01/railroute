from pydantic import BaseModel


class StationResponse(BaseModel):
    code: str
    name: str
    city: str
    state: str
    score: int
    is_junction: bool
