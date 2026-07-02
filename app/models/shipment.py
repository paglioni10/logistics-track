from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.enums import CanonicalStatus


class Shipment(Base):
    """Uma entrega rastreada, identificada pelo código de rastreio da transportadora."""

    __tablename__ = "shipments"
    __table_args__ = (
        Index("ix_shipments_carrier_tracking_code", "carrier_id", "tracking_code", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    carrier_id: Mapped[int] = mapped_column(ForeignKey("carriers.id"))
    tracking_code: Mapped[str] = mapped_column(String(100), index=True)
    order_reference: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)

    current_status: Mapped[CanonicalStatus] = mapped_column(
        Enum(CanonicalStatus, native_enum=False, length=30),
        default=CanonicalStatus.DESCONHECIDO,
    )
    last_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    carrier: Mapped["Carrier"] = relationship(back_populates="shipments")
    events: Mapped[list["TrackingEvent"]] = relationship(
        back_populates="shipment", order_by="TrackingEvent.occurred_at"
    )
