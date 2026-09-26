# ADR-0017: Memoria conversacional humana y voz de asesor (Fase 10)

**Estado:** Aceptado — extiende [ADR-0015](0015-retrieval-intelligence-layer.md) y [ADR-0016](0016-conversation-guide.md); no modifica [ADR-0005](0005-chain-of-verification-strategy.md) (una llamada por consulta; los turnos de orientación no llaman al modelo).

**Fecha:** 2026-09-26

## Contexto

Tras la Fase 9.2 el asistente resolvía referencias y acompañaba, pero una lectura de conversaciones reales con Claude Haiku 4.5 mostró que aún se sentía como un sistema: repetía lo recién dicho, no entendía «¿quién **la** da?», «esa oficina», «esa beca de antes» ni «volviendo a las elecciones…», perdía la comparación en curso, respondía «estoy perdido» con «No encontré normativa», ofrecía un tema sin respaldo («seguro estudiantil») en su lista de capacidades, abría las respuestas de elección con «La normativa no establece…» y construía ejemplos con cifras inventadas. Un banco reservado escrito antes de tocar el código dio 0.786 en sus turnos de Fase 10.

## Decisión

Sin capas nuevas: se amplían los componentes existentes.

1. **Memoria de corto plazo** en `ConversationState` (derivada, como antes): última pregunta del estudiante, entidades recientes y comparación en curso. Permite:
   - pronombres átonos de tercera persona («¿quién la da?») y arrastre del objeto de la pregunta anterior («autorización»), solo sustantivos;
   - referencias por categoría («esa oficina», «ese consejo de antes», «esa beca de antes») resueltas contra la última respuesta o las entidades recientes, aunque haya cambiado el tema;
   - comparaciones: cada entidad se busca por separado (subconsultas) y la comparación sigue en juego para «¿cuál me conviene?»;
   - regreso explícito («volviendo a las elecciones, …»): el resto se interpreta dentro de ese tema;
   - un demostrativo («esa») elige una opción nombrada; un pronombre átono («¿quién lo decide?») habla del asunto; una opción cuenta solo si la respuesta la nombra completa.
2. **Orientación sin modelo** para «estoy perdido», «no sé qué preguntar», «necesito ayuda con algo»: menú de temas que el corpus realmente cubre (verificado con una búsqueda local), cada uno con una pregunta de ejemplo que se puede usar tal cual. «No entiendo» con tema activo vuelve a explicar lo mismo con palabras sencillas (estilo `SIMPLER`).
3. **Perfil de tema** (cacheado por versión del corpus): aspectos que la normativa trata, documento que lo regula e instancia que más menciona. Alimenta abstenciones «premium» (qué no está, qué sí describe ese documento, con quién confirmarlo, qué preguntar después) y distingue los temas que solo aparecen de paso (cambio de carrera).
4. **Voz de asesor**: el prompt pide empezar por lo que aplica, resumir primero, no repetir lo dicho (se envía un extracto de la respuesta anterior marcado como «no es fuente»), no inventar ejemplos numéricos ni oficinas; directivas nuevas para comparación (tabla + «En resumen»), ranking, recomendación y explicación sencilla. En preguntas de elección, una primera frase negativa se mueve al final de forma determinista.
5. **Textos locales fieles al corpus**: saludo, capacidades, fuera de dominio y ruido listan solo temas cubiertos.
6. **Evaluación**: configuración `conversational` en el benchmark de recuperación (el camino desplegado) y cinco invariantes nuevos en el simulador.

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| Enviar el historial completo al modelo | Riesgo de fundamentarse en respuestas propias y más tokens por turno; basta un extracto de la última respuesta marcado como «no es fuente» |
| Clasificar la intención del estudiante con el modelo | Una llamada más por turno (ADR-0005) y no reproducible |
| Reescribir la respuesta con una segunda llamada para quitar negativas y repeticiones | Duplica costo; la reordenación determinista cubre el caso frecuente sin tocar el contenido |
| Ofrecer siempre la misma lista de capacidades | Prometía un tema sin respaldo documental |

## Consecuencias

**Positivas:** turnos de Fase 10 del banco de desarrollo 0.61 → 1.00; banco reservado 0.800 → 0.920 (sus turnos de Fase 10, 0.786 → 1.000); simulador 1.000 en 14 invariantes (8 722 turnos, tres semillas); recuperación del camino desplegado: recall del contexto 0.913 → 0.924 sin pérdida de hit@1; cero llamadas adicionales al modelo.

**Negativas:** más léxico de dominio que mantener (categorías, necesidad económica, pedidos de ayuda); el hilo (pregunta y extracto de la respuesta anterior) añade unos 150 tokens a cada seguimiento; la reordenación de negativas es una heurística limitada a preguntas de elección.
