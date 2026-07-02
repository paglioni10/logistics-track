"""Disparo de webhooks outbound quando o status de uma entrega muda.

Assina o payload com HMAC-SHA256 (padrão comum em webhooks — Stripe,
GitHub etc.) para que o receptor possa validar a autenticidade da
chamada, e registra cada tentativa em WebhookDelivery para permitir
retry e auditoria.
"""

import hashlib
import hmac
import json

import httpx
from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.models.shipment import Shipment
from app.models.webhook import WebhookDelivery, WebhookSubscription
from app.schemas.webhook import WebhookOutboundPayload


def _sign(payload_json: str, secret: str) -> str:
    return hmac.new(secret.encode(), payload_json.encode(), hashlib.sha256).hexdigest()


async def dispatch_status_change(
    db: Session,
    shipment: Shipment,
    previous_status: str | None,
) -> None:
    settings = get_settings()
    subscriptions = (
        db.query(WebhookSubscription)
        .filter(WebhookSubscription.is_active.is_(True))
        .filter(
            (WebhookSubscription.status_trigger == "*")
            | (WebhookSubscription.status_trigger == shipment.current_status)
        )
        .all()
    )
    if not subscriptions:
        return

    payload = WebhookOutboundPayload(
        shipment_id=shipment.id,
        tracking_code=shipment.tracking_code,
        order_reference=shipment.order_reference,
        previous_status=previous_status,
        current_status=shipment.current_status,
        occurred_at=shipment.last_event_at or shipment.updated_at,
    )
    payload_json = payload.model_dump_json()
    signature = _sign(payload_json, settings.webhook_signing_secret)

    async with httpx.AsyncClient(timeout=settings.webhook_timeout_seconds) as client:
        for subscription in subscriptions:
            delivery = WebhookDelivery(
                subscription_id=subscription.id,
                shipment_id=shipment.id,
                payload=payload_json,
            )
            try:
                response = await _post_with_retry(
                    client, subscription.target_url, payload_json, signature
                )
                delivery.response_status_code = response.status_code
                delivery.delivered = response.is_success
                delivery.attempt_count = 1
            except httpx.HTTPError:
                delivery.delivered = False
                delivery.attempt_count = 3
            db.add(delivery)
    db.commit()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
async def _post_with_retry(
    client: httpx.AsyncClient, target_url: str, payload_json: str, signature: str
) -> httpx.Response:
    response = await client.post(
        target_url,
        content=payload_json,
        headers={
            "Content-Type": "application/json",
            "X-Logistics-Track-Signature": signature,
        },
    )
    response.raise_for_status()
    return response
