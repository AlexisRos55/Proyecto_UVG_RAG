# ADR-0001: Adoptar Arquitectura Hexagonal + Clean Architecture

**Estado:** Aceptado

**Fecha:** 2026-09-02

## Contexto

El asesor exige un pipeline RAG con componentes que, por su naturaleza, tienen alta probabilidad de cambiar durante el desarrollo o después de la defensa de tesis: el modelo de embeddings, el proveedor del LLM, y potencialmente el vector store. Además, este proyecto es el artefacto principal de un trabajo de graduación en Ingeniería en Tecnología de Sistemas Informáticos, por lo que la calidad del diseño de software es en sí misma un criterio de evaluación, no solo el resultado funcional.

## Decisión

Se adopta Arquitectura Hexagonal (Ports & Adapters) para desacoplar el dominio de las tecnologías externas, combinada con Clean Architecture para definir la regla de dependencia entre capas (`infrastructure → application → domain`, nunca al revés).

## Alternativas consideradas

| Alternativa | Ventajas | Desventajas | Por qué se descartó |
|---|---|---|---|
| Arquitectura en capas tradicional (MVC / N-capas simple) | Más rápida de implementar, familiar, menos archivos | El acoplamiento entre lógica de negocio y frameworks/SDKs es directo; cambiar de LLM o vector store implicaría tocar la lógica de negocio | No demuestra dominio de patrones de desacoplamiento avanzados; mayor riesgo de "vendor lock-in" con Anthropic SDK/ChromaDB dentro del propio código de negocio |
| Solo Hexagonal, sin Clean Architecture | Menos ceremonia de carpetas | No define explícitamente cómo organizar casos de uso ni la regla de dependencia interna entre dominio y aplicación | Se perdería la separación entre entidades y casos de uso, mezclando reglas de negocio con orquestación |
| Solo Clean Architecture, sin puertos explícitos (Hexagonal) | Menos interfaces que mantener | Sin puertos explícitos, es fácil que una capa "interna" termine llamando directamente a un SDK externo por conveniencia | No resolvería el requisito de poder sustituir ChromaDB/Anthropic sin tocar el dominio |
| Monolito modular sin arquitectura formal | Máxima velocidad para 21 horas de desarrollo disponibles | Alto riesgo de acoplamiento accidental bajo presión de tiempo; no defendible como "excelencia de diseño" ante un tribunal | Contradice el objetivo explícito del proyecto (el diseño de software es el criterio principal, no solo el funcionamiento) |

## Consecuencias

**Positivas:**
- Los casos de uso son testeables sin infraestructura real (dobles de prueba que implementan los mismos puertos).
- Cambiar de proveedor LLM, vector store o modelo de embeddings queda contenido en un adaptador nuevo, sin tocar el dominio.
- Es un argumento de diseño concreto y verificable en el código para la defensa de tesis, no una afirmación sin evidencia.

**Negativas / trade-offs aceptados:**
- Más archivos y más ceremonia (interfaces, inyección de dependencias) que un enfoque directo.
- Curva de disciplina: es fácil, bajo presión de tiempo, "atajar" e importar un SDK directamente en un caso de uso — se mitiga con revisión de código consciente durante la implementación.

## Cómo se ajusta a las restricciones del proyecto

El costo adicional de definir puertos e interfaces es pequeño en tiempo absoluto (se paga una vez, al diseñar cada puerto) y se recupera en mantenibilidad y en testabilidad sin infraestructura real — relevante cuando no hay tiempo para levantar entornos de prueba complejos repetidamente. No afecta el alcance funcional definido por el asesor: es una decisión de organización interna del código.
