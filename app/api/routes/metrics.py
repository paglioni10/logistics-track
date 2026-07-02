from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings
from app.enums import CanonicalStatus
from app.models.carrier import Carrier
from app.models.shipment import Shipment

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/status-breakdown")
def status_breakdown(db: Session = Depends(get_db)) -> dict[str, int]:
    """Quantidade de entregas por status canônico — base do dashboard de SLA."""
    rows = (
        db.query(Shipment.current_status, func.count(Shipment.id))
        .group_by(Shipment.current_status)
        .all()
    )
    return {status: count for status, count in rows}


@router.get("/carrier-sla")
def carrier_sla(db: Session = Depends(get_db)) -> list[dict]:
    """Taxa de entrega (ENTREGUE / total) por transportadora."""
    rows = (
        db.query(
            Carrier.code,
            func.count(Shipment.id).label("total"),
            func.sum(
                case((Shipment.current_status == CanonicalStatus.ENTREGUE, 1), else_=0)
            ).label("delivered"),
        )
        .join(Shipment, Shipment.carrier_id == Carrier.id)
        .group_by(Carrier.code)
        .all()
    )
    return [
        {
            "carrier": code,
            "total": total,
            "delivered": delivered or 0,
            "delivery_rate": round((delivered or 0) / total, 4) if total else 0.0,
        }
        for code, total, delivered in rows
    ]


@router.get("/stalled")
def stalled_shipments(db: Session = Depends(get_db)) -> list[dict]:
    """Entregas sem atualização de status há mais de N horas (alerta operacional)."""
    settings = get_settings()
    threshold = datetime.now(timezone.utc) - timedelta(hours=settings.stalled_shipment_alert_hours)

    shipments = (
        db.query(Shipment)
        .filter(Shipment.current_status.notin_([CanonicalStatus.ENTREGUE, CanonicalStatus.FALHA_ENTREGA]))
        .filter((Shipment.last_event_at.is_(None)) | (Shipment.last_event_at < threshold))
        .all()
    )
    return [
        {
            "shipment_id": s.id,
            "tracking_code": s.tracking_code,
            "current_status": s.current_status,
            "last_event_at": s.last_event_at,
        }
        for s in shipments
    ]
