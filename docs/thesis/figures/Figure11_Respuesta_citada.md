# Figura 11. Respuesta fundamentada con citación de la fuente

| Campo | Valor |
|---|---|
| Número | Figura 11 |
| Nombre | Respuesta fundamentada con citación de la fuente |
| Tipo | Captura de pantalla |
| Archivo | `docs/thesis/figures/capturas/Figura11_respuesta_citada.png` |
| Ubicación | Anexo E; se cita en VIII.D.4 (y desde VIII.C.9) |
| Ruta del prototipo | `http://localhost:5173/chat` con la cuenta de estudiante de demostración |
| Estado | **Capturada** el 10 de octubre de 2026 con `tools/capture_figures.cjs`  · 2880 × 2370 px (alto ampliado para incluir las fuentes) |

## Objetivo

Es la figura central del documento: muestra el resultado del objetivo específico 2. Una pregunta en lenguaje natural recibe una respuesta redactada exclusivamente con la normativa y acompañada de su fuente exacta: documento, artículo y página.

## Qué debe mostrar

- **Pantalla**: chat en escritorio.
- **Usuario**: `demo.tesis…@uvg.edu.gt` (cuenta ficticia creada por el script), en la misma conversación vacía de la Figura 10.
- **Conversación**: un único turno.
  - Pregunta: **«¿Qué tipos de ayuda financiera ofrece la universidad?»** (Q01 del banco de referencia).
  - Respuesta esperada: tres tipos de ayuda.
    - la **beca**, que no es reembolsable;
    - el **crédito educativo**, que el estudiante reembolsa a la universidad;
    - el **subsidio por auxiliatura**, que se acredita al ser nombrado auxiliar.
  - Bloque de fuentes obtenido («Fuentes · 2»):
    - **Reglamento de ayudas financieras**, «Capítulo 1 · Artículo 7. Tipos de ayudas financieras · págs. 4–5»;
    - **Reglamento de ayudas financieras**, «Capítulo III · Artículo 12. Horas Beca · pág. 6», que respalda el compromiso de horas de servicio de los becados.
  - Etiqueta de confianza: «Confianza alta».
- **Elementos visibles**: la pregunta, la respuesta completa en Markdown (lista con negritas), el bloque «Fuente» con título y ubicación, la etiqueta de confianza y el compositor.

> La respuesta exacta la redacta el modelo y no puede fijarse de antemano. Lo que debe cumplirse es que la respuesta nombre los tres tipos de ayuda y que la fuente cite el artículo 7. Si cita otro artículo o no muestra sección ni página, no uses la captura y revisa la indexación (guía, paso 0).

**Alternativa**, si quieres mostrar además el formato de tabla: «¿Qué diferencia hay entre una beca y un crédito educativo?» (Q02). La respuesta debe salir como comparación, citando también el artículo 7.

## Cómo capturarla

| Parámetro | Valor |
|---|---|
| Resolución | 1440 × 900, DPR 2 → 2880 × 1800 px; si la respuesta no cabe, usa «Capture full size screenshot» y recorta |
| Relación de aspecto | 16:10 preferida; se admite más alta si es necesario para incluir el bloque «Fuente» |
| Modo | Claro |
| Zoom | 100 % |
| Datos personales | Solo el correo ficticio de demostración |
| Momento | Cuando la respuesta esté completa y el bloque «Fuente» haya aparecido |

Pasos: [guía de capturas, Figura 11](../capture_guide.md#figura-11--respuesta-con-citación).

**Qué evitar**
- Cortar el bloque «Fuente»: es el objeto de la figura.
- Respuestas con la advertencia de confianza media o baja (vuelve a preguntar en una conversación nueva solo si no aparece «Confianza alta»).
- Capturar mientras se ve el indicador «pensando».

## Pie de figura

> Figura 11. Respuesta fundamentada con citación de la fuente. Elaboración propia con base en el prototipo desarrollado.

## Referencia dentro del texto

Insertada en el protocolo (VIII.D.4, después del punto 4):

> La Figura 11 (Anexo E) ilustra una respuesta fundamentada. Ante la pregunta sobre los tipos de ayuda financiera, el asistente enumera la beca, el crédito educativo y el subsidio por auxiliatura, y debajo de la respuesta identifica el documento, el artículo y la página que la respaldan, de modo que el estudiante puede verificar la información en el reglamento oficial. La etiqueta de confianza corresponde al nivel autoinformado por el modelo durante la verificación.

En VIII.C.9 se añadió además: «La Figura 11 (Anexo E) muestra cómo se presenta la cita en la interfaz.»
