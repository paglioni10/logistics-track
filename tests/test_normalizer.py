import pytest

from app.enums import CanonicalStatus
from app.services.normalizer import normalize, normalize_by_rules


@pytest.mark.parametrize(
    "raw_status,expected",
    [
        ("Objeto postado", CanonicalStatus.POSTADO),
        ("Objeto em trânsito - por favor aguarde", CanonicalStatus.EM_TRANSPORTE),
        ("Objeto saiu para entrega ao destinatário", CanonicalStatus.SAIU_PARA_ENTREGA),
        ("Objeto entregue ao destinatário", CanonicalStatus.ENTREGUE),
        ("Tentativa de entrega não efetuada - destinatário ausente", CanonicalStatus.FALHA_ENTREGA),
        ("Texto totalmente desconhecido sem nenhuma pista", CanonicalStatus.DESCONHECIDO),
    ],
)
def test_normalize_by_rules(raw_status: str, expected: CanonicalStatus) -> None:
    assert normalize_by_rules(raw_status) == expected


@pytest.mark.asyncio
async def test_normalize_falls_back_to_desconhecido_when_llm_disabled() -> None:
    # Com LLM_NORMALIZER_ENABLED=false (padrão), o fallback deve retornar
    # DESCONHECIDO em vez de tentar chamar o Ollama.
    result = await normalize("mensagem totalmente fora do padrão esperado")
    assert result == CanonicalStatus.DESCONHECIDO
