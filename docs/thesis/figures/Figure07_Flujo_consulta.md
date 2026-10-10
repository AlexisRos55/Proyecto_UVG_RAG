# Figura 7. Flujo de atención de una consulta

| Campo | Valor |
|---|---|
| Número | Figura 7 |
| Nombre | Flujo de atención de una consulta |
| Tipo | Diagrama de flujo (Mermaid) |
| Fuente | [`../diagrams/flow.mmd`](../diagrams/flow.mmd) |
| Archivo para el documento | `../diagrams/flow.png` |
| Ubicación | Anexo D (tras el intercambio); se cita en VIII.C |
| Orientación | Vertical, página completa (proporción casi cuadrada) |

## Objetivo

Es el diagrama de flujo que solicita el protocolo. Muestra el recorrido real de un mensaje desde que el usuario lo escribe hasta que recibe la respuesta, con todas las salidas posibles: rechazo por sesión inválida, respuesta local sin el modelo, las dos abstenciones, el fallo del proveedor y la respuesta fundamentada con citas. Respalda el objetivo específico 2 y la Fase III.

> **Depende de las decisiones D2 y D3** del [índice](../figures_index.md#4-discrepancias-entre-el-protocolo-y-la-implementación). El paso 3 representa la recuperación híbrida desplegada, no la búsqueda densa con Top-K = 10 y umbral 0.35 que describe hoy VIII.B.4.

## Qué debe mostrar

Siete pasos numerados y cuatro decisiones, tal como los ejecuta `AnswerStudentQueryUseCase`:

| Paso | Contenido | Componente |
|---|---|---|
| 1 | Envío: `POST /chat` con Bearer JWT | Frontend, router `/chat` |
| Decisión | ¿Sesión válida? No → 401 | `get_current_user` |
| 2 | Registro del mensaje, saneamiento, intención, política, comprensión del turno | MessageSanitizer, RuleBasedIntentClassifier, ResponsePolicy, ConversationTracker |
| Decisión | ¿Se resuelve sin buscar? Sí → respuesta sin el modelo | guía conversacional, habilidades locales, catálogo |
| 3 | Recuperación híbrida: análisis, embedding, búsqueda densa y BM25 en paralelo, RRF + reordenamiento, admisión, ensamblado | QueryAnalyzer, KnowledgeRetriever, EvidenceReranker, ContextAssembler |
| Decisión | ¿Hay evidencia? No → abstención «sin normativa» sin llamar al modelo | |
| 4 | Generación y verificación en una llamada con salida estructurada | AnswerPlanner, SingleCallVerificationAdapter, AnthropicLLMAdapter |
| Decisión | ¿Fundamentada y con cobertura? No → abstención «información insuficiente» | |
| 5 | Citación (documento, sección, páginas) y matiz por confianza | `_cited_passages`, `_resolve_sources`, VoiceGuard |
| 6 | Persistencia y tiempos | ConversationRepository, registro de latencias |
| 7 | Presentación en Markdown con bloque «Fuentes» | Frontend |

Convención de color: verde oscuro para la única llamada al modelo, gris para lo resuelto sin el modelo, ámbar para abstenciones y errores, azul para decisiones.

**Sobre el «reranking».** El sistema no usa un modelo de reordenamiento (*cross-encoder*): reordena con Reciprocal Rank Fusion más señales estructurales (artículo citado, sección, entidad en foco). El diagrama lo nombra así para no atribuirle una técnica que no implementa.

## Cómo generarla

PNG exportado (4452 × 4608 px) en una página propia, al ancho del texto.

## Pie de figura

> Figura 7. Flujo de atención de una consulta. Elaboración propia con base en el repositorio del proyecto.

## Referencia dentro del texto

Insertada en el protocolo (VIII.C, después del párrafo sobre el prompt de sistema):

> La Figura 7 (Anexo D) representa el flujo completo de una consulta. Las decisiones previas a la recuperación son deterministas y no consumen tokens; solo las consultas institucionales con evidencia suficiente llegan a la única llamada al modelo, y el sistema dispone de dos puntos de abstención: uno antes de esa llamada, cuando la recuperación no encuentra evidencia, y otro después, cuando la verificación determina que los fragmentos no respaldan la respuesta.
