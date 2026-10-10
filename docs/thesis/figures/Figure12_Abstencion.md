# Figura 12. Abstención ante una consulta sin respaldo documental

| Campo | Valor |
|---|---|
| Número | Figura 12 |
| Nombre | Abstención ante una consulta sin respaldo documental |
| Tipo | Captura de pantalla |
| Archivo | `docs/thesis/figures/capturas/Figura12_abstencion.png` (2880 × 1800 px) |
| Ubicación | Anexo E; se cita en VIII.D.4 (y desde VIII.C.8) |
| Estado | **Capturada** el 10 de octubre de 2026 con `tools/capture_figures.cjs` |

## Objetivo

Mostrar el comportamiento que distingue al prototipo de un chatbot genérico: ante una pregunta plausible que el corpus no responde, el asistente declara que no encontró normativa en lugar de inventar un dato. Respalda VI.B.6, VIII.C.8 y la métrica de exactitud de abstención (Cuadro 5).

## Qué muestra

- **Usuario**: una cuenta de demostración propia (`demo.abstencion…@uvg.edu.gt`) sin mensajes previos. Debe ser otra cuenta porque el backend guarda una sola conversación por usuario y el tema en foco de otra conversación influiría en la interpretación.
- **Pregunta**: «¿Cuál es el horario de atención de la biblioteca?» (Q31, una de las 10 preguntas fuera del corpus). El folleto general menciona la biblioteca, pero ningún documento indica su horario.
- **Respuesta obtenida**: la abstención «sin normativa», que ocurre **antes** de llamar al modelo porque la recuperación no encontró evidencia suficiente:
  > No logré relacionar tu mensaje con la normativa oficial. Si me lo cuentas con otras palabras (qué quieres hacer o qué te preocupa), lo busco de nuevo.
  >
  > También puedo orientarte con las becas y ayudas financieras, el calendario académico o la admisión. Por ejemplo: «¿Qué becas hay para estudiantes del Altiplano?»
- Debajo, la nota de la interfaz: «No encontré normativa que respalde una respuesta a esto».
- Sin bloque «Fuente»: la abstención no cita documentos.

## Descripción académica

La captura corresponde al primer punto de abstención del flujo de la Figura 7. La recuperación híbrida no encontró ningún fragmento que superara los umbrales de evidencia, por lo que el asistente se abstuvo sin consumir una llamada al modelo de lenguaje. La guía conversacional reformula la abstención como una invitación a precisar la consulta y ofrece temas que el corpus sí cubre.

## Si se vuelve a capturar

- El texto exacto puede variar, porque la guía conversacional adapta la respuesta. Lo que debe cumplirse es que sea una abstención, sin fuentes y sin ningún horario.
- Si el asistente da un horario, es una alucinación: no uses la captura, regístrala como hallazgo y usa la pregunta de respaldo «¿Cómo pido una constancia de estudios y cuánto cuesta?» (Q40). El script lo hace automáticamente y lo anota en `capture_report.json`.
- Evita la pregunta de los buses (Q38): puede tratarse como tema fuera de dominio, que es una habilidad local y no una abstención.

## Pie de figura

> Figura 12. Abstención ante una consulta sin respaldo documental. Elaboración propia con base en el prototipo desarrollado.

## Referencia dentro del texto

Insertada en el protocolo (VIII.D.4, después del punto 4):

> La Figura 12 (Anexo E) muestra el comportamiento opuesto. Ante una pregunta plausible cuya respuesta no figura en el corpus, como el horario de atención de la biblioteca, la recuperación no encuentra evidencia suficiente y el asistente se abstiene antes de consultar al modelo de lenguaje: en lugar de proponer un horario, declara que no logró relacionar la consulta con la normativa oficial, invita a reformularla y sugiere temas que el corpus sí cubre, sin citar ninguna fuente.
