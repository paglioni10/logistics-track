from app.connectors.base import CarrierConnector
from app.connectors.correios import CorreiosConnector
from app.connectors.jadlog import JadlogConnector
from app.enums import CarrierCode

_CONNECTORS: dict[str, type[CarrierConnector]] = {
    CarrierCode.CORREIOS: CorreiosConnector,
    CarrierCode.JADLOG: JadlogConnector,
}


def get_connector(carrier_code: str) -> CarrierConnector:
    connector_cls = _CONNECTORS.get(carrier_code)
    if connector_cls is None:
        raise ValueError(f"Nenhum conector registrado para a transportadora '{carrier_code}'")
    return connector_cls()
