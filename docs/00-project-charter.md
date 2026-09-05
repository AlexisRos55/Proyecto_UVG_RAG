# Project Charter — Asistente Virtual Institucional (RAG) UVG Altiplano

| Campo | Valor |
|---|---|
| Nombre del proyecto | Asistente Virtual Inteligente basado en Arquitectura RAG para consultas institucionales |
| Institución | Universidad del Valle de Guatemala (UVG), Campus Altiplano |
| Tipo | Trabajo de Graduación — Ingeniería en Tecnología de Sistemas Informáticos |
| Asesor | Fuente oficial de requisitos funcionales (documento `Descripción Técnica: Asistente Virtual RAG - UVG Altiplano`) |
| Equipo de desarrollo | 1 desarrollador (Natán Saquic), con asistencia de herramientas de IA (Claude, ChatGPT) como apoyo de ingeniería — no como reemplazo de autoría ni de criterio técnico |
| Fecha de inicio de esta fase | 2026-09-02 |
| Fecha de entrega objetivo | Última semana de septiembre de 2026 (~3 semanas de desarrollo disponibles) |
| Dedicación estimada | ~1 hora/día, equipo de una persona (~15–21 horas efectivas totales) |

## 1. Propósito del proyecto

Construir un prototipo funcional de asistente conversacional que resuelva consultas estudiantiles sobre normativas internas, reglamentos académicos, beneficios estudiantiles y seguros institucionales de UVG Altiplano, utilizando una arquitectura de Generación Aumentada por Recuperación (RAG) que evite alucinaciones y base cada respuesta exclusivamente en documentos oficiales.

Este proyecto es el artefacto principal de un trabajo de graduación. Por lo tanto, además de funcionar, debe estar diseñado y documentado de forma que cada decisión técnica sea defendible ante un tribunal académico.

## 2. Justificación de negocio

El modelo actual de atención es manual: el personal administrativo resuelve consultas repetitivas sobre normativa institucional, generando cuellos de botella y latencia en la atención al estudiante. Automatizar estas consultas libera tiempo del personal para tareas administrativas de mayor valor, sin sacrificar precisión, siempre que el sistema declare explícitamente cuándo no tiene información suficiente en vez de inventar respuestas.

## 3. Objetivos del proyecto

1. Implementar el pipeline RAG completo (ingesta, chunking, embeddings, recuperación semántica, generación verificada) exactamente como lo especifica el asesor en cuanto a comportamiento funcional.
2. Diseñar la solución bajo Arquitectura Hexagonal y Clean Architecture, con principios SOLID aplicados de forma verificable (no solo declarada), de modo que el diseño de software sea defendible por sí mismo, independientemente del resultado de precisión del modelo.
3. Evaluar empíricamente el sistema con el framework RAGAS (tríada RAG + latencia) frente al proceso de atención manual.
4. Entregar un sistema desplegable de forma reproducible mediante Docker Compose, dentro del alcance realista de una demo local para la defensa de tesis.

## 4. Alcance

### Dentro de alcance (fuente: documento del asesor + decisiones de arquitectura registradas en los ADR)

- Ingesta y procesamiento de documentos oficiales en PDF.
- Recuperación semántica sobre ChromaDB.
- Generación de respuestas mediante el SDK de Anthropic (Claude), con verificación de fundamentación (Chain-of-Verification) y negativa explícita ante falta de contexto.
- Autenticación institucional simple (correo `@uvg.edu.gt`).
- Persistencia relacional (PostgreSQL) de usuarios, sesiones de conversación y retroalimentación.
- Panel administrativo ligero para gestión documental (fuera del alcance de evaluación de tesis, ver [ADR-0008](adr/0008-admin-panel-scope.md)).
- Evaluación con RAGAS contra un conjunto de referencia.
- Despliegue local mediante Docker Compose.

### Fuera de alcance (explícitamente, para esta versión)

- Integración SSO real con sistemas de identidad de UVG.
- Despliegue en infraestructura institucional o en la nube.
- Pipeline de verificación multi-llamada (queda diseñado como extensión futura, no implementado — ver [ADR-0005](adr/0005-chain-of-verification-strategy.md)).
- Recuperación híbrida (BM25 + vectorial), reranking, y chunking semántico por estructura legal — quedan documentados como mejoras futuras (ver `06-high-level-architecture.md`, sección "Evolución futura"), no como parte del MVP.
- Soporte multilenguaje (el sistema opera en español).

Ningún elemento de "fuera de alcance" contradice el documento del asesor: son mejoras de arquitectura/infraestructura que el equipo decidió no implementar ahora por restricción de tiempo, no recortes al alcance funcional definido por el asesor.

## 5. Restricciones del proyecto

- **Tiempo:** ~3 semanas, ~1 hora/día, un solo desarrollador. Es la restricción dominante del proyecto y condiciona todas las demás decisiones de priorización (ver `08-roadmap.md`).
- **Presupuesto:** financiado personalmente, sin presupuesto institucional para consumo de API. El diseño debe minimizar el uso de tokens (ver [ADR-0005](adr/0005-chain-of-verification-strategy.md) y [ADR-0006](adr/0006-configurable-llm-model-selection.md)).
- **Stack tecnológico:** fijado por decisión de arquitectura (ver `05-technology-decisions.md`), no sujeto a debate salvo hallazgo crítico durante la implementación.
- **Alcance funcional:** fijado por el documento del asesor, no modificable.

## 6. Criterios de éxito

1. El sistema responde consultas dentro del dominio documental con fidelidad medible por RAGAS, y se abstiene explícitamente cuando no hay contexto suficiente.
2. La arquitectura hexagonal es verificable en el código: los casos de uso no dependen de detalles de infraestructura (ChromaDB, Anthropic SDK, PostgreSQL) sino de puertos abstractos.
3. El sistema se levanta de forma reproducible con `docker compose up`.
4. La documentación de arquitectura (este conjunto de documentos) sustenta cada decisión con alternativas consideradas y justificación técnica, apta para defensa de tesis.
5. Existe al menos una corrida de evaluación RAGAS documentada, comparando el sistema contra una referencia de atención manual (aunque sea con un conjunto de referencia reducido, dado el tiempo disponible).

## 7. Supuestos

- El asesor acepta que el stack técnico específico (LangChain → SDK directo de Anthropic, adición de PostgreSQL, autenticación propia) es una decisión de arquitectura del equipo que no altera el comportamiento funcional exigido.
- El corpus documental inicial será provisto por el equipo (documentos públicos o de ejemplo de UVG Altiplano) dado que el asesor no entregó el corpus junto con la especificación funcional.
- No se requiere disponibilidad 24/7 ni tolerancia a fallos de producción: es un prototipo académico evaluado en un entorno controlado.

## 8. Aprobación

Este charter representa el entendimiento actual del alcance y las restricciones. Cualquier cambio a los objetivos funcionales requiere revisión con el asesor; cambios de arquitectura/infraestructura quedan a criterio del equipo y se documentan mediante nuevos ADR.
