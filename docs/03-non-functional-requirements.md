# Non-Functional Requirements (NFR)

Cada NFR incluye su justificación y, cuando aplica, cómo se verifica. Los NFR de este documento están calibrados para el alcance real del proyecto: un prototipo académico de un solo desarrollador con presupuesto personal, desplegado localmente para su defensa — no un sistema en producción. Fijar NFR de nivel productivo (p. ej. 99.9% de disponibilidad) sería una decisión no defendible frente al tribunal, porque no hay forma de sustentarla con la infraestructura y el tiempo disponibles.

## NFR-01 — Rendimiento / Latencia

**Requisito:** El sistema debe registrar y reportar la latencia de extremo a extremo de cada consulta (desde que el estudiante envía la pregunta hasta que recibe la respuesta completa), para poder compararla contra el tiempo de atención manual, tal como exige la evaluación RAGAS del asesor.

**Justificación:** La latencia es una de las cuatro métricas de validación explícitamente pedidas por el asesor. No se fija un umbral numérico de éxito porque no existe todavía una medición base de la atención manual — se define como parte de la fase de evaluación, no como arquitectura.

**Cómo se verifica:** Logging estructurado (Loguru) con timestamps por etapa del pipeline (recuperación, generación, verificación), agregado en el reporte de evaluación.

## NFR-02 — Costo de operación

**Requisito:** El sistema debe minimizar el consumo de tokens de la API de Anthropic por consulta.

**Justificación:** El presupuesto es personal y limitado (ver Project Charter, sección 5). Esto se traduce en decisiones concretas de arquitectura, no solo en una intención: estrategia de verificación en una sola llamada ([ADR-0005](adr/0005-chain-of-verification-strategy.md)), modelo económico por defecto ([ADR-0006](adr/0006-configurable-llm-model-selection.md)), y un puerto de caché de respuestas diseñado para implementación futura si el tiempo lo permite.

**Cómo se verifica:** Registro de tokens consumidos por solicitud (entrada/salida) en cada log de consulta.

## NFR-03 — Mantenibilidad

**Requisito:** La lógica de negocio (casos de uso, entidades) no debe depender directamente de FastAPI, ChromaDB, el SDK de Anthropic, SQLAlchemy ni Sentence Transformers. Toda dependencia externa se accede a través de un puerto definido en la capa de dominio.

**Justificación:** Es el requisito no funcional con mayor peso en la evaluación de tesis: demuestra la aplicación real (no solo declarada) de Arquitectura Hexagonal y del Principio de Inversión de Dependencias.

**Cómo se verifica:** Los casos de uso deben ser testeables con dobles de prueba (fakes/stubs) que implementen los puertos, sin necesidad de credenciales reales ni de contenedores levantados.

## NFR-04 — Seguridad

**Requisito:**
- Las credenciales (API keys, cadenas de conexión, secretos de sesión) se gestionan mediante variables de entorno, nunca en código fuente ni en control de versiones.
- Las contraseñas de usuario se almacenan con hash (no en texto plano).
- El sistema valida y sanitiza la entrada del usuario antes de incluirla en el prompt del LLM, como mitigación básica de inyección de prompt.
- El acceso al chat y al panel administrativo requiere autenticación; el panel administrativo requiere además el rol `admin`.

**Justificación:** El sistema maneja información institucional (beneficios, seguros) asociada a cuentas de estudiantes reales. Aunque el alcance es un prototipo, la ausencia total de estos controles no sería defendible ante un tribunal con conocimiento de seguridad básica, y contradice el objetivo explícito de "diseño de software excelente".

**Cómo se verifica:** Revisión de código (no se commitean secretos), pruebas unitarias de la capa de autenticación, casos de prueba con entradas adversariales básicas.

## NFR-05 — Observabilidad

**Requisito:** Todo el sistema debe emitir logging estructurado (Loguru) con niveles apropiados, y el backend debe exponer un endpoint de *health check* verificable por Docker Compose.

**Justificación:** Sin trazabilidad de lo que ocurre en cada etapa del pipeline RAG, las métricas de RAGAS carecen de evidencia de cómo se midieron, y depurar fallas de un solo desarrollador con tiempo limitado sin logs adecuados es inviable.

**Cómo se verifica:** Cada servicio en `docker-compose.yml` declara un `healthcheck`; los logs de cada etapa del pipeline son inspeccionables.

## NFR-06 — Portabilidad / Reproducibilidad

**Requisito:** El sistema completo debe poder levantarse con un único comando (`docker compose up`), sin pasos de configuración manual adicionales más allá de completar el archivo `.env`.

**Justificación:** Es un requisito explícito del asesor (Docker + Docker Compose) y además es indispensable para que el tribunal o cualquier tercero pueda ejecutar el sistema durante la defensa sin depender del entorno de desarrollo del autor.

**Cómo se verifica:** `docker-compose.yml` con todos los servicios necesarios (backend, frontend, PostgreSQL); `.env.example` documentando cada variable requerida.

## NFR-07 — Gobierno de datos (documentado, no resuelto por completo)

**Requisito:** El sistema debe documentar explícitamente qué datos salen de la infraestructura local hacia servicios de terceros.

**Justificación / hallazgo:** El documento del asesor indica que ChromaDB se mantiene local "por privacidad", pero cada consulta envía la pregunta del estudiante y los fragmentos de contexto recuperados a la API en la nube de Anthropic. La privacidad es parcial: el corpus documental completo no se expone, pero sí se exponen fragmentos puntuales y las preguntas de los estudiantes, consulta por consulta. Dado el presupuesto y el plazo, no se implementa un LLM local como alternativa (ver [ADR-0006](adr/0006-configurable-llm-model-selection.md), sección "Alternativas consideradas"); se documenta como riesgo aceptado (ver `09-risk-register.md`, R-01).

**Cómo se verifica:** Este documento y el ADR correspondiente son la evidencia de que la decisión fue consciente, no omitida.

## NFR-08 — Usabilidad

**Requisito:** La interfaz de chat debe comunicar visualmente el estado de la solicitud (enviando, esperando respuesta, error) y debe distinguir claramente cuándo el asistente respondió con base documental de cuándo declaró no tener información.

**Justificación:** Es la forma en que el requisito funcional FR-08 (declarar falta de información) se vuelve perceptible para el usuario — un requisito funcional sin su contraparte de UX pierde valor práctico.

**Cómo se verifica:** Revisión manual de la interfaz durante pruebas exploratorias antes de la defensa.
