# ADR-0015: Capa de inteligencia de recuperación (estado conversacional determinista)

**Estado:** Aceptado — extiende [ADR-0012](0012-structure-aware-ingestion-and-hybrid-retrieval.md) y [ADR-0013](0013-document-comprehension-catalog.md); no modifica [ADR-0005](0005-chain-of-verification-strategy.md) (sigue siendo una llamada por consulta).

**Fecha:** 2026-09-24

## Contexto

La recuperación busca lo que se le pide. En una conversación, lo que el estudiante escribe rara vez es lo que hay que buscar: «¿Cuánto cubre esa?», «¿Y cuáles son los requisitos?», «Continuemos». El mecanismo anterior anteponía la pregunta anterior cuando una expresión regular detectaba una anáfora; medido con un banco de conversaciones sobre el corpus oficial (`scripts/evaluate_conversations.py`), resolvía **0 %** de las referencias y superaba el **28 %** de los turnos. Además: la pregunta actual se leía como «la anterior» por una lista de historial compartida; «¿Pierdo la beca si bajo mi promedio?» se declinaba como dato personal; «¿Cómo funcionan las elecciones?» se respondía como pregunta sobre el asistente.

## Decisión

Se añade una capa previa a la búsqueda, determinista y sin llamadas al modelo:

1. **Estado conversacional** (`ConversationState`): tema, entidad, aspecto, documentos y artículo activos, aspectos ya tratados. Se **deriva** reproduciendo los mensajes persistidos (`ConversationTracker.replay`); los turnos sociales no lo alteran.
2. **Resolución de referencias e interpretación del turno** (`TurnInterpretation`): nuevo, seguimiento, profundizar, retomar o artículo contiguo. Distingue tema (lo que cambia la conversación) de aspecto (lo que se pregunta del tema), reconoce anáforas, pronombres átonos y enclíticos, y decide si un sustantivo nuevo pertenece al tema en curso por **coocurrencia en el corpus**.
3. **Reescritura y expansión**: consulta interna = palabras del estudiante + foco; los términos del aspecto van como expansión de peso reducido. Los panoramas («háblame de las becas») se expanden con las entidades que el corpus realmente nombra.
4. **Comprensión documental ampliada**: entidades con nombre (programas, instancias, campus, carreras, eventos, autoridades), artículo que define cada entidad y ficha del documento (membrete conservado una vez).
5. **Recuperación anclada y reordenamiento**: la evidencia fuerte de un seguimiento debe mencionar su foco; el reordenamiento premia la entidad en foco, el aspecto en el título del artículo (solo si es del tema), los artículos que definen entidades y el calendario para preguntas de fecha.
6. **Contexto adaptativo y planificación de la respuesta**: presupuesto ×1.5 para panoramas y ×0.7 para un dato de una entidad; la forma se decide con la evidencia (por programa, panorama, consecuencias).
7. **Prevención de alucinaciones**: advertencia en las tablas que perdieron sus marcas gráficas, reglas de fundamentación más estrictas, guardia determinista de la voz y degradación elegante ante fallos del proveedor.

Al modelo le llega la pregunta **literal** del estudiante acompañada de una glosa de la interpretación («Pregunta de seguimiento: se refiere a la Beca Despega; pregunta por cuánto cubre»).

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| Reescritura de la consulta con el LLM (una llamada adicional) | Duplica llamadas (NFR-02, ADR-0005), añade latencia, no es reproducible y no se puede probar exhaustivamente |
| Enviar el historial completo al modelo | El modelo podría fundamentarse en sus propias respuestas previas (ADR de la capa de agencia); más tokens en cada turno |
| Persistir el estado en una tabla | Segunda fuente de verdad; derivarlo del historial es instantáneo y siempre coherente |
| Clasificador de temas entrenado | Sin datos etiquetados suficientes; el léxico explícito es auditable y cubre el dominio acotado |

## Consecuencias

**Positivas:** banco de desarrollo 28 % → 100 % de turnos; conjunto reservado 62.5 % en su primera medición (87.5 % tras correcciones de causa general); recuperación de una sola pregunta hit@1 0.457 → 0.565 sin regresiones; cero llamadas adicionales.

**Negativas:** el léxico de temas y aspectos es conocimiento del dominio que hay que mantener si el corpus incorpora temas nuevos (los temas no reconocidos siguen funcionando, con menor precisión); las reglas se ajustaron con un banco pequeño etiquetado por el equipo.

## Cómo se ajusta a las restricciones del proyecto

No añade llamadas al modelo, dependencias ni tablas. Todo componente es un servicio de dominio puro o una ampliación de un puerto existente (`CorpusCatalogPort.entities/vocabulary/co_occur`), inyectado desde la raíz de composición. Sin catálogo, o con `conversation_intelligence=False`, el caso de uso se comporta exactamente como antes.
