# ADR-0008: Alcance mínimo del panel administrativo

**Estado:** Aceptado

**Fecha:** 2026-09-02

## Contexto

El documento del asesor no menciona ninguna interfaz para gestionar documentos: implícitamente asume que el corpus se procesa de forma manual/offline. Sin embargo, como parte de demostrar mantenibilidad y extensibilidad de la arquitectura, el equipo decidió incluir un módulo administrativo, con la condición explícita de mantenerlo fuera del alcance de evaluación central de la tesis (que es el pipeline RAG y su desempeño medido con RAGAS).

## Decisión

Se implementa un panel administrativo con alcance deliberadamente acotado a cinco capacidades: subir un documento PDF, ver el listado de documentos indexados, eliminar o reemplazar un documento, disparar manualmente la reindexación, y ver el estado de la última indexación (éxito/error, fecha, logs). No se implementa un gestor documental completo (versionado de documentos, control de permisos granular, edición de metadatos, búsqueda avanzada).

## Alternativas consideradas

| Alternativa | Ventajas | Desventajas | Por qué se descartó |
|---|---|---|---|
| Sin panel administrativo; ingesta solo por script/CLI | Cero tiempo de frontend/backend adicional | No demuestra extensibilidad de la arquitectura hacia un segundo tipo de usuario (admin) ni el uso del rol `admin` en el módulo de autenticación | El equipo priorizó mostrar el patrón de autorización por rol como parte de la arquitectura, con costo de implementación acotado |
| CMS documental completo (versionado, metadatos enriquecidos, permisos granulares) | Más "empresarial" en apariencia | Esfuerzo de implementación desproporcionado frente al tiempo disponible (~21 horas totales) y frente al objetivo real de evaluación de la tesis, que es el pipeline RAG, no la gestión documental | Contradice la restricción de tiempo del proyecto; el valor añadido para la defensa de tesis es marginal frente al costo |
| Panel administrativo mínimo (elegido) | Demuestra el patrón de autorización por rol y la extensibilidad de la arquitectura (nuevo caso de uso, nuevo router, mismo `AuthPort`) sin comprometer el tiempo destinado al pipeline RAG, que es el criterio de evaluación central | Funcionalidad limitada; no apto para operación real sostenida por UVG sin ampliarlo | — |

## Consecuencias

**Positivas:**
- Demuestra en código real (no solo en documentación) que la arquitectura soporta más de un tipo de usuario y más de un caso de uso sin romper el diseño hexagonal.

**Negativas / trade-offs aceptados:**
- Es la funcionalidad con **prioridad más baja** en el backlog (ver `07-backlog.md`): si el tiempo se agota, queda diseñada (puertos, casos de uso, ADR) pero no completamente implementada, y así se documentará honestamente en el informe final de tesis.

## Cómo se ajusta a las restricciones del proyecto

Esta decisión protege explícitamente el tiempo disponible para el pipeline RAG (que es lo que el asesor pidió evaluar) frente a una funcionalidad que el equipo añadió por iniciativa propia para mostrar buenas prácticas de arquitectura. Si hay que sacrificar algo por el plazo de 3 semanas, este ADR dice explícitamente que debe ser el panel administrativo, no el pipeline RAG ni su evaluación.
