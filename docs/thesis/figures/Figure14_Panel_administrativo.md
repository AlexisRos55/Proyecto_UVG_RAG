# Figura 14. Panel administrativo de documentos

| Campo | Valor |
|---|---|
| Número | Figura 14 |
| Nombre | Panel administrativo de documentos |
| Tipo | Captura de pantalla |
| Archivo | `docs/thesis/figures/capturas/Figura14_panel_administrativo.png` |
| Ubicación | Anexo E; se cita en VIII.D.4 (y desde VII.B) |
| Ruta del prototipo | `http://localhost:5173/admin` con la cuenta administrativa |
| Estado | **Capturada** el 10 de octubre de 2026 con `tools/capture_figures.cjs` · página completa, 2880 × 3126 px; muestra «Indexados 15» |

## Objetivo

Respaldar el objetivo específico 1 («administrable desde la propia aplicación») y VII.B: el corpus activo son exactamente los 15 documentos oficiales, todos indexados, y el administrador puede cargar, buscar, reindexar y eliminar documentos sin reiniciar el servicio.

## Qué debe mostrar

- **Pantalla**: página «Documentos» del panel administrativo.
- **Usuario**: la cuenta administrativa configurada en `.env` (`DEFAULT_ADMIN_EMAIL`; por defecto, `admin@uvg.edu.gt`).
- **Datos**: la lista con **los 15 documentos oficiales**, cada uno con el estado «Indexado», y nada más:
  - **sin** `becas_y_beneficios.pdf`, `reglamento_estudiantil.pdf` ni `seguro_estudiantil.pdf`;
  - **sin** la segunda copia de «Administración de Empresas 2025».

  Los nombres se muestran con los acentos reparados (por ejemplo, «Educación Física», no «Educaci¢n F°sica»).
- **Elementos visibles**: título «Documentos», área de carga de PDF, buscador vacío, filas con nombre, estado y botones de reindexar y eliminar, y el botón para volver al asistente.

## Cómo capturarla

| Parámetro | Valor |
|---|---|
| Resolución | 1440 × 900, DPR 2 → 2880 × 1800 px; si no caben las 15 filas, usa «Capture full size screenshot» |
| Relación de aspecto | 16:10, o más alta si es necesario para mostrar las 15 filas |
| Modo | Claro |
| Zoom | 100 % |
| Datos personales | Ninguno (los documentos son institucionales y públicos para la sede) |
| Momento | Con la lista cargada y sin notificaciones (*toasts*) en pantalla |

Pasos: [guía de capturas, Figura 14](../capture_guide.md#figura-14--panel-administrativo).

**Qué evitar**
- Capturar antes de retirar el corpus ficticio y el duplicado (guía, paso 0): la figura contradiría VII.B.
- El diálogo «¿Eliminar este documento?» abierto.
- Una notificación «Documento reindexado» visible.

## Pie de figura

> Figura 14. Panel administrativo de documentos con el corpus oficial indexado. Elaboración propia con base en el prototipo desarrollado.

## Referencia dentro del texto

Insertada en el protocolo (VIII.D.4, después del punto 4):

> Por último, la Figura 14 (Anexo E) presenta el panel administrativo con los 15 documentos oficiales que conforman el corpus de la evaluación, todos en estado indexado. Desde este panel, el administrador carga nuevos documentos en formato PDF, consulta su estado de indexación, los reindexa o los elimina junto con sus fragmentos, sin necesidad de reiniciar el servicio.
