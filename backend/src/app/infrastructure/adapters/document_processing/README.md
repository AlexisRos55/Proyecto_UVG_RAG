# infrastructure/adapters/document_processing

Implementación concreta de `DocumentTextExtractorPort` y el servicio de chunking.

Previsto:
- `PyMuPDFExtractorAdapter`: extracción de texto crudo de PDFs institucionales.
- `RegexTextCleaner`: limpieza de artefactos de extracción (encabezados, pies de página, saltos de línea espurios) según lo especificado por el asesor.
- `FixedSizeChunkingService`: división en fragmentos de tamaño fijo con overlap de 100 caracteres (ver [ADR-0009](../../../../../../docs/adr/0009-chromadb-vector-store.md)).

Cada responsabilidad vive en su propia clase (extracción ≠ limpieza ≠ chunking), aplicando el Principio de Responsabilidad Única en vez de un único módulo "procesar documento".
