from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class RawTrackingEvent:
    """Evento de rastreio como veio da fonte, ainda não normalizado.

    `raw_status` preserva o texto original da transportadora — é o que
    o normalizador (app/services/normalizer.py) consome para produzir
    um CanonicalStatus.
    """

    raw_status: str
    occurred_at: datetime
    location: str | None
    source: str  # "api" | "scraping"


class CarrierConnector(ABC):
    """Interface que todo conector de transportadora precisa implementar.

    Mantém o resto do sistema (polling, normalização, API) agnóstico de
    como cada transportadora expõe seus dados — API oficial, scraping,
    ou uma combinação com fallback.
    """

    code: str

    @abstractmethod
    async def fetch_events(self, tracking_code: str) -> list[RawTrackingEvent]:
        """Retorna o histórico de eventos para um código de rastreio.

        Deve levantar `CarrierConnectorError` em caso de falha definitiva
        (código inválido, transportadora fora do ar, etc.), não deixar
        exceções genéricas vazarem para o worker de polling.
        """
        raise NotImplementedError


class CarrierConnectorError(Exception):
    """Erro ao consultar uma transportadora (rede, parsing, código inválido)."""
