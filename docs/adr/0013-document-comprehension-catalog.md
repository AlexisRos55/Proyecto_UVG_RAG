# ADR-0013: Comprensión documental mediante un catálogo del corpus, sin generación

**Estado:** Aceptado

**Fecha:** 2026-09-24

## Contexto

Los estudiantes no solo preguntan datos contenidos en un fragmento («¿cuál es el promedio mínimo?»). También preguntan por los documentos como tales: «¿de qué trata este reglamento?», «¿cuáles son sus capítulos?», «¿dónde habla de becas?», «¿qué documento debo consultar?», «¿qué documentos están relacionados?». Con recuperación por similitud y generación, el modelo solo ve diez fragmentos sueltos y tendría que adivinar la estructura del documento: la respuesta sería cara, incompleta y no verificable.

## Decisión

Se incorpora un **catálogo del corpus** (`CorpusCatalogPort`) que deriva, desde los fragmentos indexados, el índice de cada documento: título declarado, código y versión, capítulos con sus artículos y páginas, resumen extractivo (el Artículo 1 declara el objeto del reglamento en sus propias palabras) y términos distintivos. Cinco intenciones nuevas (panorama, estructura, localización de un tema, enrutamiento a documentos, documentos relacionados) se resuelven con un servicio de dominio puro, `DocumentNavigator`, que compone respuestas deterministas y citadas **sin llamar al modelo**.

El índice se **deriva** y no se almacena: siempre describe exactamente lo indexado y no necesita tabla ni migración.

## Alternativas consideradas

| Alternativa | Ventajas | Desventajas | Por qué se descartó |
|---|---|---|---|
| Responder con el pipeline RAG normal | Sin código nuevo | El modelo no ve la estructura completa; cuesta una llamada; puede inventar capítulos | Inexacto y caro para un dato que el sistema ya conoce |
| Resumen generado por LLM al indexar | Prosa más elaborada | Llamada por documento, no reproducible, resumen no verificable | Se prefirió el resumen extractivo: exacto y citable |
| Tabla `document_outlines` en PostgreSQL | Consulta directa | Segunda fuente de verdad a sincronizar con ChromaDB | La derivación es instantánea para el corpus actual |

## Consecuencias

**Positivas:** respuestas exactas sobre estructura, con artículo y página; cero tokens por este tipo de consulta; las consultas de una sola palabra («becas») reciben un mapa del tema con subtemas reales del corpus en lugar de una petición genérica de detalle.

**Negativas:** la calidad depende de que el documento tenga estructura reconocible (en folletos sin articulado el panorama se apoya en términos distintivos y en la primera sección); la clasificación de estas intenciones es por reglas y puede no reconocer formulaciones muy inusuales (se degradan a consulta fundamentada, no a error).

## Cómo se ajusta a las restricciones del proyecto

Reduce el consumo de tokens (NFR-02) y no añade dependencias. Mantiene la frontera establecida por el catálogo local: las respuestas locales siguen sin fuentes; las de navegación sí las llevan, porque describen el corpus.
