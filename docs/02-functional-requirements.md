# Functional Requirements

Fuente primaria: documento del asesor `Descripción Técnica: Asistente Virtual RAG - UVG Altiplano`. Los requisitos marcados **[Asesor]** provienen directamente de ese documento y no son negociables. Los marcados **[Arquitectura]** son consecuencia de decisiones de arquitectura tomadas por el equipo (persistencia, autenticación, panel admin) y están documentados en su ADR correspondiente — no amplían el dominio del problema, solo lo hacen implementable de forma sostenible.

Cada requisito tiene un identificador estable (`FR-XX`) para trazabilidad hacia el backlog (`07-backlog.md`).

## Actores

- **Estudiante**: usuario autenticado con correo `@uvg.edu.gt` que consulta el asistente.
- **Administrador**: rol interno responsable del corpus documental.
- **Sistema de ingesta**: proceso (CLI) que transforma documentos oficiales en vectores indexados.

## Requisitos funcionales

### Ingesta y procesamiento documental

- **FR-01** [Asesor] El sistema debe extraer texto de documentos oficiales en formato PDF usando PyMuPDF.
- **FR-02** [Asesor] El texto extraído debe limpiarse mediante expresiones regulares (remoción de artefactos de extracción: encabezados, pies de página, saltos de línea espurios).
- **FR-03** [Asesor] El texto limpio debe dividirse en fragmentos de tamaño fijo con solapamiento de 100 caracteres entre fragmentos consecutivos.
- **FR-04** [Asesor] Cada fragmento debe convertirse en un vector numérico usando un modelo de embeddings de la familia Sentence Transformers.
- **FR-05** [Asesor] Los vectores deben indexarse de forma persistente en ChromaDB.

### Recuperación y generación de respuestas

- **FR-06** [Asesor] Ante una consulta del estudiante, el sistema debe convertirla en un vector y recuperar los `Top-K` fragmentos más similares por similitud de coseno.
- **FR-07** [Asesor] El sistema debe generar una respuesta usando el LLM de Anthropic (Claude), construida única y exclusivamente a partir de los fragmentos recuperados.
- **FR-08** [Asesor] Si no se recupera contexto relevante, el sistema debe declarar explícitamente que no posee la información, sin generar una respuesta inventada.
- **FR-09** [Asesor] La generación debe usar temperatura 0.0 (decodificación determinista).
- **FR-10** [Asesor] El sistema debe aplicar una estrategia de Chain-of-Verification antes de entregar la respuesta final al estudiante (ver [ADR-0005](adr/0005-chain-of-verification-strategy.md) para el patrón de implementación elegido).

### Interacción del estudiante

- **FR-11** [Asesor] El estudiante debe poder escribir una pregunta en una interfaz de chat y recibir una respuesta en lenguaje natural.
- **FR-12** [Asesor] La interfaz debe mostrar un indicador de "escribiendo" mientras se procesa la respuesta, para mitigar la percepción de latencia.
- **FR-13** [Arquitectura] El estudiante debe autenticarse con su correo institucional `@uvg.edu.gt` antes de acceder al chat (ver [ADR-0004](adr/0004-institutional-authentication.md)).
- **FR-14** [Arquitectura] El sistema debe persistir el historial de conversación del estudiante autenticado, asociado a su cuenta.

### Gestión documental (administración)

- **FR-15** [Arquitectura] Un administrador autenticado debe poder subir un nuevo documento PDF al corpus institucional.
- **FR-16** [Arquitectura] Un administrador debe poder ver el listado de documentos actualmente indexados.
- **FR-17** [Arquitectura] Un administrador debe poder eliminar o reemplazar un documento existente.
- **FR-18** [Arquitectura] Un administrador debe poder disparar manualmente la reindexación del corpus tras un cambio documental.
- **FR-19** [Arquitectura] Un administrador debe poder consultar el estado de la última indexación (éxito, error, fecha, logs asociados).

> Nota de alcance (ver [ADR-0008](adr/0008-admin-panel-scope.md)): FR-15 a FR-19 son parte de la arquitectura del sistema pero están fuera del alcance de evaluación central de la tesis. Su implementación es prioridad baja frente a FR-01 a FR-14 dentro de la ventana de tiempo disponible (ver `08-roadmap.md`).

## Fuera de alcance funcional (explícito)

- Corrección de normativa por parte del estudiante (el sistema es de solo consulta).
- Notificaciones proactivas (p. ej. avisos de cambios normativos).
- Multilenguaje: el sistema opera únicamente en español.
- Cualquier flujo transaccional (solicitudes, trámites): el sistema informa, no ejecuta procesos administrativos.
