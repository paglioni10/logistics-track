"""Fallback de normalização via LLM local (Ollama) — IA 100% gratuita.

Roda inteiramente na máquina local, sem chave de API e sem custo por
token: https://ollama.com. Instale, rode `ollama pull llama3.2` e
`ollama serve`; o resto é uma chamada HTTP comum ao endpoint local.

Este módulo só é chamado quando o normalizador baseado em regras
(`app/services/normalizer.py`) não reconhece o texto bruto de status —
ou seja, o LLM é a exceção, não o caminho principal. Isso é
proposital: regras determinísticas são mais baratas, previsíveis e
fáceis de testar; o LLM entra só para lidar com a cauda longa de
variações de texto entre transportadoras.
"""

import json

import httpx

from app.core.config import get_settings
from app.enums import CanonicalStatus

_PROMPT_TEMPLATE = """\
Classifique o status de rastreio de encomenda abaixo em EXATAMENTE uma
das categorias a seguir, respondendo só com a categoria, sem explicação:

POSTADO, EM_TRANSPORTE, SAIU_PARA_ENTREGA, ENTREGUE, FALHA_ENTREGA, DESCONHECIDO

Texto do status: "{raw_status}"
Categoria:"""


async def classify_with_llm(raw_status: str) -> CanonicalStatus:
    """Consulta o Ollama local para classificar um status ambíguo.

    Retorna DESCONHECIDO se o LLM estiver desligado, indisponível, ou
    responder algo fora do enum esperado — nunca levanta exceção para
    o chamador, já que isso é um fallback best-effort.
    """
    settings = get_settings()
    if not settings.llm_normalizer_enabled:
        return CanonicalStatus.DESCONHECIDO

    prompt = _PROMPT_TEMPLATE.format(raw_status=raw_status)
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={"model": settings.ollama_model, "prompt": prompt, "stream": False},
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, json.JSONDecodeError):
        return CanonicalStatus.DESCONHECIDO

    answer = data.get("response", "").strip().upper()
    for status in CanonicalStatus:
        if status.value in answer:
            return status
    return CanonicalStatus.DESCONHECIDO
