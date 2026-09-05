# ADR-0006: Modelo LLM configurable por entorno, Claude Haiku 4.5 por defecto

**Estado:** Aceptado

**Fecha:** 2026-09-02

## Contexto

El documento original del asesor especifica "Claude 3.5 Sonnet". Esa versión corresponde a una generación de modelos de Anthropic anterior a la disponible actualmente; para el desarrollo directo mediante el SDK de Anthropic (ver [ADR-0002](0002-no-langchain-direct-anthropic-sdk.md)) se necesita fijar un modelo vigente. Además, el presupuesto de API es personal y limitado (ver Project Charter, sección 5), lo que hace del costo por token un criterio de selección tan relevante como la calidad de respuesta.

## Decisión

El modelo por defecto es Claude Haiku 4.5, seleccionado por su eficiencia de costo y latencia para una tarea de Q&A acotada a un dominio documental cerrado. El nombre del modelo **nunca se hardcodea**: se lee desde la variable de entorno `ANTHROPIC_MODEL` mediante `pydantic-settings`, de modo que cambiar a Claude Sonnet 5 (o cualquier modelo futuro) no requiere modificar código, solo configuración.

## Alternativas consideradas

| Alternativa | Ventajas | Desventajas | Por qué se descartó (o quedó como opción configurable) |
|---|---|---|---|
| Claude Sonnet 5 | Mayor capacidad de razonamiento, potencialmente mejor autoevaluación en el Chain-of-Verification de una sola llamada | Mayor costo y latencia por token que Haiku 4.5 | No se descarta: sigue disponible como valor de configuración (`ANTHROPIC_MODEL=claude-sonnet-5`) si la evaluación con RAGAS muestra que Haiku 4.5 no alcanza fidelidad suficiente |
| Claude Opus 5 | Máxima capacidad disponible | Costo y latencia significativamente mayores, sin beneficio claro para un caso de uso de Q&A acotado; podría perjudicar la comparación de latencia contra la atención manual que pide el asesor | Sobre-dimensionado para este caso de uso; descartado como valor por defecto |
| Un LLM local (self-hosted, open-weight) para eliminar el envío de datos a un tercero | Resolvería por completo la tensión de privacidad descrita en NFR-07 | Requiere cómputo (GPU) y esfuerzo de ingeniería incompatibles con el presupuesto personal y el plazo de 3 semanas; calidad típicamente inferior a Claude en tareas de instrucción estricta como Chain-of-Verification | Descartado para esta versión; la tensión de privacidad queda documentada como riesgo aceptado (NFR-07, R-01 en `09-risk-register.md`) en vez de resuelta por completo |
| Modelo hardcodeado en el código del adaptador | Ninguna ventaja real sobre la configuración por entorno | Cualquier cambio de modelo (por deprecación de Anthropic, por resultados de evaluación, o por cambio de presupuesto) requeriría modificar y redesplegar código | Contradice NFR-03 (mantenibilidad) y el principio de configuración externa (12-factor app) |

## Consecuencias

**Positivas:**
- El sistema puede adaptarse a cambios en el catálogo de modelos de Anthropic (incluida una eventual deprecación de un modelo) sin tocar código, solo la variable de entorno.
- Permite comparar empíricamente Haiku 4.5 vs. Sonnet 5 durante la evaluación con RAGAS simplemente cambiando la configuración entre corridas.

**Negativas / trade-offs aceptados:**
- Haiku 4.5, al ser el modelo más económico de la familia vigente, podría rendir peor que Sonnet 5 en la métrica de fidelidad de RAGAS — se acepta este riesgo como punto de partida y se deja documentado que el cambio de modelo es una mitigación de un solo valor de configuración, no un cambio de arquitectura.

## Cómo se ajusta a las restricciones del proyecto

Responde directamente a NFR-02 (minimizar costo de operación) sin cerrar la puerta a mejorar calidad más adelante. También resuelve el riesgo de que el modelo literal mencionado por el asesor (Claude 3.5 Sonnet) esté deprecado o sin soporte activo al momento de la implementación o la defensa.

## Addendum (fase de implementación, 2026-09-04): el SDK vigente eliminó `temperature`

Durante la implementación se descubrió, inspeccionando directamente el código fuente instalado (no por documentación externa), que el SDK oficial de Anthropic para Python en su línea 1.x (`anthropic>=1.0`, la versión "vigente" que esta ADR eligió usar) **eliminó por completo `temperature` como parámetro tipado** de `messages.create()`. Esto afecta directamente a FR-09 ("temperatura 0.0, decodificación determinista"), un requisito que proviene del asesor, no de esta ADR.

Se consultó al equipo (Project Charter: ninguna decisión que module un requisito del asesor se toma unilateralmente) y se decidió: mantener el SDK 1.x vigente y enviar `temperature: 0.0` mediante el parámetro `extra_body` del cliente, que reenvía campos crudos al cuerpo de la petición HTTP sin pasar por la validación tipada del SDK (ver `AnthropicLLMAdapter.complete`). Esto se verificó parcialmente: una llamada real con una API key inválida devolvió `401 authentication_error` en vez de un error de "campo no reconocido", lo que indica que el servidor acepta el campo y llega hasta la validación de credenciales — evidencia indirecta pero razonable de que el mecanismo funciona. No se pudo confirmar con una respuesta exitosa completa por no contar con una API key real durante la implementación; **el equipo debe validarlo con una key real antes de la defensa** y, si el servidor llegara a rechazar el campo, evaluar entonces la alternativa de fijar `anthropic<1.0` (línea 0.x, con `temperature` tipado y soportado, pero ya no actualizada activamente por Anthropic).
