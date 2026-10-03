# Fase 9.5 y fase final — El asesor antes del modelo

**Fecha:** 2026-10-03 · **Antecedente:** [16-excelencia-en-la-respuesta.md](16-excelencia-en-la-respuesta.md) · **ADR:** ninguno nuevo; no se modificó ningún ADR.

La API de Anthropic estuvo **sin crédito durante toda la fase**. No se hizo ninguna llamada al modelo salvo dos comprobaciones mínimas del saldo, que respondieron «credit balance is too low». Por eso el objetivo fue que el software piense como un asesor universitario **antes** de llamar al modelo, para que el modelo solo tenga que redactar. Todo se validó offline: el pipeline real (recuperación híbrida, rastreador conversacional, política, ensamblado) con un registrador en lugar del modelo.

**Regla de trabajo:** un cambio se conserva solo si mejora un banco sin empeorar ninguno de los demás. Dos cambios se descartaron por esa regla (sección 4).

---

## 1. Qué se mejoró

### Comprensión: la necesidad dicha con palabras propias
| El estudiante escribe | Antes | Ahora |
|---|---|---|
| «Mis papás no pueden pagar la universidad», «soy de bajos recursos», «no tengo plata para la u» | búsqueda literal o «no logré relacionar» | becas y ayudas: panorama de opciones |
| «quiero estudiar», «quiero entrar a la universidad», «¿cómo entro a la UVG?» | búsqueda literal; «entrar a» se expandía con sinónimos de **clubes** | admisión |
| «me quiero salir de un curso» | «no logré relacionar» | retiro de cursos (se busca con «retiro de cursos», no con «salir») |
| «ya voy a terminar la carrera, ¿qué sigue?» | folletos de carreras | graduación |
| «voy a reprobar un curso» | sin evidencia (abstención) | penalizaciones por reprobación |
| «¡¡Me dieron la beca!! ¿y ahora qué hago?» | cómo solicitarla | condiciones para mantenerla, felicitando |
| «quiero volver a estudiar» | búsqueda literal | reingreso (tema propio: en este corpus «inscripción» es también la de planillas y clubes) |
| «¿y cuánto me darían?» | sin aspecto | cobertura |

### Seguimiento y memoria
- **Lo ofrecido se recuerda.** Las respuestas cierran con «Si quieres, también puedo explicarte A, B o C». Antes, «sí» o «dale» reenviaban la misma pregunta al modelo y «no» también. Ahora:
  - «sí» con varias opciones pregunta «¿Por cuál empezamos: A, B o C?», con las mismas palabras ofrecidas y sin llamar al modelo;
  - con una sola opción, la responde;
  - «no» cierra con amabilidad;
  - «la primera» elige la primera opción ofrecida.
- **La consulta ya no crece.** En una cadena de elipsis («¿y cuánto?», «¿y cuándo?»…) la consulta interna se duplicaba en cada turno. En el banco de hilos largos con el código anterior, 7 consultas superaban las 40 palabras.
- **«¿y cuánto?»** es cobertura en becas y crédito, y costo en lo demás. En el crédito se busca con «interés, plazo, mensualidades».
- **«¿Cuáles existen?»** tras abrir un tema muestra el panorama con los artículos que definen cada opción.
- **«¿Y después?», «tons?», «y entonces»** continúan la explicación. **«¿Qué más debo saber?»** busca el foco e indica al modelo qué ya se explicó, para no repetirlo.
- **Deixis documental:**
  - «¿y allí qué dice de los requisitos?» busca dentro del documento en consulta;
  - «¿qué más dice ese reglamento?» da el panorama del documento.
- **Referencias imposibles:**
  - «¿y la otra?» o «¿esa cuál era?» sin opciones dadas reciben «¿A cuál te refieres?», en lugar de una llamada al modelo;
  - si el estudiante insiste, la pregunta se reformula.
- **«¿Me lo explicas más fácil?»** reformula la última respuesta con fuentes, aunque en medio haya habido un «exacto» → «Entendido.».

### Lenguaje natural y perfiles
- **Acuses, afirmaciones y risas** se responden sin el modelo y sin mover el foco: «simón», «sip», «nel», «xd», «jeje», «👍», «🙏», «no por ahora», «cool».
- **Muletillas fuera de la búsqueda:** «mire, fíjese que…», «xfa», «pls», «please» y los emojis.
- **Fórmulas de cortesía y disculpa** ya no cambian el tema: «Disculpe la molestia, …», «Perdón que pregunte, …», «Mire, disculpe, …».
- **Presentaciones:**
  - «Soy docente. Háblame del crédito educativo» ya no pierde la pregunta;
  - «soy nuevo y no entiendo cómo funciona la u» recibe una bienvenida con admisión y calendario primero, en lugar de la explicación de cómo funciona el asistente;
  - si vuelve a pedir orientación, se le recomienda un primer paso concreto.
- **Emociones:**
  - la angustia («AYUDA URGENTE!!! me van a quitar la beca») se responde con el problema que nombró y con la indicación al modelo de reconocerla en una frase tranquila;
  - la alegría se comparte («¡Qué gusto!»);
  - quejas como «esto es una porquería» se reconocen como frustración.
- **Contar la propia situación no es pedir datos personales.** «Reprobé dos cursos y tengo beca» antes respondía «No tengo acceso a tu información personal».
- **Varias preguntas en un mensaje:** «… Y además, ¿…?» se separa; la ficha de un documento ya no se come la segunda pregunta.

### Recuperación (sin cambiar el pipeline)
- **Palabras vacías nuevas:** «voy», «quisiera», «puedes»… Al no existir en el corpus, inflaban el denominador de cobertura léxica con un idf máximo.
- **Familia morfológica para términos ausentes del corpus:** «reprobar» → «reprobados». Solo se aplica a términos que hoy no coinciden con nada, y está memoizada.
- **Las paráfrasis de un tema** se sustituyen por los términos canónicos del tema.
- **Los temas solo mencionados de paso** (graduación en el reglamento de ayudas) ya no ofrecen aspectos de otro asunto («qué cubre»). Se distinguen de los regulados sin artículo propio (crédito educativo) por la insistencia: 4,2 menciones por fragmento frente a 1,5.

### Rendimiento
- **Reproducción incremental del estado conversacional.** Antes, cada turno reinterpretaba todo el historial (coste cuadrático): era el **72%** del tiempo del caso de uso. Ahora se reanuda desde un punto de control por conversación. Se verificó contra la reproducción completa: 0 diferencias en 2.788 turnos.
- **Caché LRU de embeddings de consulta.** En los hilos sintéticos, 1.301 cálculos correspondían a 129 textos distintos.

### Mantenibilidad
- Funciones con complejidad ciclomática > 10 (ruff C901): **8 en la línea base → 7**.
- Las reglas nuevas viven como reglas con nombre del rastreador.
- Las aclaraciones son una tabla de despacho.
- `execute` delega los movimientos conversacionales locales y la oferta de cierre.

## 2. Bancos nuevos

| Herramienta | Qué mide | Escala |
|---|---|---|
| `conversation_benchmark_asesor.json` | comprensión de asesor, ofertas, deixis, habla coloquial, emociones | 25 conversaciones, 56 turnos (48 con comprobaciones) |
| `persona_conversations.py` | equivalencia metamórfica: la misma conversación escrita por 11 perfiles se interpreta igual | 1.000 conversaciones × 2, 16.339 turnos |
| `long_conversations.py` | hilos adversariales de 20–50 turnos; seguimiento, acuses, consulta acotada, sin repeticiones, llamadas al modelo | 300 hilos, 10.397 turnos |

## 3. Métricas antes y después (mismo instrumento, mismo corpus, sin modelo)

| Banco | Antes | Después |
|---|---|---|
| Asesor (38 turnos comprobados, etiquetados antes de implementar) | 0.342 | **1.000** |
| Asesor completo (48 turnos: incluye 10 de regresión añadidos al descubrir fallos) | 0.271 | **1.000** |
| Perfiles: global | 0.959 | **1.000** |
| — equivalencia entre perfiles | 0.922 | **1.000** |
| — «no» sin llamar al modelo | 0.275 | **1.000** |
| — «sí» a un ofrecimiento | 0.502 | **1.000** |
| — relleno («ok», 👍) sin modelo | 0.733 | **1.000** |
| Hilos largos: global | 0.925 | **1.000** |
| — acuses sin modelo | 0.420 | **1.000** |
| — seguimiento dentro del tema | 0.915 | **1.000** |
| — llamadas al modelo por turno | 0.88 | **0.70** (−20%) |
| — turnos resueltos sin modelo | 12% | **30%** |
| Tiempo por turno (perfiles) | 10,9 ms | **4,5 ms** |
| Hilos largos, tiempo total | 124 s | **30 s** |
| Banco de desarrollo / reservado | 1.000 / 0.960 | 1.000 / 0.960 |
| Recuperación conversacional hit@1 / recall@5 / MRR | 0.674 / 0.880 / 0.762 | igual |
| Simulador (semillas 7, 13, 29) / estrés | 1.000 / 1.000 | 1.000 / 1.000 |
| Pruebas unitarias | 351 | **404** (431 con integración y e2e, sobre un PostgreSQL desechable) |

**Nota de reproducibilidad.** Entre corridas, o con la CPU saturada, dos casos casi empatados del banco de recuperación (af-02 y af-16) pueden intercambiar posiciones por diferencias de punto flotante del modelo de embeddings: ±1 caso en hit@1. Ocurre igual en el código anterior.

## 4. Experimentos descartados

- **Familias morfológicas en el lematizador** (-ado, -ido, -ación). Arreglaba «reprobar», pero bajaba recall@5 de 0.880 a 0.859 y el simulador de 1.000 a ~0.99. Se sustituyó por la corrección por prefijo, que solo actúa sobre términos ausentes del corpus.
- **Buscar con los términos canónicos en toda pregunta parafraseada** (no solo en los panoramas). af-13 y ge-05 perdían toda su evidencia (contexto 1.00 → 0.00). Revertido.
- **Un panorama para toda necesidad económica.** Empeoraba af-13: «¿dan apoyo económico a estudiantes con pocos recursos?» es una pregunta concreta. Ahora el panorama solo se da cuando la necesidad se expresa sin nombrar la ayuda.

## 5. Lo que sigue pendiente

- **Tablas de varias columnas linealizadas.** El artículo 17 (Cobertura) mezcla columnas de becas y del crédito en el mismo fragmento. «¿Cuánto cubre el crédito educativo?» como pregunta nueva no recupera la fila del interés. En seguimiento sí, gracias al vocabulario por tema. La solución de fondo es extraer las tablas por columna en la ingesta, lo cual cambia el pipeline y quedó fuera del alcance de esta fase.
- **«Dejé de estudiar un año, ¿cómo regreso?»** Se reconoce el reingreso, pero las palabras propias del estudiante diluyen la búsqueda y termina en una abstención honesta con derivación al Registro Académico. El calendario sí fija las «inscripciones de reingreso». La corrección general probada empeoraba otros casos (sección 4).
- **«¿Y si soy menor de edad / extranjero?»** El corpus no lo regula. El sistema busca dentro del tema y deja que el modelo diga que la normativa no lo establece; no hay abstención previa porque sí hay evidencia del tema.

## 6. Solo verificable con la API

- Que el modelo use bien las glosas nuevas: el estado de ánimo («angustia», «alegría»), «ya se le explicó…: no lo repitas» y lo ofrecido aceptado.
- La redacción real de las respuestas a «¿esa también aplica para mí?», «¿y si soy extranjero?» y a los panoramas de necesidades («soy de bajos recursos»).
- Una auditoría de estilo en vivo (`scripts/live_conversations.py`) sobre los tres conjuntos de hilos, comparada con la de la Fase 10.1.

## Verificación

Desde `scripts/`, con `PYTHONPATH=../backend/src:.` y el corpus real:

```
python evaluate_conversations.py --corpus-dir <PDF> --benchmark conversation_benchmark_asesor.json
python persona_conversations.py --corpus-dir <PDF> --conversations 1000
python long_conversations.py --corpus-dir <PDF> --threads 300
```

Y en `backend/`: `pytest tests/unit`, `mypy src`, `ruff check src --select C901`.
