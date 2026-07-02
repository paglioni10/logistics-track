from enum import StrEnum


class CanonicalStatus(StrEnum):
    """Modelo canônico de status de entrega.

    Toda transportadora conectada precisa mapear seus status
    proprietários para um destes valores — é o contrato que
    permite tratar Correios, Jadlog e regionais de forma uniforme.
    """

    POSTADO = "POSTADO"
    EM_TRANSPORTE = "EM_TRANSPORTE"
    SAIU_PARA_ENTREGA = "SAIU_PARA_ENTREGA"
    ENTREGUE = "ENTREGUE"
    FALHA_ENTREGA = "FALHA_ENTREGA"
    DESCONHECIDO = "DESCONHECIDO"


# Ordem esperada de progressão, usada para detectar regressões de status
# (ex: um evento "EM_TRANSPORTE" chegando depois de "ENTREGUE" é suspeito).
STATUS_ORDER: dict[CanonicalStatus, int] = {
    CanonicalStatus.POSTADO: 0,
    CanonicalStatus.EM_TRANSPORTE: 1,
    CanonicalStatus.SAIU_PARA_ENTREGA: 2,
    CanonicalStatus.ENTREGUE: 3,
    CanonicalStatus.FALHA_ENTREGA: 3,
    CanonicalStatus.DESCONHECIDO: -1,
}


class CarrierCode(StrEnum):
    CORREIOS = "correios"
    JADLOG = "jadlog"
