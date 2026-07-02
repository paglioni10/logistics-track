"""Popula a tabela de transportadoras com os conectores disponíveis.

Rodar após as migrações do Alembic: `python -m scripts.seed_carriers`
"""

from app.db.session import SessionLocal
from app.enums import CarrierCode
from app.models.carrier import Carrier

CARRIERS = [
    (CarrierCode.CORREIOS, "Correios", 1800),
    (CarrierCode.JADLOG, "Jadlog", 1800),
]


def main() -> None:
    db = SessionLocal()
    try:
        for code, name, interval in CARRIERS:
            existing = db.query(Carrier).filter(Carrier.code == code).first()
            if existing is None:
                db.add(Carrier(code=code, name=name, polling_interval_seconds=interval))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
