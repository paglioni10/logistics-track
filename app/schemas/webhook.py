from datetime import datetime

from pydantic import BaseModel, ConfigDict, HttpUrl


class WebhookSubscriptionCreate(BaseModel):
    target_url: HttpUrl
    status_trigger: str = "*"


class WebhookSubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    target_url: str
    status_trigger: str
    is_active: bool
    created_at: datetime


class WebhookOutboundPayload(BaseModel):
    """Corpo enviado ao target_url quando um status muda."""

    event: str = "shipment.status_changed"
    shipment_id: int
    tracking_code: str
    order_reference: str | None
    previous_status: str | None
    current_status: str
    occurred_at: datetime
