from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.webhook import WebhookSubscription
from app.schemas.webhook import WebhookSubscriptionCreate, WebhookSubscriptionRead

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("", response_model=WebhookSubscriptionRead, status_code=201)
def create_subscription(
    payload: WebhookSubscriptionCreate, db: Session = Depends(get_db)
) -> WebhookSubscription:
    subscription = WebhookSubscription(
        target_url=str(payload.target_url),
        status_trigger=payload.status_trigger,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


@router.get("", response_model=list[WebhookSubscriptionRead])
def list_subscriptions(db: Session = Depends(get_db)) -> list[WebhookSubscription]:
    return db.query(WebhookSubscription).order_by(WebhookSubscription.created_at.desc()).all()
