from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db
from app.models.carrier import Carrier
from app.models.shipment import Shipment
from app.schemas.shipment import ShipmentCreate, ShipmentDetail, ShipmentRead

router = APIRouter(prefix="/shipments", tags=["shipments"])


@router.post("", response_model=ShipmentRead, status_code=201)
def create_shipment(payload: ShipmentCreate, db: Session = Depends(get_db)) -> Shipment:
    carrier = db.query(Carrier).filter(Carrier.code == payload.carrier_code).first()
    if carrier is None:
        raise HTTPException(404, f"Transportadora '{payload.carrier_code}' não encontrada")

    existing = (
        db.query(Shipment)
        .filter(Shipment.carrier_id == carrier.id, Shipment.tracking_code == payload.tracking_code)
        .first()
    )
    if existing is not None:
        return existing

    shipment = Shipment(
        carrier_id=carrier.id,
        tracking_code=payload.tracking_code,
        order_reference=payload.order_reference,
    )
    db.add(shipment)
    db.commit()
    db.refresh(shipment)
    return shipment


@router.get("", response_model=list[ShipmentRead])
def list_shipments(
    order_reference: str | None = None,
    db: Session = Depends(get_db),
) -> list[Shipment]:
    query = db.query(Shipment)
    if order_reference:
        query = query.filter(Shipment.order_reference == order_reference)
    return query.order_by(Shipment.created_at.desc()).limit(200).all()


@router.get("/{shipment_id}", response_model=ShipmentDetail)
def get_shipment(shipment_id: int, db: Session = Depends(get_db)) -> Shipment:
    shipment = (
        db.query(Shipment)
        .options(joinedload(Shipment.events))
        .filter(Shipment.id == shipment_id)
        .first()
    )
    if shipment is None:
        raise HTTPException(404, "Shipment não encontrado")
    return shipment
