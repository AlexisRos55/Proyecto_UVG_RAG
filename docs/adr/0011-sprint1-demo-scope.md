# ADR-0011: Alcance de la demo del Sprint 1 (subconjunto de la arquitectura ya implementada)

**Estado:** Aceptado

**Fecha:** 2026-09-05

## Contexto

Antes de este sprint, la fase de implementación ya había construido y probado (51 pruebas: unitarias, integración contra PostgreSQL/ChromaDB reales, y e2e) el sistema completo aprobado en la arquitectura: autenticación institucional completa (registro + login + JWT + bcrypt), panel administrativo de documentos (EPIC-7), y el script de evaluación RAGAS (EPIC-6).

Para una demo de una sola sesión, mostrar todo el sistema completo distrae del objetivo real: demostrar que el pipeline RAG completo (PDF → PyMuPDF → limpieza → chunking → embeddings → ChromaDB → recuperación → verificación → Claude → respuesta con fuente) funciona de punta a punta, con una interfaz profesional. El equipo decidió acotar el **guion de la demo**, no el sistema: nada de lo ya implementado se elimina.

## Decisión

Para el sprint 1:

1. **Login de demo, no de producción.** Se siembra una única cuenta (`admin@uvg.edu.gt` / `admin123`, configurable vía `DEFAULT_ADMIN_EMAIL`/`DEFAULT_ADMIN_PASSWORD`) automáticamente al arrancar el backend (`app/infrastructure/bootstrap.py`), usando el mismo `RegisterStudentUseCase`, `AuthPort` y `UserRepositoryPort` ya existentes — no se creó un mecanismo de login paralelo. El enlace de registro se oculta en el frontend para esta demo, pero el endpoint `/auth/register` sigue activo.
2. **Sin panel administrativo en la navegación de la demo.** El código de EPIC-7 (`AdminDocumentsPage`, endpoints `/admin/documents/*`) permanece intacto y probado, pero no se enlaza desde la interfaz de la demo.
3. **Carga de documentos por convención de carpeta.** Los PDF de `backend/documents/` se indexan automáticamente al arrancar (`seed_documents_from_directory`, idempotente por nombre de archivo), reutilizando `IngestDocumentUseCase`/`DocumentIndexingPipeline` sin cambios. Es un mecanismo adicional a — no un reemplazo de — el panel administrativo y `scripts/ingest.py`.
4. **Citación de fuente sin número de página.** Se añadió `SourceReference` (value object) y `Message.source_document_names` para mostrar el documento de origen de cada respuesta (explicabilidad). El número de página queda modelado en el esquema (`page_number: int | None`) pero siempre `None`: la extracción actual (FR-01 a FR-03) concatena todo el texto antes de fragmentar, por lo que no hay límites de página por fragmento todavía. Añadirlo después es un cambio de datos, no de arquitectura ni de contrato de API.
5. **"Nueva conversación" es un reinicio visual, no un nuevo hilo persistente.** Dado que el historial de conversaciones está explícitamente fuera de alcance de este sprint, el botón limpia la vista local; el backend sigue usando `get_or_create_active_conversation` (una sola conversación activa por usuario, FR-14), sin cambios.
6. **Logging de latencia por etapa.** `AnswerStudentQueryUseCase` ahora registra pregunta recibida, tiempo de recuperación, tiempo de generación y tiempo total (Loguru), sentando la base para NFR-01 sin implementar aún el panel de métricas.

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| Construir un login "de mentira" (verificación de credenciales solo en el frontend, sin backend real) | Contradice "la arquitectura de autenticación debe quedar compatible con la implementación futura": sería código desechable, no una base real. La cuenta sembrada usa el `AuthPort`/JWT real. |
| Eliminar temporalmente el panel administrativo y el registro del código para "simplificar" | Contradice la instrucción explícita del equipo de no remover módulos ya implementados; además destruiría trabajo ya probado sin necesidad. |
| Implementar número de página ahora | Requeriría rediseñar la extracción para trackear límites de página por fragmento — cambio real de pipeline, no justificado por una demo cuando el requisito lo marca como opcional. |

## Consecuencias

**Positivas:** la demo se puede preparar y ensayar sin tocar el sistema ya probado; todo lo construido en sprints anteriores sigue disponible para sprints futuros sin re-implementar nada.

**Negativas / trade-offs aceptados:** el botón "Nueva conversación" no crea un hilo persistente nuevo (documentado explícitamente arriba, para no presentarlo como más de lo que es); la citación de fuente no incluye página todavía.

## Cómo se ajusta a las restricciones del proyecto

No modifica ninguna decisión de arquitectura, ADR o principio ya aprobado (Hexagonal, Clean Architecture, SOLID): cada adición de este sprint (siembra de admin, ingesta automática, citación de fuente) se implementó como una extensión aditiva sobre los puertos existentes, nunca como un cambio a su contrato.
