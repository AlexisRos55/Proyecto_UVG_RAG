# Asistente Virtual Institucional — RAG UVG Altiplano

Trabajo de Graduación — Ingeniería en Tecnología de Sistemas Informáticos, Universidad del Valle de Guatemala, Campus Altiplano.

## Descripción

Asistente conversacional institucional que responde preguntas de estudiantes sobre reglamentos, becas, beneficios y seguro estudiantil de UVG Altiplano. Está construido sobre una arquitectura de **Recuperación Aumentada por Generación (RAG)**: cada respuesta se genera exclusivamente a partir de fragmentos recuperados de documentos oficiales indexados, nunca del conocimiento general del modelo. Si no encuentra evidencia suficiente en los documentos, el sistema lo declara explícitamente en lugar de inventar una respuesta.

## Objetivo

Reducir la carga de consultas repetitivas hacia las oficinas administrativas del campus (Registro Académico, Becas, Seguro Estudiantil, etc.), ofreciendo a los estudiantes una vía de autoservicio conversacional, disponible en todo momento, cuyas respuestas están siempre respaldadas por una fuente documental verificable.

## Estado del proyecto

El proyecto fue diseñado en fases (documentación de arquitectura → implementación) y actualmente cubre un **Sprint 1 de demostración**: login institucional, chat con flujo RAG completo end-to-end, citación de fuentes y panel administrativo de documentos, todo verificado corriendo contra una base de datos, un vector store y un modelo de Claude reales.

| Área | Estado |
|---|---|
| Ingesta documental (PDF → limpieza → chunking → embeddings → ChromaDB) | Implementado y validado con documentos reales |
| Núcleo conversacional RAG (recuperación + verificación + respuesta) | Implementado (Chain-of-Verification de una sola llamada), validado end-to-end |
| Autenticación institucional | Implementado (registro, login, bcrypt, JWT, roles estudiante/admin) |
| Frontend de chat | Implementado, con design system propio e identidad UVG (ver capturas) |
| Panel administrativo de documentos | Implementado (subir / listar / eliminar / reindexar), sin rediseño visual todavía |
| Infraestructura Docker Compose | Implementado y verificado (`docker compose up --build` levanta los 3 servicios) |
| Evaluación con RAGAS | Script implementado; pendiente de ejecutarse con una `ANTHROPIC_API_KEY` real para obtener métricas |

Cobertura de pruebas automatizadas del backend: **54 pruebas** (unitarias, de integración contra PostgreSQL/ChromaDB reales, y end-to-end contra la API real) — ver `backend/tests/`.

> **Nota honesta:** el corpus de documentos que se incluye en este repositorio (`backend/documents/`) es un **corpus de ejemplo ficticio** (reglamento, becas y seguro estudiantil de muestra), no los documentos oficiales reales de UVG Altiplano. El sistema fue validado también con documentos reales cargados manualmente vía el panel administrativo durante el desarrollo, pero esos archivos no se distribuyen en este repositorio. Para una demostración con contenido real, cárgalos desde `/admin` una vez el sistema esté corriendo.

## Capturas de pantalla

**Inicio de sesión**

![Login](docs/screenshots/login.png)

**Chat — pantalla de bienvenida con sugerencias**

![Chat vacío](docs/screenshots/chat-empty.png)

**Chat — respuesta con citación de fuentes**

![Conversación](docs/screenshots/chat-conversation.png)

**Modo oscuro**

![Modo oscuro](docs/screenshots/chat-dark.png)

## Características principales

- **Chat institucional** con respuestas fundamentadas exclusivamente en documentos oficiales indexados.
- **Citación de fuentes**: cada respuesta muestra el/los documento(s) PDF de los que proviene la información.
- **Abstención explícita**: si no hay contexto relevante o la verificación determina que la respuesta no está fundamentada, el asistente lo comunica en vez de alucinar.
- **Autenticación institucional** restringida a correos `@uvg.edu.gt`, con sesiones JWT y contraseñas con hash bcrypt.
- **Roles estudiante / administrador**, con endpoints y vistas protegidas según el rol.
- **Panel administrativo de documentos**: subir, listar, eliminar y reindexar PDFs desde la interfaz, sin reiniciar el servicio.
- **Ingesta automática al arrancar**: cualquier PDF colocado en `backend/documents/` se indexa solo la primera vez que el backend inicia.
- **Modelo de Claude configurable por variable de entorno** (`ANTHROPIC_MODEL`), sin hardcodear el modelo en el código.
- **Design system propio** (`frontend/src/design-system/`) con escala tipográfica, sombras, curvas de movimiento y componentes reutilizables, en lugar de estilos dispersos por componente.
- **Identidad visual UVG** derivada del manual de normas gráficas oficial (`docs/design/brand-source/`): verde institucional `#008C36` como acento en modo claro y verde MASTERS `#0DF2B0` en modo oscuro, ambos tomados de la paleta oficial. El color de marca se usa solo en acentos, nunca como superficie.
- **Modo claro y oscuro**, con conmutador en la aplicación y respeto por la preferencia del sistema.
- **Interfaz responsiva**, con panel lateral colapsable en pantallas pequeñas.
- **Dockerizado end-to-end**: `docker compose up --build` levanta base de datos, backend y frontend con healthchecks y migraciones automáticas.
- **Script de evaluación con RAGAS** (fidelidad, relevancia, precisión y exhaustividad de contexto) sobre un dataset de referencia (`scripts/golden_dataset.json`).

## Tecnologías utilizadas

**Backend**

| Tecnología | Uso |
|---|---|
| Python 3.12 + FastAPI | API HTTP |
| Pydantic v2 / Pydantic Settings | Validación de datos y configuración |
| Anthropic SDK (directo, sin LangChain en producción) | Generación y verificación de respuestas (Claude) |
| ChromaDB | Vector store para búsqueda semántica |
| Sentence Transformers (`all-MiniLM-L6-v2`) | Generación de embeddings |
| PyMuPDF | Extracción de texto de documentos PDF |
| SQLAlchemy 2.x (async) + Alembic | Persistencia relacional y migraciones |
| PostgreSQL 16 | Base de datos relacional (usuarios, conversaciones, mensajes, documentos) |
| bcrypt + PyJWT | Hash de contraseñas y sesiones JWT |
| Loguru | Logging estructurado |
| pytest / ruff / mypy | Pruebas y calidad de código |
| RAGAS (solo en `scripts/evaluate.py`) | Evaluación offline de calidad del pipeline RAG |

**Frontend**

| Tecnología | Uso |
|---|---|
| React 19 + TypeScript + Vite | SPA |
| Tailwind CSS v4 + shadcn/ui | Estilos y componentes de UI |
| TanStack Query | Estado de servidor / llamadas a la API |
| React Hook Form + Zod | Formularios y validación |
| React Router | Enrutamiento |
| Framer Motion | Animaciones y microinteracciones |
| react-markdown + remark-gfm | Renderizado de las respuestas del asistente |
| next-themes | Modo claro / oscuro |
| Vitest + Testing Library | Pruebas de componentes |

**Infraestructura**

| Tecnología | Uso |
|---|---|
| Docker + Docker Compose | Orquestación local de los 3 servicios |
| nginx | Servidor estático de producción del frontend |

## Arquitectura

El backend sigue **Arquitectura Hexagonal (Ports & Adapters)** combinada con **Clean Architecture** y los principios **SOLID**. El detalle completo, con diagramas, está en [`docs/04-software-architecture.md`](docs/04-software-architecture.md) y en los [ADRs](docs/adr/). Resumen:

- **Ports & Adapters**: el dominio y los casos de uso definen *puertos* (interfaces) como `LLMPort`, `VectorStorePort`, `EmbeddingPort` o `UserRepositoryPort`. Cada tecnología concreta (Anthropic, ChromaDB, Sentence Transformers, PostgreSQL) es un *adaptador* que implementa un puerto. Esto permite, por ejemplo, cambiar de ChromaDB a otro vector store sin tocar la lógica de negocio.
- **Clean Architecture (regla de dependencia)**: las dependencias solo apuntan hacia adentro — `infrastructure → application → domain`. El dominio (`domain/`) no conoce FastAPI, Anthropic, ChromaDB ni SQLAlchemy; solo depende de sus propios puertos.
- **SOLID**: cada caso de uso tiene una única responsabilidad (S); los puertos permiten extender con nuevos adaptadores sin modificar el código existente (O); los adaptadores son intercambiables porque cumplen el contrato del puerto (L); los puertos son específicos y pequeños en vez de una única interfaz gigante (I); los casos de uso dependen de abstracciones (los puertos), no de implementaciones concretas (D).
- **Frontend por *features*** (no por tipo de archivo): cada feature (`auth`, `chat`, `admin`) es autocontenida, con sus propios componentes, hooks y llamadas a la API.

Todas las decisiones técnicas relevantes están documentadas como **ADR** (Architecture Decision Record) en [`docs/adr/`](docs/adr/), con alternativas consideradas, ventajas, desventajas y justificación — pensado para sustentar la defensa académica del trabajo de graduación.

## Estructura del proyecto

```
.
├── backend/                  # API FastAPI — Arquitectura Hexagonal (ver backend/README.md)
│   ├── src/app/
│   │   ├── domain/           # Entidades, value objects y puertos. Sin dependencias externas.
│   │   ├── application/      # Casos de uso. Depende solo de domain.
│   │   ├── infrastructure/   # Adaptadores concretos, entrypoints HTTP, configuración.
│   │   └── shared/           # Logging, excepciones base, utilidades transversales.
│   ├── tests/                # unit/ · integration/ · e2e/
│   ├── migrations/           # Migraciones Alembic
│   ├── documents/            # Corpus de ejemplo indexado automáticamente al arrancar
│   └── docker-entrypoint.sh
├── frontend/                  # SPA React + TypeScript (ver frontend/README.md)
│   └── src/
│       ├── app/               # Enrutamiento y providers globales
│       ├── features/          # auth/ · chat/ · admin/
│       └── shared/            # Cliente HTTP, tipos compartidos, componentes UI reutilizables
├── infrastructure/docker/     # Dockerfiles (backend y frontend, multi-stage)
├── scripts/                   # Ingesta manual, generación de corpus de ejemplo, evaluación RAGAS
├── docs/                      # Documentación de arquitectura, ADRs, diseño y capturas
├── docker-compose.yml
├── .env.example
└── LICENSE
```

## Documentación

| Documento | Contenido |
|---|---|
| [docs/00-project-charter.md](docs/00-project-charter.md) | Propósito, objetivos, alcance, restricciones y criterios de éxito |
| [docs/01-project-vision.md](docs/01-project-vision.md) | Visión de producto, usuarios objetivo, principios de diseño |
| [docs/02-functional-requirements.md](docs/02-functional-requirements.md) | Requisitos funcionales trazables (FR-01 a FR-19) |
| [docs/03-non-functional-requirements.md](docs/03-non-functional-requirements.md) | Requisitos no funcionales con justificación |
| [docs/04-software-architecture.md](docs/04-software-architecture.md) | Arquitectura Hexagonal + Clean Architecture, capas, puertos, SOLID aplicado |
| [docs/05-technology-decisions.md](docs/05-technology-decisions.md) | Matriz de decisiones tecnológicas con justificación |
| [docs/06-high-level-architecture.md](docs/06-high-level-architecture.md) | Diagramas C4, secuencia, despliegue, evolución futura |
| [docs/07-backlog.md](docs/07-backlog.md) | Backlog inicial por épicas |
| [docs/08-roadmap.md](docs/08-roadmap.md) | Roadmap con análisis de capacidad real |
| [docs/09-risk-register.md](docs/09-risk-register.md) | Registro de riesgos técnicos y de proyecto |
| [docs/10-addendum-tecnico-implementacion.md](docs/10-addendum-tecnico-implementacion.md) | Addendum Técnico de Implementación (ATI) — reconcilia el Protocolo de Investigación con las decisiones técnicas reales, sin modificarlo (borrador de diseño; redacción final pendiente de congelamiento total del proyecto) |
| [docs/11-reproducibility.md](docs/11-reproducibility.md) | Matriz oficial de parámetros experimentales congelados y guía de instalación reproducible exacta |
| [docs/adr/](docs/adr/) | Architecture Decision Records — cada decisión con alternativas, ventajas, desventajas y trade-offs |
| [docs/source/](docs/source/) | Especificación funcional original del asesor y Protocolo de Investigación |

---

## Guía de instalación en Windows (desde cero)

Esta guía asume una computadora con **Windows 10/11** recién instalada, sin ninguna de estas herramientas.

### 1. Instalar Git

1. Descarga el instalador desde [git-scm.com](https://git-scm.com/downloads/win).
2. Ejecuta el instalador dejando las opciones por defecto.
3. Verifica la instalación abriendo **PowerShell** y ejecutando:
   ```powershell
   git --version
   ```

### 2. Instalar Docker Desktop

1. Descarga Docker Desktop desde [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/).
2. Durante la instalación, acepta habilitar **WSL 2** (Docker lo solicitará si no está activo).
3. Reinicia la computadora si el instalador lo pide.
4. Abre Docker Desktop y espera a que el ícono de la ballena indique que está corriendo.
5. Verifica en PowerShell:
   ```powershell
   docker --version
   docker compose version
   ```

> Si solo vas a ejecutar el proyecto con Docker (recomendado para una primera prueba), puedes saltar los pasos 3 y 4 e ir directo a la sección **"Ejecución con Docker"**.

### 3. Instalar Python 3.12

1. Descarga Python 3.12 desde [python.org/downloads](https://www.python.org/downloads/windows/) (usa la versión 3.12.x, no una posterior — el proyecto fija `requires-python = ">=3.12"` pero fue desarrollado y probado en 3.12).
2. Durante la instalación, **marca la casilla "Add python.exe to PATH"**.
3. Verifica:
   ```powershell
   python --version
   ```

### 4. Instalar Node.js

1. Descarga Node.js **LTS** desde [nodejs.org](https://nodejs.org/en/download) (el proyecto usa Node 22 en su imagen Docker; instala esa versión LTS o superior).
2. Instala dejando las opciones por defecto (incluye `npm`).
3. Verifica:
   ```powershell
   node --version
   npm --version
   ```

### 5. Clonar el repositorio

```powershell
git clone https://github.com/AlexisRos55/Proyecto_UVG_RAG.git
cd Proyecto_UVG_RAG
```

### 6. Crear el archivo `.env`

```powershell
copy .env.example .env
```

Abre `.env` con un editor de texto y completa como mínimo:

- `ANTHROPIC_API_KEY`: tu clave real de la API de Anthropic (Claude). Sin esto, el chat no podrá generar respuestas.
- `SESSION_SECRET`: un valor aleatorio de al menos 32 caracteres. Puedes generarlo con:
  ```powershell
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- El resto de variables ya tienen valores por defecto razonables para correr localmente (ver comentarios dentro del archivo).

A partir de aquí tienes dos caminos: **Docker** (recomendado, todo se levanta con un solo comando) o **manual** (backend y frontend corridos directamente en tu máquina). Ambos se explican abajo.

---

## Ejecución con Docker

Con Docker Desktop corriendo y el archivo `.env` ya creado:

```powershell
docker compose up --build
```

Esto levanta tres servicios:

| Servicio | Qué hace | Puerto |
|---|---|---|
| `postgres` | Base de datos PostgreSQL 16, con un volumen persistente para no perder datos entre reinicios | `5432` |
| `backend` | Aplica las migraciones de Alembic, siembra la cuenta admin de demo y el corpus de ejemplo, y levanta la API FastAPI (Uvicorn) | `8000` |
| `frontend` | Compila el SPA de React con Vite y lo sirve como archivos estáticos vía nginx | `5173` |

El backend tiene un `healthcheck` con `start_period` de 60s (la primera vez que arranca hace más trabajo: migraciones + siembra de datos), y el frontend espera a que el backend esté saludable antes de arrancar.

Una vez que los tres contenedores muestren `healthy` (`docker compose ps`), abre:

```
http://localhost:5173
```

Para detener todo:

```powershell
docker compose down
```

Para detenerlo y **borrar también los datos** (base de datos, documentos indexados, etc.):

```powershell
docker compose down -v
```

---

## Ejecución sin Docker

Útil para desarrollo activo del backend o del frontend. Requiere PostgreSQL corriendo por separado (puedes usar Docker solo para la base de datos, ver abajo).

### Base de datos

Si no quieres instalar PostgreSQL nativamente en Windows, la forma más simple es levantar solo el contenedor de Postgres con Docker:

```powershell
docker run -d --name uvg-rag-postgres `
  -e POSTGRES_USER=rag_app `
  -e POSTGRES_PASSWORD=devpassword123 `
  -e POSTGRES_DB=asistente_rag `
  -p 5432:5432 `
  postgres:16-alpine
```

(El backtick `` ` `` es el separador de línea de PowerShell; en `cmd.exe` escribe el comando en una sola línea.)

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"

# Aplicar migraciones
alembic upgrade head

# Levantar el servidor de desarrollo (recarga automática)
uvicorn app.infrastructure.entrypoints.api.main:app --reload
```

El backend queda disponible en `http://localhost:8000` (documentación interactiva en `http://localhost:8000/docs`, generada automáticamente por FastAPI).

La cuenta admin de demo y el corpus de ejemplo (`backend/documents/*.pdf`) se siembran **automáticamente la primera vez que el proceso arranca** — no hace falta ningún comando adicional. Si quieres reindexar manualmente o agregar documentos después, puedes correr:

```powershell
python scripts/ingest.py                 # reingesta backend/documents/
```

### Frontend

En otra terminal:

```powershell
cd frontend
npm install
npm run dev
```

El frontend queda disponible en `http://localhost:5173` y llama al backend en `http://localhost:8000` (variable `VITE_API_BASE_URL`, ver `frontend/.env.example`).

> `npm install` es para desarrollo normal. Para reproducir exactamente el entorno usado en la validación experimental (Fase V del protocolo), usa `npm ci` en su lugar, que instala estrictamente lo fijado en `package-lock.json` — ver [docs/11-reproducibility.md](docs/11-reproducibility.md).

### Variables de entorno relevantes fuera de Docker

Cuando corres el backend directamente (no en contenedor), asegúrate de que `DATABASE_URL` en tu `.env` apunte a `localhost` en vez del nombre de servicio `postgres`, por ejemplo:

```
DATABASE_URL=postgresql+psycopg://rag_app:devpassword123@localhost:5432/asistente_rag
```

---

## Usuarios de demostración

El sistema siembra automáticamente una cuenta de administrador la primera vez que arranca (ver `app/infrastructure/bootstrap.py`), usando las credenciales definidas en `.env`:

**Administrador**

- Correo: `admin@uvg.edu.gt`
- Contraseña: `admin123`
- Rol: `admin` (acceso al panel `/admin` además del chat)

> Estas credenciales son **solo para demostración local**. Si el proyecto se despliega más allá de una demo en tu propia máquina, cambia `DEFAULT_ADMIN_EMAIL` / `DEFAULT_ADMIN_PASSWORD` en `.env` antes de arrancar por primera vez, o rota la contraseña del usuario después.

También existe una pantalla de registro (`/register`) para crear cuentas de estudiante con cualquier correo `@uvg.edu.gt` — no está enlazada desde la barra de navegación en esta versión (decisión de alcance del Sprint 1, ver [ADR-0011](docs/adr/0011-sprint1-demo-scope.md)), pero la ruta y el endpoint (`POST /auth/register`) están implementados y funcionan.

## Funcionalidades implementadas

- Inicio de sesión institucional (`@uvg.edu.gt`) con JWT y bcrypt.
- Registro de nuevos estudiantes (`POST /auth/register`, ruta `/register`).
- Chat conversacional con flujo RAG completo: pregunta → embedding → búsqueda semántica en ChromaDB → verificación de fundamentación → respuesta.
- Citación de fuentes documentales en cada respuesta fundamentada.
- Abstención explícita cuando no hay evidencia suficiente (sin llamar al LLM si no hay contexto relevante).
- Historial de conversación por estudiante (`GET /chat/history`).
- Panel administrativo de documentos: subir (`POST /admin/documents`), listar (`GET /admin/documents`), consultar estado de un documento (`GET /admin/documents/{id}`), eliminar (`DELETE /admin/documents/{id}`) y reindexar (`POST /admin/documents/{id}/reindex`).
- Ingesta automática al arrancar del corpus en `backend/documents/`.
- Roles de autorización estudiante/administrador (`ADMIN_EMAILS` + cuenta admin sembrada).
- Extracción de texto con PyMuPDF, limpieza y *chunking* de tamaño fijo con solapamiento.
- Embeddings con Sentence Transformers (`all-MiniLM-L6-v2`) y almacenamiento vectorial en ChromaDB.
- Generación y verificación de respuestas con Claude (Anthropic SDK directo, sin LangChain en el pipeline de producción).
- Modelo de Claude configurable por variable de entorno (`ANTHROPIC_MODEL`).
- Logging estructurado de latencia por etapa (recuperación / generación) con Loguru.
- Contenedores Docker multi-stage para backend y frontend, con healthchecks y migraciones automáticas.
- Script de evaluación offline con RAGAS (fidelidad, relevancia, precisión y exhaustividad de contexto) sobre un dataset de referencia.
- Suite de pruebas automatizadas: 54 pruebas de backend (unitarias, integración y end-to-end) + prueba de regresión de formulario en frontend.
- Diseño institucional propio para login y chat, basado en el manual de normas gráficas de UVG (colores, tipografía y logotipos oficiales).

## Trabajo futuro

Funcionalidades identificadas y priorizadas en el backlog (`docs/07-backlog.md`) que **no** forman parte del alcance actual:

- Gestión completa de usuarios (edición de perfil, recuperación de contraseña real, administración de roles desde la UI).
- Panel administrativo con diseño visual propio (actualmente es funcional pero no comparte el rediseño institucional del login/chat).
- Dashboard de analíticas de uso (preguntas más frecuentes, tasa de abstención, satisfacción).
- Historial de conversaciones múltiples por estudiante en la UI (el backend ya modela conversaciones; la UI actual solo expone la conversación activa).
- Caché de respuestas para preguntas repetidas, como optimización de costo de API.
- Despliegue en un entorno de producción real (más allá de Docker Compose local — ver [ADR-0007](docs/adr/0007-local-docker-compose-deployment.md)).
- Integración de CI/CD (lint + pruebas automáticas en cada push/PR).
- Autenticación institucional vía OAuth/SSO real en lugar de credenciales propias.
- Mejoras al pipeline RAG: *re-ranking* de resultados, chunking semántico en vez de tamaño fijo, y ejecución completa de la evaluación RAGAS con métricas reales.
- Ampliar la cobertura de pruebas automatizadas del frontend más allá de la prueba de regresión actual.

## Pruebas

**Backend**: las pruebas unitarias no requieren infraestructura, pero las de integración y end-to-end sí necesitan un PostgreSQL propio en el puerto `5433` (separado de la base de datos de desarrollo en `5432`, para poder limpiar tablas entre pruebas sin afectar tus datos locales):

```powershell
docker run -d --name uvg-rag-test-postgres `
  -e POSTGRES_USER=rag_app `
  -e POSTGRES_PASSWORD=devpassword `
  -e POSTGRES_DB=asistente_rag `
  -p 5433:5432 `
  postgres:16-alpine

cd backend
.venv\Scripts\activate
pytest                        # las 54 pruebas: unitarias + integración + e2e
pytest tests/unit -v          # solo unitarias (no requieren infraestructura)
```

**Frontend**:

```powershell
cd frontend
npm run build   # tsc -b && vite build
npm run lint     # ESLint
npm run test     # Vitest
```

## Licencia

Este proyecto se distribuye bajo la licencia MIT — ver [LICENSE](LICENSE).
