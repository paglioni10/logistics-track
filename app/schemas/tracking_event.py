from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.enums import CanonicalStatus


class TrackingEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    raw_status: str
    canonical_status: CanonicalStatus
    location: str | None
    occurred_at: datetime
    source: str
