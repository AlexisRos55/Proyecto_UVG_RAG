# Roadmap

## 1. La restricción real: matemática de capacidad

- Plazo: ~3 semanas (2026-09-02 → última semana de septiembre de 2026).
- Equipo: 1 desarrollador, ~1 hora/día.
- Capacidad bruta: 21 días × 1h ≈ **21 horas totales**.
- Capacidad efectiva realista: descontando arranque de contexto diario, depuración imprevista y días con menor disponibilidad, se estima **15-18 horas efectivas de implementación**, no 21.

El backlog completo (`07-backlog.md`) sin panel administrativo (EPIC-1 a EPIC-6, todas `Must`) ya suma **22 horas**. Esto es, por sí solo, igual o superior a la capacidad bruta, y superior a la capacidad efectiva realista. **Conclusión sin rodeos: no alcanza el tiempo para implementar todo lo "obligatorio" con acabado de producción, más el panel administrativo, más una preparación de defensa cómoda.**

Esto no es un fallo de planificación — es exactamente la clase de hallazgo que un Tech Lead debe exponer con números, no ocultar detrás de un cronograma optimista. La alternativa a decirlo ahora es descubrirlo la última semana, bajo presión, con mucho menos margen de maniobra.

## 2. Recomendación de alcance (requiere tu confirmación antes de iniciar implementación)

Propuesta de recorte, en este orden de prioridad (el primero en cortarse es el que menos compromete el objetivo de evaluación de la tesis):

1. **EPIC-7 (Panel administrativo) se ejecuta solo si sobra tiempo después de EPIC-1 a EPIC-6.** Ya está diseñado como de prioridad más baja desde [ADR-0008](adr/0008-admin-panel-scope.md); si no se implementa, el informe de tesis lo documenta honestamente como "diseñado, no implementado por restricción de tiempo", con su arquitectura ya lista como evidencia de que la extensión es viable.
2. **EPIC-3 (Autenticación) se reduce a su forma mínima viable si el tiempo aprieta:** un único flujo de login sin pantalla de registro pública (usuarios de prueba precargados vía script/seed), en vez de un flujo completo de registro + login. Esto recorta US-3.2 de 1.5h a ~0.5h. Se mantiene el hash de contraseña y la protección de rutas (no se sacrifica NFR-04).
3. **EPIC-6 (Evaluación RAGAS) mantiene su prioridad `Must` intacta**, incluso si hay que recortar en otro lado: es el criterio de éxito explícito del asesor y no tiene sustituto razonable.
4. **EPIC-1 y EPIC-2 (ingesta + núcleo RAG) no se recortan bajo ninguna circunstancia**: son el objeto de evaluación central del trabajo de graduación.

Con el recorte del punto 2, el subtotal `Must` baja de 22h a ~21h — todavía al límite de la capacidad bruta, sin margen para imprevistos. Si prefieres no recortar autenticación, la alternativa es aceptar que el panel administrativo (EPIC-7) no se implementará bajo ninguna circunstancia, dejándolo 100% como trabajo futuro documentado.

**Necesito tu confirmación explícita sobre esta propuesta antes de que la implementación comience**, conforme a la regla que definiste (Documento → Arquitectura → Revisión → Implementación).

## 3. Plan por semana (asumiendo la propuesta de la sección 2 aprobada)

### Semana 1 (días 1-7, ~7h) — Base de dominio e ingesta

- Entidades y puertos del dominio (`domain/entities`, `domain/ports`), sin implementación concreta todavía.
- EPIC-1 completo: pipeline de ingesta (extracción, limpieza, chunking, embeddings, indexación) ejecutable por CLI contra un subconjunto real de documentos.
- Pruebas unitarias de los casos de uso de ingesta con dobles de prueba.

**Entregable verificable al final de la semana:** ejecutar el script de ingesta contra un PDF real y confirmar que ChromaDB devuelve fragmentos relevantes ante una consulta manual (sin frontend, sin LLM todavía).

### Semana 2 (días 8-14, ~7h) — Núcleo conversacional y persistencia

- EPIC-2 completo: adaptador Anthropic con Chain-of-Verification single-call, `AnswerStudentQueryUseCase`, endpoint `POST /chat`.
- EPIC-3 (versión mínima acordada en la sección 2): modelo de usuario, login, protección de rutas.
- `docker-compose.yml` con backend + PostgreSQL + healthchecks (EPIC-5, parcial).

**Entregable verificable al final de la semana:** `docker compose up` levanta backend + PostgreSQL; una petición autenticada a `/chat` devuelve una respuesta real generada por Claude y fundamentada en el corpus.

### Semana 3 (días 15-21, ~7h) — Frontend, evaluación y cierre

- EPIC-4: frontend de chat mínimo, conectado al backend real.
- EPIC-6: construcción del golden dataset, corrida de RAGAS, reporte comparativo.
- EPIC-8: preparación de defensa.
- Solo si hay margen: EPIC-7 (panel administrativo).

**Entregable verificable al final de la semana:** sistema completo funcionando de extremo a extremo vía `docker compose up`, con un reporte de evaluación RAGAS documentado y comparado contra la referencia manual.

## 4. Qué pasa si una semana se atrasa

Dado que no hay margen (la capacidad bruta ya está comprometida al límite), un atraso en la Semana 1 o 2 se absorbe recortando primero EPIC-7, luego reduciendo el tamaño del golden dataset de RAGAS (EPIC-6) de 10-15 preguntas a un mínimo de 5-8 — nunca eliminando la evaluación por completo, porque es el criterio de éxito del asesor. El frontend (EPIC-4) no se recorta en funcionalidad, pero puede simplificarse visualmente (menos pulido de UI) sin afectar su funcionamiento.

## 5. Hitos formales

| Hito | Fecha objetivo | Criterio de verificación |
|---|---|---|
| M1 — Ingesta funcional | Fin de semana 1 | Recuperación semántica correcta desde CLI, sin LLM |
| M2 — RAG conversacional end-to-end | Fin de semana 2 | `/chat` autenticado responde con Claude, vía Docker Compose |
| M3 — Sistema evaluado y listo para defensa | Fin de semana 3 | Reporte RAGAS + demo funcional + documentación de tesis consolidada |
