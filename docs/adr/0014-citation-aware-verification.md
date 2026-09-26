# ADR-0014: Verificación con citas precisas y cobertura explícita

**Estado:** Aceptado — extiende [ADR-0005](0005-chain-of-verification-strategy.md) sin cambiar su decisión central (una sola llamada).

**Fecha:** 2026-09-24

## Contexto

Tras ADR-0005 la salida estructurada del modelo tenía un único booleano `is_grounded` que mezclaba dos preguntas distintas: *¿todo lo que dice la respuesta está respaldado?* (fidelidad) y *¿la respuesta contesta todo lo preguntado?* (cobertura). Una respuesta fiel pero incompleta se descartaba entera. Además, se citaban **todos** los documentos recuperados, incluidos los que no aportaron nada, y sin artículo ni página (ADR-0011).

## Decisión

1. Cada fragmento del prompt se rotula con su documento y ubicación: `[3] Reglamento de ayudas financieras — Capítulo IV… · Artículo 18. Condiciones (pág. 11)`.
2. La salida estructurada añade `coverage` (`complete` / `partial` / `none`) y `cited_fragments` (los pasajes en que el modelo dice apoyarse).
3. El caso de uso cita solo esos pasajes, como `SourceReference` con título, apartado y páginas; una respuesta parcial se muestra con confianza como máximo media; `none` o `is_grounded=false` producen abstención, que ahora indica dónde está la normativa más cercana.
4. Las citas estructuradas se persisten (`messages.sources`, JSONB, migración aditiva) para que el historial muestre lo mismo que la respuesta en vivo. La API solo **añade** campos opcionales.

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| Marcadores de cita en el texto («[3]») | Ensucian la prosa que el estudiante lee; la cita va en la tarjeta de fuente |
| Verificación en una segunda llamada (`MultiCallVerificationAdapter`) | Duplica tokens y latencia (ADR-0005); sigue disponible por el puerto |
| Citar todo lo recuperado | Presenta como fuente material que no sustenta la respuesta |

## Consecuencias

**Positivas:** citas verificables (artículo y página); respuestas parciales útiles en lugar de abstenciones; la confianza refleja la cobertura.

**Negativas:** `cited_fragments` es autoinformado por el modelo, como la confianza; si falta o es inválido se vuelve al comportamiento anterior (citar todo lo entregado). El prompt de sistema cambia y el cambio queda registrado en `docs/11-reproducibility.md`.

## Cómo se ajusta a las restricciones del proyecto

Sigue siendo exactamente una llamada por consulta (US-2.2). El aumento de tokens de salida es de unas decenas por respuesta y queda compensado por la reducción del contexto de ADR-0012.
