# Figura 6. Pipeline de ingesta documental

| Campo | Valor |
|---|---|
| Número | Figura 6 |
| Nombre | Pipeline de ingesta documental |
| Tipo | Diagrama de flujo (Mermaid) |
| Fuente | [`../diagrams/ingestion.mmd`](../diagrams/ingestion.mmd) |
| Archivo para el documento | `../diagrams/ingestion.png` |
| Ubicación | Anexo D (tras el intercambio); se cita en VIII.A |
| Orientación | Vertical, página completa |

## Objetivo

Respaldar el objetivo específico 1 y la Fase I: cómo un PDF se convierte en fragmentos vectorizados y consultables, por cualquiera de las tres vías de entrada, y cómo el sistema registra el estado del documento.

> **Depende de la decisión D1** del [índice](../figures_index.md#4-discrepancias-entre-el-protocolo-y-la-implementación). La figura representa la fragmentación **estructural** desplegada (600 caracteres por artículo), no la de tamaño fijo de 1000 caracteres que describe hoy el texto de VIII.A.4. Si el texto no se actualiza, la figura lo contradice.

## Qué debe mostrar

1. **Tres vías de entrada** que convergen en un mismo caso de uso: arranque del backend, panel administrativo (`POST /admin/documents`, solo PDF) y `scripts/ingest.py`.
2. **Registro** en la tabla `documents`, con estado «pendiente».
3. **Extracción** con PyMuPDF: texto por página, título y páginas.
4. **Limpieza estructural**: retiro del encabezado y las firmas repetidos y reconocimiento de capítulos, artículos, literales y secciones.
5. **Fragmentación estructural**: el artículo es la unidad, hasta 600 caracteres, con solapamiento de 100 y ancla de sección y páginas. Incluye la limpieza con expresiones regulares y la anotación de tablas.
6. **Vectorización** con all-MiniLM-L6-v2 (384 dimensiones).
7. **Indexación** en ChromaDB con metadatos y **sincronización** del índice BM25.
8. **Decisión** de estado: «indexado» (disponible sin reiniciar) o «error» con su mensaje.
9. **Mantenimiento**: reindexar o eliminar borra primero todos los fragmentos del documento.

## Cómo generarla

PNG exportado (2916 × 4044 px), al ancho del texto en una página propia.

## Pie de figura

> Figura 6. Pipeline de ingesta documental. Elaboración propia con base en el repositorio del proyecto.

## Referencia dentro del texto

Insertada en el protocolo (VIII.A, después del punto 6 («Vías de ingesta»)):

> La Figura 6 (Anexo D) integra estas etapas en un solo flujo. Las tres vías de ingesta convergen en el mismo caso de uso, que registra el documento como pendiente, lo procesa etapa por etapa y lo marca como indexado únicamente cuando todos sus fragmentos se han vectorizado y almacenado; si alguna etapa falla, el documento queda en estado de error con el mensaje correspondiente y no se ofrece al asistente información parcial.
