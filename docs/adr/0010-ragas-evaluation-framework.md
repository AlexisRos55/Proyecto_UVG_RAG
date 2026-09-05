# ADR-0010: RAGAS como framework de evaluación

**Estado:** Aceptado

**Fecha:** 2026-09-02

## Contexto

El asesor exige validar el sistema empíricamente contra el modelo de atención manual, midiendo la tríada RAG (fidelidad, relevancia de contexto, relevancia de respuesta) más latencia. RAGAS es el framework explícitamente mencionado en el documento del asesor para este propósito.

## Decisión

Se usa RAGAS como framework de evaluación, ejecutado como un script independiente (`scripts/evaluate.py`, a implementarse en la fase de implementación) que consume un conjunto de preguntas de referencia y produce un reporte con las cuatro métricas exigidas.

## Alternativas consideradas

| Alternativa | Ventajas | Desventajas | Por qué se descartó |
|---|---|---|---|
| Evaluación manual (revisión humana de respuestas) | No requiere infraestructura de evaluación adicional | No es reproducible, no es objetiva, no genera métricas comparables a través de corridas, y no es lo que pidió el asesor | Incumple el requisito explícito del asesor |
| Otro framework de evaluación de RAG (p. ej. TruLens, DeepEval) | Podrían ofrecer métricas similares | El asesor especificó RAGAS explícitamente; cambiarlo sin justificación alteraría la metodología de validación acordada | El documento del asesor nombra RAGAS de forma explícita, no es una decisión de arquitectura abierta |
| RAGAS (elegida) | Es el framework pedido por el asesor; mide exactamente las cuatro métricas requeridas (fidelidad, relevancia de contexto, relevancia de respuesta, latencia) | Requiere un conjunto de preguntas de referencia ("golden dataset") que aún no existe y debe construirse como parte del trabajo (ver `07-backlog.md`, EPIC-7) | — |

## Consecuencias

**Positivas:**
- Cumple literalmente el requisito de validación del asesor.
- El script de evaluación es independiente del backend en ejecución: puede correr contra los mismos casos de uso de aplicación (`AnswerStudentQueryUseCase`) usando los adaptadores reales, sin necesidad de exponer un endpoint HTTP dedicado a la evaluación.

**Negativas / trade-offs aceptados:**
- El "golden dataset" de referencia y la línea base de atención manual no existen todavía; deben construirse con recursos y tiempo limitados, lo que probablemente resulte en un conjunto de evaluación pequeño (ver `09-risk-register.md`, R-06).

## Cómo se ajusta a las restricciones del proyecto

Es un requisito no negociable del asesor y por tanto no se sustituye. La única decisión de arquitectura real aquí es *cómo* se ejecuta (script independiente reutilizando los casos de uso de aplicación, evitando duplicar lógica del pipeline RAG solo para la evaluación) y *cuándo* se construye el dataset de referencia — priorizado en el roadmap después de que el flujo end-to-end esté funcional (ver `08-roadmap.md`).

## Addendum (fase de implementación, 2026-09-04): pin de versión por bug de upstream

La versión más reciente de `ragas` (0.4.3) tiene un import roto (`from langchain_community.chat_models.vertexai import ChatVertexAI`) que falla con las versiones de `langchain-community` >=0.4.1, porque ese módulo fue removido/reubicado en el ecosistema de LangChain 1.x. Se fijó `ragas==0.2.15` junto con `langchain-community>=0.4.0,<0.4.1` (la última combinación verificada donde el módulo aún existe y es compatible con `langchain-core` 1.x), documentado en `backend/pyproject.toml`. `scripts/evaluate.py` usa `langchain-anthropic` y `langchain-huggingface` únicamente como adaptadores internos que `ragas` exige para actuar de juez LLM y calcular embeddings — esto no contradice [ADR-0002](0002-no-langchain-direct-anthropic-sdk.md), que prohíbe LangChain en el pipeline de producción, no en herramientas de evaluación offline que ya dependen de LangChain internamente por decisión del propio `ragas`.
