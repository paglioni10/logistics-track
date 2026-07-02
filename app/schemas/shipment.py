from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.enums import CanonicalStatus
from app.schemas.tracking_event import TrackingEventRead


class ShipmentCreate(BaseModel):
    carrier_code: str
    tracking_code: str
    order_reference: str | None = None


class ShipmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tracking_code: str
    order_reference: str | None
    current_status: CanonicalStatus
    last_event_at: datetime | None
    last_polled_at: datetime | None
    created_at: datetime


class ShipmentDetail(ShipmentRead):
    events: list[TrackingEventRead] = []
