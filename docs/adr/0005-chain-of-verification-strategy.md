# ADR-0005: Chain-of-Verification en una sola llamada, con puerto abierto a pipeline futuro

**Estado:** Aceptado

**Fecha:** 2026-09-02

## Contexto

El asesor exige que el agente use una estrategia de Chain-of-Verification para forzar que la respuesta se construya exclusivamente a partir de los fragmentos recuperados. Existen dos formas típicas de implementar esto: (a) una única llamada al LLM donde el propio prompt le pide generar la respuesta y auto-evaluar su fundamentación en el mismo turno (usando salida estructurada), o (b) un pipeline de múltiples llamadas independientes (generar → verificar con una llamada separada, posiblemente con un prompt distinto y más estricto → responder final). La opción (b) es más rigurosa pero duplica o triplica el consumo de tokens y la latencia por consulta — y ambas son variables críticas del proyecto: la latencia es una métrica formal de evaluación (RAGAS) y el presupuesto de API es personal y limitado (NFR-02).

## Decisión

Se implementa Chain-of-Verification como una única llamada al LLM con salida estructurada (el modelo devuelve, en la misma respuesta, tanto la respuesta al estudiante como un campo de verificación/confianza indicando si cada afirmación está respaldada por el contexto recuperado). El dominio expone un puerto `VerificationStrategyPort` con esta implementación (`SingleCallVerificationAdapter`) como la única implementada en esta versión; el puerto queda diseñado para admitir en el futuro un `MultiCallVerificationAdapter` sin modificar `AnswerStudentQueryUseCase`.

## Alternativas consideradas

| Alternativa | Ventajas | Desventajas | Por qué se descartó (o difirió) |
|---|---|---|---|
| Pipeline multi-llamada (generar + verificar por separado) | Cada etapa es inspeccionable y auditable de forma independiente; en teoría mejora la fidelidad al forzar una segunda pasada crítica sobre la respuesta | Duplica/triplica tokens y latencia por consulta; con presupuesto personal limitado y latencia como métrica de evaluación, este costo es directamente contrario a dos restricciones explícitas del proyecto | Se difiere como extensión futura (`MultiCallVerificationAdapter`), no se descarta conceptualmente — el puerto ya está preparado para ella |
| Ninguna verificación explícita (confiar solo en temperatura 0 + prompt estricto) | Mínimo costo y latencia | No cumple el requisito explícito del asesor de aplicar Chain-of-Verification | Incumple un requisito funcional obligatorio (FR-10) |
| Single-call con salida estructurada (elegida) | Una sola llamada al LLM: mismo orden de costo y latencia que una generación simple; cumple el requisito funcional de verificación; la salida estructurada (JSON/tool use) permite a la aplicación decidir programáticamente si mostrar la respuesta o abstenerse, sin depender de que el estudiante "lea entre líneas" | Verificación menos rigurosa que una segunda llamada independiente, porque es el mismo modelo, en el mismo turno, evaluando su propia salida | — |

## Consecuencias

**Positivas:**
- Cumple el requisito funcional del asesor (Chain-of-Verification) sin duplicar el costo por consulta.
- La arquitectura no queda atada a esta decisión: si la evaluación con RAGAS muestra fidelidad insuficiente, se puede implementar `MultiCallVerificationAdapter` sin tocar el caso de uso que lo consume (Open/Closed Principle en la práctica).

**Negativas / trade-offs aceptados:**
- La auto-verificación en una sola llamada es, por diseño, menos estricta que una verificación independiente — se acepta este riesgo de fidelidad a cambio de mantener costo y latencia bajo control, y se documenta como riesgo abierto en `09-risk-register.md`.

## Cómo se ajusta a las restricciones del proyecto

Esta es la decisión de mayor impacto directo sobre NFR-02 (costo) y NFR-01 (latencia): reduce a la mitad o a un tercio el número de llamadas al LLM frente a un pipeline multi-llamada, sin sacrificar el cumplimiento del requisito funcional del asesor. Es coherente con el presupuesto personal limitado y con el plazo de 3 semanas, que no permite iterar sobre una arquitectura de verificación más compleja dentro del MVP.
