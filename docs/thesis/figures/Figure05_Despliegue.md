# Figura 5. Arquitectura de despliegue con Docker Compose

| Campo | Valor |
|---|---|
| Número | Figura 5 |
| Nombre | Arquitectura de despliegue del prototipo con Docker Compose |
| Tipo | Diagrama (Mermaid, flujo horizontal) |
| Fuente | [`../diagrams/deployment.mmd`](../diagrams/deployment.mmd) |
| Archivo para el documento | `../diagrams/deployment.png` |
| Ubicación | Anexo C; se cita en VII.C y VII.D |
| Orientación | Ancho completo, vertical |

## Objetivo

Mostrar cómo se ejecuta el prototipo: tres contenedores, sus puertos, sus volúmenes persistentes, la configuración por `.env`, el orden de arranque por verificación de estado y, sobre todo, que **lo único que sale de la infraestructura del proyecto es la llamada HTTPS a la API de Anthropic con los fragmentos de cada consulta**. Esto último respalda el argumento de gobernanza de datos de VI.F.3.

## Qué debe mostrar

- El navegador del usuario fuera del equipo anfitrión, con dos conexiones: la página web (frontend, puerto 5173) y la API REST con JWT (backend, puerto 8000).
- Dentro del equipo anfitrión (Docker Desktop en macOS o Windows):
  - **frontend**: compilado con Node.js y servido por nginx.
  - **backend**: Python 3.12 y FastAPI. Al iniciar aplica las migraciones, crea la cuenta administrativa, comprueba que el índice corresponda a la configuración e indexa los documentos iniciales. Lleva embebidos ChromaDB y all-MiniLM-L6-v2.
  - **postgres**: PostgreSQL 16 con `pg_isready`.
  - Volúmenes `chroma_data`, `documents_data` y `postgres_data`.
  - Archivo `.env` con la clave de API, las credenciales y los parámetros `RAG_*`.
- Las dependencias de arranque: postgres «healthy» habilita al backend, y el backend «healthy» habilita al frontend.
- La API de Anthropic, fuera del equipo, como único servicio externo.

Verificado contra `docker-compose.yml` y `infrastructure/entrypoints/api/main.py`.

## Cómo generarla

Igual que la Figura 4: usa el PNG exportado (4281 × 2409 px) al ancho del texto.

## Pie de figura

> Figura 5. Arquitectura de despliegue del prototipo con Docker Compose. Elaboración propia con base en el repositorio del proyecto.

## Referencia dentro del texto

Insertada en el protocolo (VII.D, después del primer párrafo):

> La Figura 5 (Anexo C) resume este despliegue. Los tres servicios se ejecutan en el mismo equipo y conservan sus datos en volúmenes persistentes; la base vectorial y el modelo de embeddings residen dentro del contenedor del backend, de modo que la única comunicación con el exterior es la llamada cifrada a la API de Anthropic, en la que viajan la pregunta y los fragmentos recuperados para esa consulta.
