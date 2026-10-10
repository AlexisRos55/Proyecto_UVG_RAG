# Figura 13. Historial persistente de la conversación

| Campo | Valor |
|---|---|
| Número | Figura 13 |
| Nombre | Historial persistente de la conversación tras un nuevo inicio de sesión |
| Tipo | Captura de pantalla |
| Archivo | `docs/thesis/figures/capturas/Figura13_historial.png` (2880 × 2200 px) |
| Ubicación | Anexo E; se cita en VIII.D.4 |
| Estado | **Capturada** el 10 de octubre de 2026 con `tools/capture_figures.cjs` |

## Objetivo

Demostrar dos cosas:
- Las conversaciones de los usuarios registrados se guardan en PostgreSQL y se recuperan al volver a entrar (VI.F.3 y VIII.D.3).
- El asistente mantiene el hilo entre una pregunta y su seguimiento (memoria conversacional, VI.E.3).

## Por qué cambia respecto de la propuesta inicial

La lista inicial pedía «historial de conversaciones», en plural. Pero el backend conserva **una conversación activa por usuario**, y el botón «Nueva conversación» solo limpia la vista en el navegador. El panel lateral muestra, por tanto, una sola conversación bajo «Hoy». Una figura con varias conversaciones no puede obtenerse del sistema actual; esta figura muestra lo que sí existe (discrepancia D7 del [índice](../figures_index.md)).

## Qué muestra

- **Usuario**: la cuenta de demostración de las Figuras 10 y 11 (`demo.tesis…@uvg.edu.gt`, cuenta ficticia creada por el script), **después de cerrar sesión y volver a iniciarla**.
- **Panel lateral**: la conversación bajo «Hoy», seleccionada.
- **Conversación recuperada**: dos turnos escritos antes de cerrar sesión. El encuadre empieza en el segundo.
  1. «¿Qué tipos de ayuda financiera ofrece la universidad?»: es el turno de la Figura 11.
  2. **«¿Y en qué se diferencia la beca del crédito?»**: una pregunta elíptica que solo tiene sentido con el turno anterior. La respuesta explica que la beca no se reembolsa y el crédito sí, con una tabla comparativa (reembolso, base de otorgamiento, cobertura máxima y requisito de firma).
- Las fuentes del segundo turno quedan debajo del encuadre: Artículos 7, 22 y 25 del Reglamento de Ayudas Financieras.

## Descripción académica

La captura se tomó inmediatamente después de un nuevo inicio de sesión: la conversación no proviene de la memoria del navegador, sino del historial almacenado en la base de datos relacional. La segunda pregunta omite su objeto («¿y en qué se diferencia…?»); la capa de comprensión del turno la interpretó a partir de la anterior y el asistente eligió el formato de comparación.

## Si se vuelve a capturar

- No pulses «Nueva conversación» en esa cuenta: oculta los mensajes anteriores en ese navegador.
- Recargar la página no sirve: hay que cerrar sesión e iniciarla de nuevo para demostrar la persistencia.

## Pie de figura

> Figura 13. Historial persistente de la conversación tras un nuevo inicio de sesión. Elaboración propia con base en el prototipo desarrollado.

## Referencia dentro del texto

Insertada en el protocolo (VIII.D.4, después del punto 4):

> La Figura 13 (Anexo E) muestra la conversación de un estudiante recuperada tras cerrar e iniciar sesión de nuevo. Los mensajes se conservan en la base de datos relacional, y la segunda pregunta, formulada de forma elíptica («¿y en qué se diferencia la beca del crédito?»), se interpretó a partir del tema de la anterior y se respondió con una tabla comparativa. En el prototipo, cada usuario mantiene una única conversación activa; la gestión de varias conversaciones independientes queda como trabajo futuro.
