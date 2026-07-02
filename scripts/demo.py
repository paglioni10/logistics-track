"""Demo determinístico e autocontido do Logistics Track.

Roda em segundos, sem Docker, sem Ollama e sem rede: usa SQLite em
memória e chama o pipeline real do projeto (conector -> normalizador
híbrido -> persistência -> webhook) com eventos de exemplo. O objetivo
é deixar visível, em uma única execução, o que o README descreve —
sem exigir que quem está avaliando suba a stack inteira.

    python -m scripts.demo

Se `LLM_NORMALIZER_ENABLED=true` e o Ollama estiver rodando local
(`ollama serve`), o último evento do exemplo (frase fora do padrão das
regras) é classificado pelo LLM local. Caso contrário, cai em
DESCONHECIDO e o script explica por quê — nenhum dos dois casos quebra
a demo.
"""

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.base import Base
from app.enums import CanonicalStatus
from app.models.carrier import Carrier
from app.models.shipment import Shipment
from app.models.tracking_event import TrackingEvent
from app.models.webhook import WebhookSubscription
from app.services.normalizer import normalize
from app.services.webhook_dispatcher import dispatch_status_change

# Eventos "brutos" como uma transportadora normalmente devolveria —
# cada linha em um formato de texto ligeiramente diferente, para
# mostrar por que a normalização é necessária.
SAMPLE_RAW_EVENTS = [
    "Objeto postado nos Correios",
    "Objeto em trânsito - por favor aguarde",
    "Objeto saiu para entrega ao destinatário",
    "Cliente reagendou a rota de coleta com o motoboy parceiro",  # foge das regras de propósito
    "Objeto entregue ao destinatário",
]


def _line(char: str = "-", width: int = 72) -> str:
    return char * width


async def main() -> None:
    settings = get_settings()

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()

    carrier = Carrier(code="correios", name="Correios", polling_interval_seconds=1800)
    db.add(carrier)
    db.commit()
    db.refresh(carrier)

    # Porta local sem serviço nenhum: a conexão é recusada quase
    # instantaneamente, então a demo não fica presa esperando timeout de
    # rede/DNS de um host real — o ponto aqui é mostrar a tentativa e o
    # registro em WebhookDelivery, não uma entrega bem-sucedida de verdade.
    subscription = WebhookSubscription(target_url="http://127.0.0.1:9/webhook", status_trigger="*")
    db.add(subscription)

    shipment = Shipment(carrier_id=carrier.id, tracking_code="AA123456789BR", order_reference="PED-1")
    db.add(shipment)
    db.commit()
    db.refresh(shipment)
    shipment.carrier = carrier

    print(_line("="))
    print("Logistics Track — demo do normalizador híbrido (regras + IA local)")
    print(_line("="))
    print(f"IA local (Ollama) habilitada: {settings.llm_normalizer_enabled}")
    if not settings.llm_normalizer_enabled:
        print(
            "  -> desligada por padrão. Para ver o fallback via LLM classificando\n"
            "     o evento ambíguo abaixo, rode `ollama serve` e defina\n"
            "     LLM_NORMALIZER_ENABLED=true no .env antes de rodar este script."
        )
    print(_line())

    previous_status = shipment.current_status
    occurred_at = datetime.now(timezone.utc) - timedelta(hours=len(SAMPLE_RAW_EVENTS))

    for raw_status in SAMPLE_RAW_EVENTS:
        occurred_at += timedelta(hours=1)
        canonical = await normalize(raw_status)

        event = TrackingEvent(
            shipment_id=shipment.id,
            raw_status=raw_status,
            canonical_status=canonical,
            location=None,
            occurred_at=occurred_at,
            source="demo",
        )
        db.add(event)
        shipment.current_status = canonical
        shipment.last_event_at = occurred_at

        tag = "regra" if canonical != CanonicalStatus.DESCONHECIDO else "sem match"
        print(f'  "{raw_status}"')
        print(f"    -> {canonical.value}  [{tag}]\n")

    db.commit()
    db.refresh(shipment)

    print(_line())
    print(f"Status final da entrega {shipment.tracking_code}: {shipment.current_status.value}")
    print("Disparando webhook outbound para a assinatura de exemplo...")
    await dispatch_status_change(db, shipment, previous_status)
    print(
        "  -> tentativa registrada em WebhookDelivery (o POST falha aqui de "
        "propósito, já que a URL de exemplo não tem nada escutando — em uma "
        "assinatura real, o endpoint do cliente receberia o payload assinado "
        "com HMAC-SHA256 no header X-Logistics-Track-Signature)."
    )
    print(_line("="))

    db.close()


if __name__ == "__main__":
    asyncio.run(main())
