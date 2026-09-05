# Backend — Asistente Virtual RAG (UVG Altiplano)

Backend en Python 3.12 / FastAPI, organizado bajo Arquitectura Hexagonal + Clean Architecture. Ver `docs/04-software-architecture.md` en la raíz del repositorio para el detalle completo de capas, puertos y principios aplicados.

## Estructura

```
src/app/
├── domain/          # Entidades, value objects y puertos (interfaces). Sin dependencias externas.
├── application/     # Casos de uso. Depende solo de domain.
├── infrastructure/  # Adaptadores concretos + entrypoints HTTP + configuración. Depende de domain y application.
└── shared/          # Logging, excepciones base, utilidades transversales sin lógica de negocio.
tests/
├── unit/            # Casos de uso probados con dobles de los puertos, sin infraestructura real.
├── integration/     # Adaptadores probados contra infraestructura real (Postgres, Chroma) en contenedores de prueba.
└── e2e/             # Flujos completos vía el API HTTP.
```

## Regla de dependencia

`infrastructure → application → domain`. Nunca al revés. Ningún archivo en `domain/` o `application/` puede importar `fastapi`, `anthropic`, `chromadb`, `sqlalchemy` ni `sentence_transformers` directamente — solo a través de los puertos definidos en `domain/ports`.

## Estado actual

Implementado y probado (54 pruebas: unitarias, integración contra PostgreSQL/ChromaDB reales, y e2e contra la API real vía `TestClient`): EPIC-1 (ingesta), EPIC-2 (núcleo RAG con Chain-of-Verification de una sola llamada), EPIC-3 (autenticación institucional) y EPIC-7 (panel administrativo).

## Comandos

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Pruebas unitarias (no requieren infraestructura)
pytest tests/unit -v

# Pruebas de integración y e2e: requieren un PostgreSQL propio en localhost:5433
# (separado del de docker-compose.yml en 5432, para poder TRUNCATE tablas entre pruebas
# sin afectar datos de desarrollo):
#   docker run -d --name uvg-rag-test-postgres -e POSTGRES_USER=rag_app \
#     -e POSTGRES_PASSWORD=devpassword -e POSTGRES_DB=asistente_rag \
#     -p 5433:5432 postgres:16-alpine
pytest tests/integration tests/e2e -v

# Migraciones
alembic upgrade head

# Servidor de desarrollo
uvicorn app.infrastructure.entrypoints.api.main:app --reload
```

Requiere las variables de entorno del `.env.example` de la raíz del repositorio.
