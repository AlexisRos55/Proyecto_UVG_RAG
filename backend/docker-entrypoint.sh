#!/bin/sh
# Aplica las migraciones de Alembic antes de arrancar la API: sin esto, un Postgres
# recien creado (docker compose up en una maquina nueva) no tiene tablas.
set -e

alembic upgrade head

exec uvicorn app.infrastructure.entrypoints.api.main:app --host 0.0.0.0 --port 8000
