from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Carrier(Base):
    """Uma transportadora conectada (Correios, Jadlog, regionais...)."""

    __tablename__ = "carriers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    polling_interval_seconds: Mapped[int] = mapped_column(Integer, default=1800)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    shipments: Mapped[list["Shipment"]] = relationship(back_populates="carrier")
