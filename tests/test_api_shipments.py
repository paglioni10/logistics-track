from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.carrier import Carrier


def _create_carrier(db_session: Session) -> Carrier:
    carrier = Carrier(code="correios", name="Correios")
    db_session.add(carrier)
    db_session.commit()
    db_session.refresh(carrier)
    return carrier


def test_create_and_fetch_shipment(client: TestClient, db_session: Session) -> None:
    _create_carrier(db_session)

    response = client.post(
        "/shipments",
        json={"carrier_code": "correios", "tracking_code": "AA123456789BR", "order_reference": "PED-1"},
    )
    assert response.status_code == 201
    shipment_id = response.json()["id"]

    response = client.get(f"/shipments/{shipment_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["tracking_code"] == "AA123456789BR"
    assert body["current_status"] == "DESCONHECIDO"
    assert body["events"] == []


def test_create_shipment_unknown_carrier_returns_404(client: TestClient) -> None:
    response = client.post(
        "/shipments", json={"carrier_code": "inexistente", "tracking_code": "X"}
    )
    assert response.status_code == 404
