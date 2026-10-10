# Figura 9. Consulta en modo invitado

| Campo | Valor |
|---|---|
| Número | Figura 9 |
| Nombre | Consulta en modo invitado |
| Tipo | Captura de pantalla |
| Archivo | `docs/thesis/figures/capturas/Figura09_modo_invitado.png` |
| Ubicación | Anexo E; se cita en VIII.D.2 |
| Ruta del prototipo | `http://localhost:5173/chat`, tras pulsar «Continuar como invitado» |
| Estado | **Capturada** el 10 de octubre de 2026 con `tools/capture_figures.cjs` |

## Objetivo

Mostrar que una persona sin cuenta institucional puede consultar la normativa y recibir una respuesta con su fuente, y que la interfaz le indica que está en una sesión de visitante. Respalda la justificación (acceso más allá del horario y de la comunidad universitaria), VII.A y VIII.D.2.

## Qué debe mostrar

- **Pantalla**: chat en escritorio, con panel lateral.
- **Usuario**: sesión de invitado. El pie del panel lateral dice «Invitado» y la cabecera muestra la insignia «Invitado».
- **Conversación**: una sola pregunta y su respuesta.
  - Pregunta: **«¿Hasta cuándo puedo pagar la cuota de octubre sin recargo?»** (Q16 del banco).
  - Respuesta obtenida: «Hasta el 17 de octubre de 2026 puedes pagar la cuota de estudios de octubre sin recargo.» Fuente: **Calendario Académico · págs. 4–5**, con «Confianza alta».
- **Elementos visibles**: insignia «Invitado», indicador «En línea», la respuesta, el bloque «Fuente», el aviso inferior «Estás utilizando Alexis como visitante. Algunas funciones están disponibles únicamente para usuarios institucionales.» y el compositor vacío.
- **No visible**: enlace al panel administrativo (no existe para invitados).

## Cómo capturarla

| Parámetro | Valor |
|---|---|
| Resolución | 1440 × 900, DPR 2 → 2880 × 1800 px |
| Relación de aspecto | 16:10 |
| Modo | Claro |
| Zoom | 100 % |
| Datos personales | Ninguno: la sesión es anónima |
| Momento | Cuando la respuesta esté completa y el indicador de escritura haya desaparecido |

Pasos: [guía de capturas, Figura 9](../capture_guide.md#figura-9--modo-invitado).

**Qué evitar**
- Usar una sesión de invitado que ya tenga mensajes: el panel mostraría la conversación anterior. Abre siempre una sesión nueva.
- Capturar si la respuesta es «No pude completar la respuesta en este momento» (falta crédito de API o falla la red).

## Pie de figura

> Figura 9. Consulta en modo invitado. Elaboración propia con base en el prototipo desarrollado.

## Referencia dentro del texto

Insertada en el protocolo (VIII.D.2, después del punto 2):

> La Figura 9 (Anexo E) muestra una consulta realizada en modo invitado. El visitante recibe la misma respuesta fundamentada y la misma cita que un estudiante registrado; la interfaz identifica la sesión como de invitado y le recuerda que algunas funciones están reservadas a los usuarios institucionales.
