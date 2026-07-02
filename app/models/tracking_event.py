from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.enums import CanonicalStatus


class TrackingEvent(Base):
    """Um evento de histórico de rastreio (ex: 'objeto saiu para entrega').

    Guarda tanto o status bruto informado pela transportadora quanto o
    status já normalizado para o modelo canônico — importante para
    auditar/depurar o normalizador depois.
    """

    __tablename__ = "tracking_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shipment_id: Mapped[int] = mapped_column(ForeignKey("shipments.id"), index=True)

    raw_status: Mapped[str] = mapped_column(Text)
    canonical_status: Mapped[CanonicalStatus] = mapped_column(
        Enum(CanonicalStatus, native_enum=False, length=30)
    )
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(30))
    """Como o evento foi obtido: 'api', 'scraping' ou 'llm_fallback'."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    shipment: Mapped["Shipment"] = relationship(back_populates="events")
