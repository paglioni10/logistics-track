import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import joinedload

from app.db.session import SessionLocal
from app.enums import CanonicalStatus
from app.models.shipment import Shipment
from app.services.tracking_service import poll_shipment
from app.workers.celery_app import celery_app

_TERMINAL_STATUSES = (CanonicalStatus.ENTREGUE, CanonicalStatus.FALHA_ENTREGA)


@celery_app.task(name="app.workers.tasks.poll_active_shipments")
def poll_active_shipments() -> int:
    """Task periódica (Celery beat): enfileira o polling de cada entrega ativa.

    Respeita o `polling_interval_seconds` configurado por transportadora —
    entregas cuja transportadora tem intervalo maior não são reconsultadas
    a cada tick, só quando o intervalo delas já passou.
    """
    db = SessionLocal()
    try:
        shipments = (
            db.query(Shipment)
            .options(joinedload(Shipment.carrier))
            .filter(Shipment.current_status.notin_(_TERMINAL_STATUSES))
            .all()
        )
        due_count = 0
        for shipment in shipments:
            interval = timedelta(seconds=shipment.carrier.polling_interval_seconds)
            due = shipment.last_polled_at is None or (
                datetime.now(timezone.utc) - shipment.last_polled_at >= interval
            )
            if due:
                poll_single_shipment.delay(shipment.id)
                due_count += 1
        return due_count
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.poll_single_shipment", bind=True, max_retries=3)
def poll_single_shipment(self, shipment_id: int) -> None:
    db = SessionLocal()
    try:
        shipment = (
            db.query(Shipment)
            .options(joinedload(Shipment.carrier), joinedload(Shipment.events))
            .filter(Shipment.id == shipment_id)
            .first()
        )
        if shipment is None:
            return
        asyncio.run(poll_shipment(db, shipment))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries)) from exc
    finally:
        db.close()
