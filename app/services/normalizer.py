"""Normalização de status heterogêneos para o modelo canônico.

Estratégia híbrida: primeiro tenta regras determinísticas (rápidas,
previsíveis, cobrem a grande maioria dos casos reais); só cai para o
fallback via LLM local (app/services/llm_normalizer.py) quando nenhuma
regra bate — mantendo o caminho principal barato e testável.
"""

import re

from app.enums import CanonicalStatus
from app.services.llm_normalizer import classify_with_llm

# Ordem importa: regras mais específicas primeiro (ex: "saiu para
# entrega" antes de "em transporte", já que ambas mencionam trânsito).
_RULES: list[tuple[re.Pattern[str], CanonicalStatus]] = [
    (re.compile(r"objeto\s+postado", re.I), CanonicalStatus.POSTADO),
    (re.compile(r"postagem\s+(realizada|efetuada)", re.I), CanonicalStatus.POSTADO),
    (re.compile(r"saiu\s+para\s+entrega", re.I), CanonicalStatus.SAIU_PARA_ENTREGA),
    (re.compile(r"entregue|entrega\s+efetuada|delivered", re.I), CanonicalStatus.ENTREGUE),
    (
        re.compile(r"tentativa\s+de\s+entrega\s+n[aã]o\s+efetuada|destinat[aá]rio\s+ausente", re.I),
        CanonicalStatus.FALHA_ENTREGA,
    ),
    (re.compile(r"extravio|avaria|dev(olvido|olu[cç][aã]o)", re.I), CanonicalStatus.FALHA_ENTREGA),
    (
        re.compile(r"em\s+tr[aâ]nsito|em\s+transporte|encaminhado|in\s+transit", re.I),
        CanonicalStatus.EM_TRANSPORTE,
    ),
]


def normalize_by_rules(raw_status: str) -> CanonicalStatus:
    for pattern, canonical in _RULES:
        if pattern.search(raw_status):
            return canonical
    return CanonicalStatus.DESCONHECIDO


async def normalize(raw_status: str) -> CanonicalStatus:
    """Ponto de entrada usado pelo serviço de tracking.

    Tenta as regras primeiro; só invoca o LLM local se nada casar.
    """
    canonical = normalize_by_rules(raw_status)
    if canonical is not CanonicalStatus.DESCONHECIDO:
        return canonical
    return await classify_with_llm(raw_status)
