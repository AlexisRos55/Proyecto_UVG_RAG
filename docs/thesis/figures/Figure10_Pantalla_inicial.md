# Figura 10. Pantalla inicial del asistente

| Campo | Valor |
|---|---|
| Número | Figura 10 |
| Nombre | Pantalla inicial del asistente |
| Tipo | Captura de pantalla |
| Archivo | `docs/thesis/figures/capturas/Figura10_pantalla_inicial.png` |
| Ubicación | Anexo E; se cita en VIII.D.4 |
| Ruta del prototipo | `http://localhost:5173/chat` con una cuenta de estudiante sin mensajes |
| Estado | **Capturada** el 10 de octubre de 2026 con `tools/capture_figures.cjs` |

## Objetivo

Presentar la interfaz principal tal como la encuentra un estudiante al entrar: panel lateral, cabecera con el estado de conexión, mensaje de bienvenida, sugerencias de preguntas y compositor. Respalda VI.K (visibilidad del estado del sistema, sugerencias en la pantalla inicial, sistema de diseño propio) y VIII.D.4.

## Qué debe mostrar

- **Pantalla**: chat en escritorio, sin mensajes.
- **Usuario**: la cuenta de estudiante de demostración que crea el script (`demo.tesis…@uvg.edu.gt`, cuenta ficticia creada por el script); su correo aparece al pie del panel lateral y la pantalla saluda «Hola, Demo.».
- **Estado**: conversación vacía, «En línea» en la cabecera y el compositor vacío y sin foco.
- **Elementos visibles**: botón «Nueva conversación», lista de conversaciones vacía (sin el enlace «Documentos oficiales», que solo ve el administrador), mensaje «Bienvenido al Asistente Inteligente UVG», el subtítulo («Pregunta por becas y ayudas financieras, grupos estudiantiles, admisión, el calendario académico o la oferta académica del campus»), las cuatro sugerencias y el compositor.

## Sugerencias de la pantalla inicial (resuelto)

Las sugerencias y el subtítulo originales venían del corpus de ejemplo («seguro estudiantil», «requisitos de graduación», «reglamento de inscripción») y llevaban a abstenciones. Se reemplazaron por cuatro preguntas que el corpus oficial sí responde, una por documento: ayudas financieras, creación de un club, pasos de primer ingreso y costo de los cursos de inglés. Las cuatro se comprobaron contra el sistema en ejecución: responden con fuentes y confianza alta. La captura se tomó después del cambio.

## Cómo capturarla

| Parámetro | Valor |
|---|---|
| Resolución | 1440 × 900, DPR 2 → 2880 × 1800 px |
| Relación de aspecto | 16:10 |
| Modo | Claro |
| Zoom | 100 % |
| Datos personales | Solo el correo ficticio de demostración; nunca un correo real |
| Momento | Al terminar la animación de entrada, unos 2 s después de cargar |

Pasos: [guía de capturas, Figura 10](../capture_guide.md#figura-10--pantalla-inicial).

**Qué evitar**
- Una cuenta con mensajes previos.
- El cursor sobre una sugerencia (aparece la flecha y el resaltado).
- El aviso «Sin conexión con el servidor».

## Pie de figura

> Figura 10. Pantalla inicial del asistente. Elaboración propia con base en el prototipo desarrollado.

## Referencia dentro del texto

Insertada en el protocolo (VIII.D.4, después del punto 4):

> La Figura 10 (Anexo E) muestra la pantalla inicial del asistente. Además del panel lateral y del compositor de mensajes, la interfaz ofrece sugerencias de preguntas para iniciar la consulta e indica en la cabecera si la conexión con el servidor está activa, conforme al principio de visibilidad del estado del sistema descrito en el marco teórico.
