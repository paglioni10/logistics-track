# Logistics Track

API que agrega rastreamento de múltiplas transportadoras (Correios,
Jadlog, regionais) em um **modelo canônico de status**, mantém
histórico de eventos e dispara **webhooks outbound** quando o status
de uma entrega muda.

> Projeto de portfólio. Não é um produto comercial nem está pronto
> para produção real — o objetivo é demonstrar arquitetura e padrões
> de engenharia (integração com fontes heterogêneas, scraping
> responsável com fallback, filas assíncronas, webhooks assinados).

![Demo do normalizador híbrido rodando via scripts/demo.py](docs/demo.gif)

*Demo real (não é mockup): `python -m scripts.demo` roda o normalizador
híbrido (regras + fallback via LLM local) e o webhook dispatcher
ponta a ponta, em SQLite em memória — sem precisar subir Docker.*

## Por que esse projeto

Empresas que despacham por mais de uma transportadora não têm visão
unificada do status das entregas — o time de suporte perde tempo
consultando cada site manualmente. Este serviço centraliza isso:
consulta as transportadoras periodicamente, normaliza os status
proprietários de cada uma para um enum comum e notifica sistemas
externos via webhook quando algo muda.

## Arquitetura

```
FastAPI (API síncrona)  ──┐
                          ├─► PostgreSQL (shipments, tracking_events, webhooks)
Celery beat + workers  ──┘
        │
        ├─► Conectores (app/connectors/)
        │     ├─ CorreiosConnector: scraping com fallback
        │     │    (httpx "fast path" → Playwright como resiliente)
        │     └─ JadlogConnector: API oficial (requer credencial)
        │
        ├─► Normalizador (app/services/normalizer.py)
        │     ├─ regras determinísticas (regex) — caminho principal
        │     └─ fallback via LLM local (Ollama) — só para status
        │        que nenhuma regra reconhece
        │
        └─► Webhook dispatcher (HMAC-SHA256, retry com backoff)
```

Modelo canônico de status: `POSTADO`, `EM_TRANSPORTE`,
`SAIU_PARA_ENTREGA`, `ENTREGUE`, `FALHA_ENTREGA`, `DESCONHECIDO`.

## Sem custo financeiro, de propósito

Toda a stack roda localmente e sem chave de API paga:

- **Banco e fila**: PostgreSQL e Redis via `docker-compose` (imagens
  oficiais gratuitas, sem serviço gerenciado).
- **Scraping**: Playwright (Chromium headless, gratuito).
- **IA usada no normalizador**: fallback opcional via
  [Ollama](https://ollama.com) rodando um modelo local (ex:
  `llama3.2`) — zero custo por token porque roda 100% na sua máquina.
  Fica **desligado por padrão** (`LLM_NORMALIZER_ENABLED=false`); as
  regras determinísticas cobrem a maioria dos casos reais e o LLM
  entra só como exceção para textos de status fora do esperado.
- **Conector Jadlog**: usa API oficial, mas fica automaticamente
  desativado se `JADLOG_API_KEY` não for configurada — o projeto roda
  de ponta a ponta só com o conector dos Correios.

## Rodando localmente

### Caminho mais rápido: só a demo (sem Docker)

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m scripts.demo
```

Roda em ~3 segundos, sem banco, sem Redis, sem rede — mostra o
normalizador híbrido e o webhook dispatcher com dados de exemplo. É o
que gerou o GIF acima.

### Stack completa (API + polling + banco)

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium

cp .env.example .env
docker compose up -d          # sobe Postgres + Redis

alembic revision --autogenerate -m "schema inicial"
alembic upgrade head
python -m scripts.seed_carriers

uvicorn app.main:app --reload           # API em http://localhost:8000/docs
celery -A app.workers.celery_app worker --beat --loglevel=info  # polling
```

### IA gratuita (opcional)

Duas formas de habilitar, sem custo:

```bash
# Opção 1: junto com o resto da stack, via Docker (baixa ~2GB na primeira vez)
docker compose --profile llm up -d

# Opção 2: instalando o Ollama direto na máquina (https://ollama.com)
ollama pull llama3.2
ollama serve
```

Em ambos os casos, defina `LLM_NORMALIZER_ENABLED=true` no `.env` e
rode `python -m scripts.demo` de novo — o evento de exemplo que as
regras não reconhecem passa a ser classificado pelo LLM local em vez
de cair em `DESCONHECIDO`.

## Testes

```bash
pytest
```

Os testes de API usam SQLite em memória (sem depender do Postgres) e
os testes do normalizador validam as regras determinísticas e o
fallback com o LLM desligado.

## Endpoints principais

- `POST /shipments` — registra uma entrega para rastreamento
- `GET /tracking/{codigo}` — consulta status e histórico
- `POST /tracking/{codigo}/refresh` — força um polling imediato
- `POST /webhooks` — assina notificações de mudança de status
- `GET /metrics/status-breakdown`, `/metrics/carrier-sla`,
  `/metrics/stalled` — métricas operacionais (base de um dashboard)

## Limitações conhecidas (honestidade > venda)

- O parser do `CorreiosConnector` (`_parse_html`/`_parse_rows`) tem
  seletores de exemplo — a página pública dos Correios muda de
  markup com frequência, então os seletores reais precisam ser
  conferidos manualmente antes de rodar de verdade.
- Scraping deve respeitar `robots.txt` e os Termos de Uso da
  transportadora; este projeto não foi pensado para volume alto nem
  uso comercial.
- Não há autenticação na API — para portfólio isso é aceitável, mas
  seria o primeiro item a resolver antes de qualquer uso real.

## Possíveis evoluções

Previsão de atraso com ML, chat automatizado de status para o
cliente final, integração com Shopify/VTEX, notificações via
WhatsApp/SMS.
