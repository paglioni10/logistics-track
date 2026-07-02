"""Conector dos Correios.

Os Correios não oferecem uma API pública gratuita e estável para
rastreamento (a API oficial `SRO` é paga e exige contrato comercial).
Para fins de portfólio, este conector implementa o padrão que o
projeto propõe: scraping robusto com fallback.

  1. `_fetch_fast_path`: tenta uma requisição HTTP simples (httpx) à
     página pública de rastreamento. Rápido e barato, mas quebra fácil
     porque depende da página não ser renderizada via JS.
  2. `_fetch_with_browser`: se o fast path falhar (layout mudou, bloqueio
     etc.), cai para scraping com navegador real via Playwright, que
     renderiza JS e é mais resiliente a mudanças simples de markup.

Aviso importante (uso responsável): scraping do site dos Correios deve
respeitar o robots.txt e os Termos de Uso vigentes, e não deve ser usado
em volume alto/produção sem uma revisão jurídica e técnica adequada.
Este conector existe para demonstrar o padrão de engenharia, não para
uso comercial.
"""

from datetime import datetime

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.connectors.base import CarrierConnector, CarrierConnectorError, RawTrackingEvent

TRACKING_URL = "https://rastreamento.correios.com.br/app/index.php"


class CorreiosConnector(CarrierConnector):
    code = "correios"

    async def fetch_events(self, tracking_code: str) -> list[RawTrackingEvent]:
        try:
            events = await self._fetch_fast_path(tracking_code)
            if events:
                return events
        except Exception:
            pass  # cai para o fallback com navegador

        try:
            return await self._fetch_with_browser(tracking_code)
        except Exception as exc:
            raise CarrierConnectorError(
                f"Falha ao rastrear {tracking_code} nos Correios (fast path e browser fallback)."
            ) from exc

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4))
    async def _fetch_fast_path(self, tracking_code: str) -> list[RawTrackingEvent]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{TRACKING_URL}/{tracking_code}")
            response.raise_for_status()
            return self._parse_html(response.text)

    async def _fetch_with_browser(self, tracking_code: str) -> list[RawTrackingEvent]:
        from playwright.async_api import async_playwright

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.goto(f"{TRACKING_URL}/{tracking_code}", wait_until="networkidle")
                # Seletor de exemplo — a estrutura real da página deve ser
                # confirmada manualmente antes de rodar em produção; o site
                # muda o markup com alguma frequência.
                rows = await page.locator("li.linha-status").all_text_contents()
                html = await page.content()
                if rows:
                    return self._parse_rows(rows)
                return self._parse_html(html)
            finally:
                await browser.close()

    def _parse_html(self, html: str) -> list[RawTrackingEvent]:
        """Parser simplificado — ajustar seletores ao HTML real da página."""
        return []

    def _parse_rows(self, rows: list[str]) -> list[RawTrackingEvent]:
        events: list[RawTrackingEvent] = []
        for row in rows:
            events.append(
                RawTrackingEvent(
                    raw_status=row.strip(),
                    occurred_at=datetime.utcnow(),
                    location=None,
                    source="scraping",
                )
            )
        return events
