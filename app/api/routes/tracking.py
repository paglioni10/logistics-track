from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db
from app.models.shipment import Shipment
from app.schemas.shipment import ShipmentDetail
from app.services.tracking_service import poll_shipment

router = APIRouter(prefix="/tracking", tags=["tracking"])


@router.get("/{tracking_code}", response_model=ShipmentDetail)
def get_by_tracking_code(tracking_code: str, db: Session = Depends(get_db)) -> Shipment:
    shipment = (
        db.query(Shipment)
        .options(joinedload(Shipment.events))
        .filter(Shipment.tracking_code == tracking_code)
        .first()
    )
    if shipment is None:
        raise HTTPException(404, "Código de rastreio não encontrado")
    return shipment


@router.post("/{tracking_code}/refresh", response_model=ShipmentDetail)
async def refresh_tracking(tracking_code: str, db: Session = Depends(get_db)) -> Shipment:
    """Força um polling imediato (fora do ciclo agendado do Celery)."""
    shipment = (
        db.query(Shipment)
        .options(joinedload(Shipment.events), joinedload(Shipment.carrier))
        .filter(Shipment.tracking_code == tracking_code)
        .first()
    )
    if shipment is None:
        raise HTTPException(404, "Código de rastreio não encontrado")
    return await poll_shipment(db, shipment)
