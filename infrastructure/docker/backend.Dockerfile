# Multi-stage build: compila dependencias en una capa, copia solo lo necesario a la imagen final.
FROM python:3.12-slim AS builder

WORKDIR /build

# Dependencias de compilación para paquetes con extensiones nativas (psycopg, sentence-transformers).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src ./src

# --timeout/--retries: sentence-transformers/torch son descargas pesadas (cientos de MB);
# el timeout por defecto de pip es demasiado agresivo en redes lentas.
#
# torch se instala PRIMERO desde el indice CPU-only de PyTorch, en el MISMO entorno donde
# luego se instala el resto (sin --prefix intermedio): este contenedor nunca usa GPU (los
# embeddings corren sobre CPU), y el paquete generico de torch en PyPI arrastra varios GB de
# librerias CUDA/NVIDIA innecesarias. Al instalarlo primero, pip ya lo encuentra satisfecho
# cuando sentence-transformers lo pide como dependencia en el segundo paso.
RUN pip install --no-cache-dir --timeout=180 --retries=5 \
        torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir --timeout=180 --retries=5 .

FROM python:3.12-slim AS final

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 appuser

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini
COPY documents ./documents
COPY docker-entrypoint.sh ./docker-entrypoint.sh

# Pre-descarga el modelo de embeddings EN TIEMPO DE BUILD, no al arrancar el contenedor:
# el arranque de la demo no debe depender de la disponibilidad/velocidad de HuggingFace Hub.
ENV HOME=/home/appuser
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

RUN chmod +x ./docker-entrypoint.sh \
    && mkdir -p /app/data/chroma /app/data/documents \
    && chown -R appuser:appuser /app /home/appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=60s \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["./docker-entrypoint.sh"]
