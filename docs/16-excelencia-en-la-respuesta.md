# Fase 10.1 — Excelencia en la respuesta

**Fecha:** 2026-10-02 · **Decisión:** [ADR-0018](adr/0018-response-excellence.md) · **Antecedente:** [15-humanizacion-del-asistente.md](15-humanizacion-del-asistente.md)

Esta fase no buscó más arquitectura ni mejor recuperación como fin en sí mismo: buscó que **cada respuesta** fuera la que daría el mejor asesor de la universidad. El criterio fue leer conversaciones completas contra el modelo real (Claude Haiku 4.5) como las leería un profesor exigente, anotar cada defecto, buscar su causa general y corregirla sin romper nada de lo anterior.

**Método por iteración:**
1. Conversaciones en vivo con una auditoría de estilo automática (`scripts/live_conversations.py`).
2. Lectura completa de la transcripción.
3. Corrección de la causa.
4. Pruebas unitarias, banco de desarrollo, banco reservado, simulador (tres semillas) y benchmark de recuperación.
5. Ninguna regresión aceptada.

Para no ajustar el sistema a un solo conjunto, las conversaciones en vivo se escribieron en **tres conjuntos independientes**, el segundo y el tercero después de corregir lo que mostró el primero.

> **Aviso importante.** Durante la última iteración, la clave de la API de Anthropic **se quedó sin crédito** («Your credit balance is too low»). Las correcciones de esa iteración están verificadas con pruebas, bancos y simulador, pero **no en vivo**; se marcan con «(sin verificar en vivo)». Mientras no se recargue el crédito, la aplicación desplegada responde a toda consulta con el mensaje de error controlado («No pude completar la respuesta…»).

---

## 1. Componentes modificados

No se agregó ninguna capa. Se modificaron componentes existentes y se añadió un método a un puerto:

| Componente | Cambio |
|---|---|
| `conversation_tracker` (dominio) | Ordinales y «la otra»; «ese artículo», «ese reglamento», «esa carrera»; herencia del aspecto («¿y la graduación?»); resumir, continuar y retomar distinguidos; quién escribe; referencias sin antecedente; entidades que comparten palabras; programa «paraguas» fuera de las opciones; método `as_follow_up` |
| `conversation_lexicon` (dominio) | Patrones de resumen, continuación, ordinales, referencias a documento y artículo, audiencias, fórmulas de entrada, pedidos de ayuda; aspectos ampliados («vence», «quitar la beca», «qué tengo que hacer», «reprueba») |
| `institutional_lexicon` (dominio) | Corrector de erratas del dominio; sinónimos (inician/empiezan, revisión/reconsideración, costo/inversión, reprobar/reprobación, unirse a un club) |
| `message_sanitizer` (dominio) | Aplica el corrector; el texto original se sigue guardando tal cual |
| `conversation_guide` (dominio) | Aclaraciones, «no es un registro», remisión repetida al campus, abstenciones con la pregunta del estudiante y con frases neutras |
| `local_skill_catalog` (dominio) | Saludo que responde «buenos días» / «buenas tardes»; agradecimientos sin tuteo |
| `evidence_reranker` (dominio) | El ancla acepta raíces contenidas («reelección» ⊃ «elección») |
| `answer_planner`, `response_plan` (dominio) | Estilo de resumen; directivas con extensión máxima y sin cierres redundantes |
| `AnswerStudentQueryUseCase` (aplicación) | Misma evidencia para reformular; segundo intento local; quién escribe; fecha de hoy; folletos para carreras; remisión no repetida |
| `CorpusCatalogPort.chunks_by_ids` (+ índice en memoria) | Recupera los fragmentos que citó una respuesta anterior |
| `SingleCallVerificationAdapter` (prompt) | Extensión proporcional, no repetir, variar aperturas, campus solo si cambia la respuesta, revisar todos los fragmentos antes de decir «no establece», datos de situación sin pregunta, fecha de hoy |
| `PyMuPDFExtractorAdapter` (infraestructura) | Calendario con columnas desalineadas: 12 fechas recuperadas, entre ellas «17 de diciembre: último día para pagar la cuota de diciembre» |
| `scripts/live_conversations.py`, `live_threads*.json`, simulador | Ejecución en vivo con auditoría de estilo; 4 invariantes nuevos |

## 2. Mejoras conversacionales implementadas

- **Reformular sin cambiar de tema.** «No entendí», «explícalo diferente», «resúmelo», «dame un ejemplo» y «¿por qué?» trabajan sobre los fragmentos que sustentaron la respuesta anterior. Antes, «No entendí» después de la respuesta sobre cursos reprobados explicaba los tipos de ayuda financiera; ahora vuelve a explicar el 5/10/15 % con palabras más simples.
- **Entender a quien escribe como escribe.**
  - Erratas: «bcas», «becaz», «veca», «quiero saver», «kiero».
  - Fórmulas de entrada: «cambiando de tema», «quiero saber».
  - Frases sin signos y en minúsculas.
- **Seguir listas y señalar lo nombrado.**
  - «¿La primera?», «¿y la segunda?», «¿y la otra?».
  - «Ese artículo» (el que se está leyendo).
  - «Ese reglamento» (su ficha: quién lo elaboró, revisó y autorizó).
  - «Esa carrera».
  - «La beca de antes», aun sin «esa».
- **Continuar con naturalidad.**
  - «¿Y la graduación?» después de «¿cuándo inician las clases?» pregunta lo mismo sobre otro asunto.
  - «Continúa» justo después de una respuesta sigue explicando; después de una pausa, retoma el tema.
- **Hablarle a quien pregunta.** Un padre, un docente o personal administrativo reciben trato de usted, con el estudiante en tercera persona y sin que se les atribuyan cargos. Una presentación sin pregunta («Soy mamá de una estudiante de primer ingreso») recibe «Con gusto le ayudo. ¿Qué le gustaría saber?…».
- **Preguntar cuando no hay a qué referirse.**
  - «¿Y eso?» al empezar recibe «¿A qué te refieres?…».
  - «requisitos» suelto recibe «¿Los requisitos de qué? Por ejemplo, de una beca, de la inscripción o para crear un club.»
  - «¿Ese artículo?» sin número recibe «¿Qué artículo…?».
- **Distinguir normas de registros.** «¿Quién ganó la última elección?» se explica: el asistente consulta reglamentos, no resultados, y puede contar cómo funcionan las elecciones. Antes se rechazaba como fuera de dominio, mientras la misma respuesta ofrecía hablar de elecciones.
- **Segundo intento antes de rendirse.**
  - «¿Me devuelven el dinero?» después de hablar de retiros se lee como seguimiento.
  - «¿Quién decide?» sobre el Programa Regular se busca en el tema y llega al Comité de Ayudas Financieras.
  - «¿Puedo pedir revisión?» llega al artículo de reconsideración.
- **Fechas relativas.** «¿Cuál es la próxima fecha de pago?» se responde sabiendo qué día es hoy *(sin verificar en vivo)*.
- **Situación sin pregunta.** «Trabajo en una empresa con convenio» o «estudio Administración» se responden con lo que aplica a esa situación *(sin verificar en vivo)*.

## 3. Patrones repetitivos eliminados

Medido con la auditoría de estilo sobre el mismo conjunto de 83 turnos (primera corrida de la fase frente a la última corrida limpia):

| Patrón | Antes | Después |
|---|---|---|
| Oraciones de 8+ palabras repetidas dentro de una misma conversación | 12 | **2** (y 0 en el segundo conjunto) |
| «Conviene confirmar/consultar…» por respuesta | 0.20 | **0.11** |
| «… en el campus» por respuesta | 0.36 | **0.28** |
| «De acuerdo con…» por respuesta | 0.034 | **0.015** |
| «La documentación…» por respuesta | 0.017 | **0** |
| Palabras al responder una pregunta corta y puntual | 116 | **105** (89 en el segundo conjunto) |
| Respuestas que el modelo cierra con una pregunta | 0 | 0 |

También se eliminaron:
- **El párrafo genérico «Hay normativa relacionada con tu consulta, pero no dice lo suficiente…».** Se repetía idéntico en tres turnos seguidos y remitía a un artículo irrelevante. Ahora se dice qué se buscó o se piden otras palabras.
- **La línea «Importante:».** Repetía lo que la respuesta acababa de decir *(cambio sin verificar en vivo)*.
- **El tuteo en los agradecimientos.** «Si te surge…», «Pregunta cuando lo necesites» sonaban mal dirigidos a un padre o un docente.
- **El mismo saludo a cualquier hora.** Ahora a «Buenos días» se responde «Buenos días».
- **«La Licenciatura en Educación Física de carreras».** Era una etiqueta de memoria mal armada.

Dos patrones **no** se lograron eliminar del todo; ver la sección 8.

## 4. Nuevas capacidades de conversación

- Ordinales y «la otra» sobre la última lista de opciones.
- Resumir («¿puedes resumir?», «en pocas palabras», «resúmelo en tres puntos»).
- Distinguir «continúa» (seguir explicando) de «sigamos» tras una pausa (retomar).
- Trato según quién escribe (estudiante, padre de familia, docente, personal administrativo).
- Aclaración ante una referencia sin antecedente o un aspecto suelto.
- Preguntas sobre el documento en consulta (ficha: elaboración, revisión, autorización, versión, vigencia).
- Corrección de erratas del dominio.
- Panorama de carreras con un fragmento por folleto (Agroforestería, Educación Física, Agrícola y Pecuaria, Centro de Idiomas, Informática…).
- Fecha de hoy en preguntas de fechas *(sin verificar en vivo)*.
- Remisión al campus sin repetirse de una respuesta a la siguiente.

## 5. Conversaciones que antes fallaban y ahora funcionan

Fragmentos reales de las corridas en vivo (primera corrida de la fase frente a una posterior):

| Conversación | Antes | Ahora |
|---|---|---|
| «quiero saver de las bcas» | «No logré relacionar tu mensaje…» | Panorama de becas para el Altiplano |
| «Háblame de las becas AVE» | Abstención | Las tres becas AVE con su cobertura |
| «¿La primera?» → «¿Y la segunda?» → «¿Y la otra?» | Repetía el panorama completo | Trasciende, Despega, Transforma, en orden |
| «¿Cuál me conviene si trabajo en una empresa aliada?» (tras las AVE) | Abstención | «La Beca Despega es la que te aplica…» con tabla |
| «Soy papá de un estudiante, ¿mi hijo puede tener beca?» | Abstención | «Sí, su hijo puede acceder a becas…», de usted |
| «¿Y si reprueba un curso?» (padre) | «La normativa no establece qué sucede…» (falso) | «Si su hijo reprueba un curso, la beca se reduce… 5 %, 10 %, 15 %» |
| «Soy docente, ¿cómo funcionan las horas beca?» | «Como Director de Departamento, eres responsable…» | Explica sin atribuirle un cargo |
| «¿Quién integra el Comité de Ayudas Financieras…?» | Comparación fantasma entre seis instancias | Los cuatro integrantes, directo |
| «¿Ese reglamento quién lo aprobó?» | Abstención | Quién lo elaboró y revisó, versión y vigencia |
| «Artículo 68» → «¿Ese artículo qué dice?» | Explicaba los artículos 43, 45 y 46 | El Artículo 68 |
| «¿Cuándo inician las clases?» → «¿Y la graduación?» | Reembolso del crédito al graduarse | La ceremonia del 14 de noviembre |
| «¿Y si repruebo un curso?» → «No entendí» | Explicaba los tipos de ayuda | El 5/10/15 %, en palabras simples |
| «¿Puedes resumir?» | «No logré relacionar tu mensaje…» | Cuatro viñetas con lo esencial |
| «Continúa» (justo después de una respuesta) | Recapitulación del tema | Sigue con lo que faltó |
| «¿Qué carreras hay en el campus?» | «La normativa no contiene un listado de carreras» | Carreras de los folletos: primero parcial (Educación y Maestría); con un fragmento por folleto *(sin verificar en vivo)* |
| «Soy mamá de una estudiante de primer ingreso» | Abstención | «Con gusto le ayudo. ¿Qué le gustaría saber?…» |
| «requisitos» (al empezar) | Índice de artículos | «¿Los requisitos de qué?…» |
| «¿Y eso?» (al empezar) | «No logré relacionar tu mensaje…» | «¿A qué te refieres?…» con ejemplos |
| «¿Quién ganó la última elección de la asociación?» | Rechazo como fuera de dominio | Explica que consulta normas, no resultados |
| «Quiero meterme a un club de fútbol» | Abstención | Cómo se integra un club deportivo |
| «¿Cuánto cuesta?» (hablando de Informática) | «Las carreras no forma parte de la documentación…» | Se busca en el folleto de Informática *(sin verificar en vivo)* |
| «¿Quién decide?» (Programa Regular) | Abstención | «… el Comité de Ayudas Financieras es quien aprueba el porcentaje…» |
| «¿Puedo pedir revisión?» | Abstención | «Sí… puedes solicitar reconsideración cuando compruebes un cambio en tu situación socioeconómica…» |
| «Quiero saber cuándo empiezan las clases» | «No logré relacionar tu mensaje…» | «Las clases del primer ciclo 2027 inician el 18 de enero de 2027.» |
| «¿Me devuelven el dinero?» (tras hablar de retiros) | «No logré relacionar tu mensaje…» | Abstención honesta que nombra la pregunta: el reglamento no habla de reembolsos |
| «¿En qué fecha se paga la cuota de diciembre?» | «12 de diciembre» (la fila del calendario había perdido su fecha) | La fila se reconstruye: «17 de diciembre» *(sin verificar en vivo)* |

## 6. Pruebas ejecutadas

| Prueba | Alcance |
|---|---|
| Pruebas automatizadas | **352** en verde: 324 unitarias (17 nuevas de esta fase), integración y e2e con Postgres desechable |
| Conversaciones en vivo | **7 corridas limpias, 524 turnos** leídos completos en tres conjuntos independientes. Otras dos corridas se perdieron: una por el límite de peticiones (en paralelo) y otra por falta de crédito |
| Simulador | 18 invariantes, 3 semillas, **360 conversaciones y 9 350 turnos**, cero errores |
| Auditoría de textos deterministas | 150 conversaciones simuladas más; 195 textos locales distintos revisados con patrones gramaticales y a mano. Se corrigieron tres defectos |
| Banco de conversaciones | Desarrollo: 86 turnos. Reservado: 31 turnos (nunca usado para ajustar) |
| Recuperación | 50 preguntas, configuraciones línea base, mejorada y conversacional, repetidas para separar el ruido del índice |
| Extracción | Comparación del texto extraído de los 16 PDF antes y después: solo cambia el calendario |

## 7. Resultados de los benchmarks

| Medición | Inicio de la fase | Final |
|---|---|---|
| Banco de desarrollo | 1.000 | **1.000** |
| Banco reservado (sin ajustar) | 0.920 | **0.960** |
| Simulador (14 → 18 invariantes) | 1.000 | **1.000** en los 18 |
| Recuperación desplegada · hit@1 | 0.587 | **0.652** |
| · recall@5 | 0.804 | **0.880** |
| · MRR | 0.683 | **0.746** |
| · recall del contexto | 0.924 | **0.924** |
| · contexto enviado al modelo (caracteres) | ≈5 530 | **4 594** |
| · abstención sin evidencia / falsas abstenciones | 1.000 / 0.000 | 1.000 / 0.000 |

En vivo, sobre el primer conjunto de 83 turnos, el modelo pasó a responder 65 turnos en lugar de 59: hay menos abstenciones donde sí había respuesta. Sobre el segundo conjunto, 54 en lugar de 50.

Nota de método: el índice aproximado de ChromaDB varía ±1 caso de hit@1 entre reconstrucciones. Las cifras de recuperación se confirmaron con dos ejecuciones idénticas.

## 8. Limitaciones que siguen existiendo

- **Crédito de la API agotado.** La última iteración (fecha de hoy, «quitar la beca», situaciones sin pregunta, «explícalo con un ejemplo», «en tres puntos», cierre «Importante», calendario) está verificada sin el modelo, no en vivo.
- **Aperturas negativas.** Siguen en torno al 6–7 % de las respuestas generadas. Parte es correcta (cuando lo que falta es justo lo preguntado) y parte es el modelo que no sigue la instrucción. La reordenación determinista solo se aplica a preguntas de elección.
- **«En el Campus Altiplano…».** Sigue abriendo los panoramas de becas (≈15 % de las respuestas en el primer conjunto). Es correcto, pero se nota repetido entre conversaciones que preguntan lo mismo.
- **Inferencias del modelo.** Hubo un ejemplo con una proporción inventada («una quinta parte») y afirmaciones más fuertes que la norma («si sacas 60, pierdes la beca»). Las reglas del prompt lo reducen, no lo garantizan.
- **Tablas por programa.** El «máximo del 15 % anual» pertenece a una fila de una tabla cuyas marcas por programa se pierden. El modelo lo atribuyó una vez al Programa Regular.
- **Consistencia entre corridas.** La temperatura es 0, pero el hilo y la evidencia cambian con cada conversación, y una misma pregunta («¿y si cambio de carrera?») recibió matices distintos.
- **Entidades de carrera incompletas.** El extractor no reconoce todas las carreras de los folletos (Informática, por ejemplo). «Esa carrera» depende de una lista de palabras.
- **Recuperación profunda.** «¿Quiénes no pueden votar?», la pérdida de la membresía de un club y «¿cuánto dura en el cargo?» (Artículo 11 del reglamento de grupos) siguen sin traer su artículo; esta última se abstuvo en vivo aunque el dato existe.
- **Vocabulario interno.** En una respuesta apareció «El fragmento disponible menciona…». La guardia de voz ya lo reescribe, pero muestra que el modelo todavía filtra términos internos de vez en cuando.

## 9. Propuestas para la Fase 11

1. **Alertas del proveedor.** Una comprobación de salud que llame al modelo y avise del crédito o de los límites antes de una demostración. Hoy el fallo es elegante, pero silencioso para quien administra.
2. **Juez automático de estilo y fidelidad.** Sobre los tres conjuntos en vivo, una rúbrica puntuada por un modelo distinto: primera frase útil, extensión, repetición, cifras que no estén en los fragmentos. Así cada versión tendría una nota comparable, no solo métricas léxicas.
3. **Verificación numérica determinista.** Toda cifra, porcentaje o fecha de la respuesta debe aparecer en los fragmentos; si no, se marca o se retira.
4. **Tablas estructuradas en la ingesta.** Para las matrices de becas por programa.
5. **Entidades de carrera desde los títulos de los folletos.** Para que «esa carrera» y los costos por carrera no dependan de una lista fija.
6. **Perfil del estudiante con consentimiento.** Carrera, campus y beca actual, para que «¿cuál me conviene?» no necesite preguntar.
7. **Caché del prompt de sistema.** Para reducir costo y latencia por consulta.

---

## Verificación

```bash
cd scripts
PYTHONPATH=../backend/src python simulate_conversations.py --corpus-dir <PDF> --seed 7      # también 13 y 29
PYTHONPATH=../backend/src python evaluate_conversations.py --corpus-dir <PDF>
PYTHONPATH=../backend/src python evaluate_conversations.py --corpus-dir <PDF> --benchmark conversation_benchmark_holdout.json
PYTHONPATH=../backend/src python evaluate_retrieval.py --corpus-dir <PDF> --configs baseline,enhanced,conversational
PYTHONPATH=../backend/src python live_conversations.py --corpus-dir <PDF> --threads live_threads.json --out <carpeta>   # requiere crédito
cd ../backend && pytest
```
