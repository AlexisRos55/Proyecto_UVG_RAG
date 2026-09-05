# Backlog inicial

Estimaciones en horas de desarrollo efectivo, calibradas para un desarrollador solo con apoyo de asistentes de IA como herramienta de ingeniería (no como reemplazo de las horas de implementación, revisión y prueba). Prioridad en escala MoSCoW: **Must** (bloquea la defensa), **Should** (fuertemente deseable), **Could** (se implementa solo si sobra tiempo).

**Advertencia de capacidad (ver `08-roadmap.md` para el análisis completo):** la suma de historias `Must` de EPIC-1 a EPIC-6 ya asciende a ~22 horas, prácticamente el total del presupuesto disponible (~21 horas en 3 semanas a 1h/día). Esto significa que EPIC-7 (panel administrativo) y parte de EPIC-8 compiten por tiempo que no existe holgado. El roadmap detalla la propuesta de recorte.

## EPIC-1 — Pipeline de ingesta documental (CLI)

| ID | Historia | Criterios de aceptación | Prioridad | Estimación |
|---|---|---|---|---|
| US-1.1 | Como sistema, extraigo texto de un PDF institucional usando PyMuPDF | Dado un PDF de ejemplo, el texto extraído no está vacío y conserva el orden de lectura | Must | 1h |
| US-1.2 | Como sistema, limpio el texto extraído con reglas de regex | Encabezados/pies de página repetidos y saltos de línea espurios se eliminan sin cortar palabras | Must | 0.5h |
| US-1.3 | Como sistema, divido el texto limpio en fragmentos de tamaño fijo con overlap de 100 caracteres | Cada fragmento respeta el tamaño configurado y comparte 100 caracteres con el fragmento anterior | Must | 1h |
| US-1.4 | Como sistema, genero embeddings de cada fragmento con Sentence Transformers | Cada fragmento tiene un vector asociado de la dimensión esperada por el modelo | Must | 0.5h |
| US-1.5 | Como sistema, indexo los vectores en ChromaDB de forma persistente | Tras reiniciar el proceso, una consulta recupera fragmentos ya indexados en una corrida anterior | Must | 1h |

## EPIC-2 — Núcleo conversacional RAG

| ID | Historia | Criterios de aceptación | Prioridad | Estimación |
|---|---|---|---|---|
| US-2.1 | Como estudiante, al preguntar algo, el sistema recupera los `Top-K` fragmentos más relevantes | Dada una pregunta relacionada al corpus, se recuperan K fragmentos ordenados por similitud de coseno | Must | 1h |
| US-2.2 | Como estudiante, recibo una respuesta generada y autoverificada (Chain-of-Verification single-call) | La respuesta incluye una señal de fundamentación; el adaptador Anthropic se invoca una sola vez por consulta | Must | 2h |
| US-2.3 | Como estudiante, si no hay contexto relevante, el sistema me dice explícitamente que no tiene la información | Ante una pregunta fuera de dominio, la respuesta declara la ausencia de información, no inventa contenido | Must | 0.5h |
| US-2.4 | Como estudiante, interactúo con el asistente a través de un endpoint HTTP | `POST /chat` devuelve una respuesta JSON válida en menos del timeout configurado | Must | 1h |
| US-2.5 | Como estudiante, mi conversación queda guardada en mi historial | Tras una consulta, existe un registro en PostgreSQL asociado a mi usuario | Must | 1h |

## EPIC-3 — Autenticación institucional

| ID | Historia | Criterios de aceptación | Prioridad | Estimación |
|---|---|---|---|---|
| US-3.1 | Como sistema, modelo un usuario con correo institucional en PostgreSQL | Existe una migración de Alembic para la tabla `users` con restricción de dominio `@uvg.edu.gt` | Must | 1h |
| US-3.2 | Como estudiante, me registro e inicio sesión con correo y contraseña | La contraseña se almacena con hash; login inválido devuelve 401 sin filtrar información sensible | Must | 1.5h |
| US-3.3 | Como sistema, protejo las rutas de chat y admin exigiendo sesión válida | Una petición sin sesión válida a `/chat` o `/admin/*` devuelve 401 | Must | 1h |

## EPIC-4 — Frontend de chat

| ID | Historia | Criterios de aceptación | Prioridad | Estimación |
|---|---|---|---|---|
| US-4.1 | Como equipo, tengo el proyecto frontend inicializado con el stack decidido | `npm run dev` levanta la app con Tailwind y shadcn/ui funcionando | Must | 1h |
| US-4.2 | Como estudiante, inicio sesión desde una pantalla dedicada | El formulario valida el dominio institucional con Zod antes de enviar la petición | Must | 1h |
| US-4.3 | Como estudiante, converso con el asistente viendo un indicador de "escribiendo" | Al enviar una pregunta, se muestra un estado de carga hasta recibir la respuesta | Must | 1.5h |

## EPIC-5 — Infraestructura y observabilidad

| ID | Historia | Criterios de aceptación | Prioridad | Estimación |
|---|---|---|---|---|
| US-5.1 | Como equipo, empaqueto backend y frontend en imágenes Docker | Cada Dockerfile construye sin errores | Must | 1h |
| US-5.2 | Como equipo, levanto todo el sistema con un solo comando | `docker compose up` levanta backend, frontend y PostgreSQL con healthchecks en verde | Must | 0.5h |
| US-5.3 | Como equipo, cada etapa del pipeline RAG queda registrada en logs estructurados | Los logs muestran tiempo de recuperación, generación y tokens consumidos por consulta | Must | 0.5h |

## EPIC-6 — Evaluación RAGAS

| ID | Historia | Criterios de aceptación | Prioridad | Estimación |
|---|---|---|---|---|
| US-6.1 | Como equipo, construyo un conjunto mínimo de preguntas de referencia | Existen al menos 10-15 pares pregunta/respuesta esperada cubriendo el corpus | Must | 1h |
| US-6.2 | Como equipo, ejecuto RAGAS contra el sistema real | El script produce fidelidad, relevancia de contexto y relevancia de respuesta por pregunta | Must | 1.5h |
| US-6.3 | Como equipo, tengo una referencia de tiempo de atención manual para comparar | Existe al menos una estimación documentada (aunque no sea una medición extensa) del tiempo manual | Must | 0.5h |
| US-6.4 | Como equipo, tengo un reporte comparativo consolidado | Existe un documento/tabla con las 4 métricas del sistema vs. la referencia manual | Must | 0.5h |

## EPIC-7 — Panel administrativo (prioridad más baja, ver [ADR-0008](adr/0008-admin-panel-scope.md))

| ID | Historia | Criterios de aceptación | Prioridad | Estimación |
|---|---|---|---|---|
| US-7.1 | Como sistema, modelo el estado de indexación de un documento en PostgreSQL | Existe una tabla `documents` con estado (`pending`/`indexed`/`error`) | Could | 0.5h |
| US-7.2 | Como administrador, subo/listo/elimino documentos vía API | Endpoints `POST/GET/DELETE /admin/documents` funcionan protegidos por rol `admin` | Could | 1.5h |
| US-7.3 | Como administrador, uso una pantalla mínima para gestionar documentos | La pantalla permite subir un PDF y ver el estado de indexación | Could | 1.5h |

## EPIC-8 — Documentación de tesis y defensa

| ID | Historia | Criterios de aceptación | Prioridad | Estimación |
|---|---|---|---|---|
| US-8.1 | Como equipo, consolido los resultados de evaluación en el informe de tesis | El informe cita las métricas reales obtenidas, no estimaciones | Should | 1h |
| US-8.2 | Como equipo, preparo la demo y el guion de defensa | Existe un guion de demo que cubre el caso feliz y el caso de "no tengo información" | Should | 1h |

## Resumen de esfuerzo

| Épica | Prioridad dominante | Horas estimadas |
|---|---|---|
| EPIC-1 Ingesta | Must | 4.0h |
| EPIC-2 Núcleo RAG | Must | 5.5h |
| EPIC-3 Autenticación | Must | 3.5h |
| EPIC-4 Frontend chat | Must | 3.5h |
| EPIC-5 Infraestructura | Must | 2.0h |
| EPIC-6 Evaluación RAGAS | Must | 3.5h |
| **Subtotal Must (EPIC 1-6)** | | **22.0h** |
| EPIC-7 Panel admin | Could | 3.5h |
| EPIC-8 Documentación defensa | Should | 2.0h |
| **Total backlog completo** | | **27.5h** |

El presupuesto disponible es de ~21 horas. El análisis de este desbalance y la propuesta de recorte están en `08-roadmap.md`.
