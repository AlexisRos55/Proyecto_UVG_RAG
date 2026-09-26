# ADR-0016: Guía conversacional determinista (anticipación, abstención útil y memoria de sesión)

**Estado:** Aceptado — extiende [ADR-0015](0015-retrieval-intelligence-layer.md); no modifica [ADR-0005](0005-chain-of-verification-strategy.md) (sigue siendo una llamada por consulta, y los turnos sociales, de pausa y de reanudación no llaman al modelo).

**Fecha:** 2026-09-25

## Contexto

La capa de ADR-0015 resolvía referencias, pero la conversación completa seguía sintiéndose como búsquedas sueltas. Un simulador de 120 conversaciones largas (2 696 turnos, `scripts/simulate_conversations.py`) midió en la línea base: el tema se olvidaba al despedirse «hasta mañana» (41 % de aciertos), los seguimientos elípticos buscaban fuera del tema (81 %), una cortesía como «Perfecto gracias» llamaba al modelo (81 %), y un tema sin respaldo documental a veces se «respondía» con evidencia de otro tema (66 %). Las abstenciones eran un «no sé» que no orientaba, se repetían idénticas y prometían oficinas que el sistema no puede nombrar; el modelo cerraba con «¿Quieres saber más…?» encima de la sugerencia del sistema.

## Decisión

1. **`conversation_guide`** (servicio de dominio puro) decide cómo acompaña el asistente:
   - *Ofrecer solo lo que se puede cumplir*: los aspectos ofrecidos («los requisitos, la cobertura o cómo se solicita») se detectan en los títulos de los artículos del documento, o del capítulo, que trata el tema; si el tema es un apartado de otro documento (el cambio de carrera dentro del reglamento de ayudas), solo cuentan los artículos recuperados. Como máximo tres.
   - *Una sola invitación*: la del sistema reemplaza el cierre interrogativo del modelo (`close_with_offer`).
   - *Abstención que orienta*: «No encontré una disposición oficial que establezca X. La normativa sí describe A, B y C… Si lo deseas, puedo ayudarte con…».
   - *No repetirse*: la segunda abstención seguida es breve, la tercera redirige a lo que el corpus sí trata, las siguientes varían y son cortas.
   - *Retomar con recapitulación*: «Claro, sigamos con las becas. Hasta ahora vimos… ¿Qué te interesa?».
2. **Memoria de sesión**: el estado se reproduce sobre hasta 120 mensajes y caduca a los 7 días; las pausas («continuemos mañana») y los saludos de regreso nombran el tema activo sin llamar al modelo.
3. **Referencias ampliadas** en el rastreador: «¿por qué?», «dame un ejemplo», «el anterior», «Artículo 20» a secas dentro de un documento activo, sustitución de carrera («¿y para Tecnología?») y «esa» tras una pregunta de ranking (el primer candidato nombrado en la respuesta).
4. **Artículo exacto**: la navegación por artículos recupera el artículo por número desde el catálogo (`CorpusCatalogPort.article_chunks`), no por similitud.
5. **Anclas sin homónimos**: el ancla de un tema usa palabras cuya raíz no colisiona con otras del corpus («póliza», «asegurado» en lugar de «seguro», que comparte raíz con «seguridad»).

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| Dejar que el modelo redacte las ofertas y abstenciones | Promete lo que la normativa no cubre, no es reproducible y cuesta una llamada en turnos que no la necesitan |
| Instrucción en el prompt para no cerrar con preguntas (sola) | Se probó: el modelo la incumple a veces; el recorte determinista del último párrafo es fiable |
| Memoria persistente en una tabla | Segunda fuente de verdad; el estado derivado del historial ya es instantáneo (ADR-0015) |
| Banco de conversaciones etiquetado a mano, más grande | No escala a miles de turnos; los invariantes sí, y el banco etiquetado se conserva para los hechos concretos |

## Consecuencias

**Positivas:** simulador 0.863 → 1.000 (tres semillas, 8 307 turnos); banco de conversaciones con los cinco casos de la Fase 9.2 0.828 → 1.000; sin regresiones en recuperación (hit@1 0.565, recall del contexto 0.891) ni en el conjunto reservado (0.875). Cero llamadas adicionales al modelo; menos llamadas en total (cortesías, pausas y reanudaciones son locales).

**Negativas:** las frases de oferta y abstención son plantillas en español que hay que mantener; el simulador sustituye el modelo por un registrador, así que la calidad de la redacción generada se verifica con corridas en vivo, no con el simulador.
