"""Orquestra um ciclo de polling: conector -> normalizador -> persistência -> webhook."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.connectors.base import CarrierConnectorError
from app.connectors.registry import get_connector
from app.enums import STATUS_ORDER, CanonicalStatus
from app.models.shipment import Shipment
from app.models.tracking_event import TrackingEvent
from app.services.normalizer import normalize
from app.services.webhook_dispatcher import dispatch_status_change


async def poll_shipment(db: Session, shipment: Shipment) -> Shipment:
    connector = get_connector(shipment.carrier.code)

    try:
        raw_events = await connector.fetch_events(shipment.tracking_code)
    except CarrierConnectorError:
        shipment.last_polled_at = datetime.now(timezone.utc)
        db.commit()
        return shipment

    existing_occurrences = {event.occurred_at for event in shipment.events}
    previous_status = shipment.current_status
    new_status_candidate: CanonicalStatus | None = None
    new_status_at: datetime | None = None

    for raw_event in raw_events:
        if raw_event.occurred_at in existing_occurrences:
            continue

        canonical = await normalize(raw_event.raw_status)
        event = TrackingEvent(
            shipment_id=shipment.id,
            raw_status=raw_event.raw_status,
            canonical_status=canonical,
            location=raw_event.location,
            occurred_at=raw_event.occurred_at,
            source=raw_event.source,
        )
        db.add(event)

        # Só avança o status "corrente" se for uma progressão válida —
        # evita que um evento fora de ordem regrida o status da entrega.
        if new_status_at is None or raw_event.occurred_at > new_status_at:
            if STATUS_ORDER.get(canonical, -1) >= STATUS_ORDER.get(previous_status, -1):
                new_status_candidate = canonical
                new_status_at = raw_event.occurred_at

    shipment.last_polled_at = datetime.now(timezone.utc)
    if new_status_candidate is not None:
        shipment.current_status = new_status_candidate
        shipment.last_event_at = new_status_at

    db.commit()
    db.refresh(shipment)

    if new_status_candidate is not None and new_status_candidate != previous_status:
        await dispatch_status_change(db, shipment, previous_status)

    return shipment
