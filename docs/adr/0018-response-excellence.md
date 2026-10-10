# ADR-0018: Excelencia en la respuesta — misma evidencia para reformular, segundo intento local y quien escribe

**Estado:** Aceptado — extiende [ADR-0017](0017-human-conversation-memory-and-voice.md); no modifica [ADR-0005](0005-chain-of-verification-strategy.md) (una llamada al modelo por consulta; los reintentos de búsqueda son locales).

**Fecha:** 2026-10-02

## Contexto

La Fase 10 hizo que el asistente entendiera la conversación. Leer 500 turnos reales contra Claude Haiku 4.5 mostró que la calidad de **cada respuesta** todavía fallaba de formas que un estudiante nota de inmediato:
- «No entendí» se volvía a explicar con otra búsqueda, que a veces traía otro tema.
- «Bcas», «quiero saver», «¿la segunda?», «resúmelo» o «continúa» no se entendían.
- Un padre de familia recibía una abstención.
- La pregunta por la próxima fecha de pago se respondía sin saber qué día es hoy.
- Una fila del calendario había perdido su fecha al extraerse.
- Las respuestas repetían oraciones y cerraban con «confírmalo en el campus».
- Las preguntas cortas recibían respuestas de más de 100 palabras.

## Decisión

1. **Reformular con la misma evidencia.** «No entendí», «explícalo diferente», «resúmelo», «dame un ejemplo» y «¿por qué?» usan los fragmentos que citó la respuesta anterior (`CorpusCatalogPort.chunks_by_ids`, a partir de `source_chunk_ids`, ya persistidos). «Continúa» parte de ellos y suma lo nuevo.
2. **Segundo intento local antes de abstenerse.** Si no queda contexto útil:
   - una pregunta nueva sin tema se relee como seguimiento del tema activo;
   - un seguimiento anclado a una entidad se amplía al tema, con las palabras del aspecto en la consulta principal («quién decide» → «comité… ayudas financieras»).
   No hay llamada adicional al modelo.
3. **Comprensión de turnos reales** en el rastreador, determinista:
   - erratas del dominio (corregidas en el saneamiento, distancia de una edición contra una lista cerrada; se guarda el texto original);
   - ordinales y «la otra» sobre la última lista;
   - «ese artículo», «ese reglamento», «esa carrera»;
   - «¿y la graduación?» hereda el aspecto de la pregunta anterior;
   - fórmulas de entrada («cambiando de tema», «quiero saber») que no se buscan;
   - «continúa» distingue entre seguir explicando y retomar tras una pausa;
   - una referencia sin antecedente se aclara en lugar de buscarse.
4. **Quién escribe.** «Soy papá de…», «soy docente», «trabajo en el área administrativa»: la presentación se quita de la búsqueda y el modelo recibe cómo tratar a la persona (de usted, el estudiante en tercera persona, sin atribuir cargos). Una presentación sin pregunta recibe una pregunta de vuelta.
5. **Fecha de hoy** en preguntas de fechas («próxima», «cuándo»), en hora de Guatemala.
6. **Estilo, con reglas medibles:**
   - extensión proporcional a la pregunta;
   - el resumen no se repite en las viñetas;
   - lo común a varias opciones se dice una vez;
   - el campus se nombra solo cuando cambia la respuesta;
   - «confirmarlo en el campus» solo cuando decide algo, y no dos respuestas seguidas: el sistema quita la remisión repetida y conserva lo que falta;
   - en «resúmelo en tres puntos», exactamente tres.
7. **Un defecto de datos corregido.** El calendario tenía columnas de fecha desalineadas: la fecha suelta se empareja con la actividad más cercana (hasta 12 puntos) y la página se reconoce como calendario si tiene encabezados de mes. Solo cambia la extracción del calendario (comprobado contra los otros 15 PDF).

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| Corrector ortográfico general | Convertiría «clave» en «clase»; se corrige solo hacia palabras del dominio y con una única candidata |
| Enviar la respuesta anterior completa como fuente para reformular | El modelo se fundamentaría en sí mismo (ADR-0005); los fragmentos citados son la fuente correcta |
| Segunda llamada al modelo para reescribir el estilo | Duplica el costo; las reglas medibles más la limpieza determinista de la remisión repetida cubren lo frecuente |
| Pedir al estudiante que reformule ante cualquier pregunta sin respuesta | Ya hay un tema activo que da contexto; un asesor lo usa antes de preguntar |

## Consecuencias

**Positivas:**
- Recuperación en el camino desplegado: hit@1 0.587 → 0.652, recall@5 0.804 → 0.880, MRR 0.683 → 0.746, con menos contexto enviado (≈5 500 → 4 594 caracteres).
- Banco reservado: 0.920 → 0.960 sin ajustarlo.
- Simulador: 18 invariantes en 1.000 sobre 9 350 turnos.
- En vivo: oraciones repetidas dentro de una conversación 12 → 0–2; respuestas a preguntas puntuales 116 → 89–105 palabras.
- Cero llamadas adicionales.

**Negativas:**
- Más vocabulario de dominio que mantener: erratas, fórmulas de entrada, sinónimos y patrones de quién escribe.
- La reformulación con la misma evidencia hereda los límites de esa evidencia: si la respuesta anterior fue parcial, la reformulación también lo será.
