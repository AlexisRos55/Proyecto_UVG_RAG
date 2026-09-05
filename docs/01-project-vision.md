# Project Vision

## 1. Declaración de visión

Para los estudiantes de UVG Altiplano que necesitan resolver dudas sobre normativa institucional, beneficios y seguros, el Asistente Virtual RAG es una aplicación conversacional que entrega respuestas precisas y trazables a partir de los documentos oficiales de la universidad, a diferencia de la atención manual actual, que es lenta y depende de la disponibilidad del personal administrativo. A diferencia de un chatbot genérico basado únicamente en un modelo de lenguaje, este asistente nunca responde con información que no pueda sustentar en un fragmento documental recuperado.

## 2. Problema que resuelve

- Los estudiantes tienen preguntas recurrentes sobre reglamentos, beneficios y seguros que hoy solo puede responder personal administrativo.
- Esto genera latencia (tiempo de espera del estudiante) y costo operativo (tiempo del personal en consultas repetitivas de bajo valor).
- Un LLM sin control de fuentes resolvería la latencia pero introduciría un riesgo inaceptable para un contexto institucional: alucinar normativa que no existe, con consecuencias reales para decisiones del estudiante (p. ej. becas, seguros, fechas límite).

La arquitectura RAG es la respuesta a esa tensión: mantiene la velocidad de un asistente conversacional sin ceder el control de la fuente de verdad, que sigue siendo el documento oficial.

## 3. Usuarios objetivo

| Actor | Descripción | Necesidad principal |
|---|---|---|
| Estudiante UVG Altiplano | Usuario final autenticado con correo institucional | Obtener respuestas rápidas y confiables sobre normativa, sin tener que leer el reglamento completo ni esperar a personal administrativo |
| Administrador (rol interno) | Miembro del equipo responsable de mantener el corpus documental actualizado | Subir, reemplazar o eliminar documentos oficiales y disparar la reindexación, sin depender de acceso directo a la base de datos vectorial |

No se definen otros actores (p. ej. personal administrativo como usuario final del chat, aspirantes, egresados) porque el documento del asesor no los menciona; si se requieren, es una ampliación de alcance funcional que debe validarse con el asesor primero, no una decisión de arquitectura.

## 4. Qué NO es este proyecto (fronteras explícitas)

- No es un asistente de propósito general: no responde preguntas fuera del corpus documental institucional.
- No es un sistema de identidad institucional: no reemplaza ni integra el sistema de autenticación oficial de UVG (decisión registrada en [ADR-0004](adr/0004-institutional-authentication.md)).
- No es un gestor documental completo (CMS): el panel administrativo cubre únicamente el ciclo mínimo de subir/ver/eliminar/reindexar (ver [ADR-0008](adr/0008-admin-panel-scope.md)).
- No es un sistema de producción con garantías de disponibilidad: es un prototipo de tesis, desplegado localmente para su defensa.

## 5. Principios de diseño que guían el proyecto

Estos principios no son una lista genérica de buenas prácticas: cada uno responde a un riesgo concreto identificado en el análisis inicial del proyecto.

1. **Arquitectura Hexagonal (Ports & Adapters).** El pipeline RAG depende de piezas con alta probabilidad de cambio durante el desarrollo (modelo de embeddings, proveedor LLM, vector store). Aislar el dominio detrás de puertos permite que un cambio de proveedor (p. ej. cambiar el modelo de Claude, o incluso el vector store) no obligue a tocar la lógica de negocio.
2. **Clean Architecture (regla de dependencia hacia adentro).** Los casos de uso (p. ej. "responder una consulta del estudiante") deben poder probarse sin FastAPI, sin ChromaDB real y sin llamar a la API de Anthropic — usando dobles de prueba que implementan los mismos puertos.
3. **SOLID aplicado, no solo declarado.** En particular, Inversión de Dependencias (los casos de uso dependen de interfaces, no de SDKs concretos) y Responsabilidad Única (la extracción de texto, el chunking, el embedding y la generación son responsabilidades separadas, no un único módulo "RAG").
4. **Costo y latencia como restricciones de diseño, no como detalles de implementación.** Dado el presupuesto personal y limitado, cada decisión de IA (modelo, estrategia de verificación, tamaño de contexto) se evalúa explícitamente por su costo en tokens, no solo por su calidad de respuesta.
5. **Decisiones documentadas, no tácitas.** Toda decisión de arquitectura relevante se registra como ADR con alternativas y trade-offs, porque el objetivo del proyecto no es solo que funcione, sino que el diseño sea defendible.

## 6. Métrica de éxito del producto (no solo del proyecto)

El asistente es exitoso si, ante una pregunta dentro del dominio documental, entrega una respuesta cuya fidelidad y relevancia (medidas por RAGAS) sean comparables o superiores a la atención manual, y si ante una pregunta fuera del dominio documental, se abstiene explícitamente en lugar de alucinar. Ambas condiciones son igual de importantes: un sistema que responde bien pero nunca dice "no lo sé" no cumple el objetivo del asesor.
