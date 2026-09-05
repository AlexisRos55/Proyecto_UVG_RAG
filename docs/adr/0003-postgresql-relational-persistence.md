# ADR-0003: Usar PostgreSQL para persistencia relacional

**Estado:** Aceptado

**Fecha:** 2026-09-02

## Contexto

El stack original especificado por el asesor solo contempla ChromaDB, que almacena y recupera vectores — no está diseñado para modelar usuarios, sesiones, historial de conversación ni metadatos de documentos administrados. Al incorporar autenticación institucional (ver [ADR-0004](0004-institutional-authentication.md)) y un panel administrativo (ver [ADR-0008](0008-admin-panel-scope.md)), el sistema necesita un lugar donde persistir datos relacionales con integridad referencial (un usuario tiene muchas conversaciones, un documento tiene un estado de indexación, etc.).

## Decisión

Se añade PostgreSQL como servicio independiente en Docker Compose, gestionado desde el backend mediante SQLAlchemy 2.x y migraciones con Alembic, detrás de los puertos `UserRepositoryPort`, `ConversationRepositoryPort` y `DocumentRepositoryPort`.

## Alternativas consideradas

| Alternativa | Ventajas | Desventajas | Por qué se descartó |
|---|---|---|---|
| SQLite embebido | Cero contenedores adicionales, cero configuración de red, arranque instantáneo | No soporta bien escritura concurrente real; no es el estándar esperado en un sistema descrito como "empresarial"; migrar después a Postgres implicaría reescribir parte del acceso a datos | El proyecto se define explícitamente como un sistema de nivel empresarial; un componente central de persistencia debe reflejar eso, y el costo de un contenedor adicional en Docker Compose es bajo |
| Sin persistencia relacional (stateless) | Cero complejidad adicional | Elimina la posibilidad de autenticación real, historial de conversación y panel administrativo — funcionalidades ya decididas como parte de la arquitectura | Incompatible con las decisiones de autenticación y administración ya tomadas |
| MongoDB u otra base documental | Esquema flexible, natural para documentos JSON | Los datos del dominio (usuarios, conversaciones, documentos) tienen relaciones claras y consistentes (uno-a-muchos); un modelo relacional es más adecuado y más defendible académicamente para este tipo de dato | No aporta ventaja real sobre PostgreSQL para este caso de uso, y añade un paradigma de datos distinto sin necesidad |

## Consecuencias

**Positivas:**
- Integridad referencial real (una conversación no puede existir sin un usuario válido).
- Alembic da trazabilidad completa del esquema a lo largo del proyecto — relevante para defender decisiones de modelado de datos ante el tribunal.
- PostgreSQL es un componente estándar en arquitecturas empresariales modernas, coherente con el objetivo declarado del proyecto.

**Negativas / trade-offs aceptados:**
- Un contenedor adicional en `docker-compose.yml`, con su propio healthcheck y volumen persistente.
- Tiempo de implementación adicional (modelos SQLAlchemy, migraciones, repositorios) que compite directamente con las ~21 horas disponibles — mitigado priorizando en el backlog solo las tablas estrictamente necesarias para el MVP (usuarios y conversaciones antes que metadatos administrativos completos).

## Cómo se ajusta a las restricciones del proyecto

El presupuesto de tiempo es la restricción más severa del proyecto. Por eso el modelo de datos se mantiene deliberadamente mínimo (ver `07-backlog.md`): solo las tablas necesarias para autenticación y el flujo de chat quedan en el camino crítico del MVP; las tablas de soporte al panel administrativo se implementan solo si el tiempo lo permite, sin bloquear el resto del sistema.
