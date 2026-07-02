from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class WebhookSubscription(Base):
    """Configuração de um cliente: 'me avise em target_url quando status = X'."""

    __tablename__ = "webhook_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    target_url: Mapped[str] = mapped_column(String(500))
    status_trigger: Mapped[str] = mapped_column(String(30))
    """Status canônico que dispara o webhook, ou '*' para qualquer mudança."""
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    deliveries: Mapped[list["WebhookDelivery"]] = relationship(back_populates="subscription")


class WebhookDelivery(Base):
    """Registro de tentativa de entrega de um webhook (para debug e retry)."""

    __tablename__ = "webhook_deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey("webhook_subscriptions.id"))
    shipment_id: Mapped[int] = mapped_column(ForeignKey("shipments.id"))

    payload: Mapped[str] = mapped_column(Text)
    response_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    delivered: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    subscription: Mapped["WebhookSubscription"] = relationship(back_populates="deliveries")
