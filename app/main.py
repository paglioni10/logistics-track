from fastapi import FastAPI

from app.api.routes import metrics, shipments, tracking, webhooks

app = FastAPI(
    title="Logistics Track",
    description=(
        "API de rastreamento logístico que agrega múltiplas transportadoras "
        "em um modelo canônico de status de entrega."
    ),
    version="0.1.0",
)

app.include_router(shipments.router)
app.include_router(tracking.router)
app.include_router(webhooks.router)
app.include_router(metrics.router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
