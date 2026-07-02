"""Conector Jadlog via API oficial.

A Jadlog exige contrato comercial e credenciais (JADLOG_API_KEY) para
acesso à API de tracking. Este conector fica desativado (levanta
CarrierConnectorError) quando não há credencial configurada — assim o
projeto continua rodando de ponta a ponta usando só o conector dos
Correios, sem custo, e este arquivo serve como referência de como
plugar uma transportadora com API oficial no mesmo contrato
(CarrierConnector) usado pelo scraping.
"""

from datetime import datetime

import httpx

from app.connectors.base import CarrierConnector, CarrierConnectorError, RawTrackingEvent
from app.core.config import get_settings


class JadlogConnector(CarrierConnector):
    code = "jadlog"

    def __init__(self) -> None:
        self._settings = get_settings()

    async def fetch_events(self, tracking_code: str) -> list[RawTrackingEvent]:
        if not self._settings.jadlog_api_key:
            raise CarrierConnectorError(
                "JADLOG_API_KEY não configurada — conector Jadlog desativado "
                "(defina a variável de ambiente para habilitar)."
            )

        headers = {"Authorization": f"Bearer {self._settings.jadlog_api_key}"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{self._settings.jadlog_api_base_url}/{tracking_code}",
                headers=headers,
            )
            response.raise_for_status()
            return self._parse_response(response.json())

    def _parse_response(self, payload: dict) -> list[RawTrackingEvent]:
        events = []
        for item in payload.get("eventos", []):
            events.append(
                RawTrackingEvent(
                    raw_status=item.get("descricao", ""),
                    occurred_at=datetime.fromisoformat(item["dataHora"]),
                    location=item.get("cidade"),
                    source="api",
                )
            )
        return events
