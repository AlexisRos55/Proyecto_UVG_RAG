# Material gráfico del Trabajo de Graduación

Figuras, diagramas y capturas del protocolo *Diseño y desarrollo de un prototipo de asistente virtual basado en arquitectura RAG con pruebas de recuperación, relevancia y latencia para la consulta de normativas en UVG Altiplano*, generados a partir del código de este repositorio.

## Qué hay aquí

```
docs/thesis/
├── README.md               este archivo
├── figures_index.md        las 11 figuras, ubicación en el protocolo, discrepancias y cobertura
├── capture_guide.md        cómo producir las capturas (automática o manual)
├── diagrams/               Figuras 4 a 7: fuente Mermaid + PNG (para Word) + SVG
│   ├── architecture.*      Figura 4 · Arquitectura hexagonal del prototipo
│   ├── deployment.*        Figura 5 · Arquitectura de despliegue con Docker Compose
│   ├── ingestion.*         Figura 6 · Pipeline de ingesta documental
│   ├── flow.*              Figura 7 · Flujo de atención de una consulta
│   └── README.md           cómo volver a exportar y convenciones visuales
├── figures/                una ficha por figura: objetivo, contenido, pie y texto para citar
│   ├── Figure04_… a Figure14_…
│   └── capturas/           Figuras 8 a 14 en PNG + capture_report.json
└── tools/
    └── capture_figures.cjs captura automática de las Figuras 8 a 14
```

## Protocolo con el material insertado

El material ya está insertado en la versión oficial del protocolo (la de Descargas, del 10 de octubre de 2026). Hay tres archivos en `~/Downloads/`:

| Archivo | Para qué |
|---|---|
| `Protocolo_Alexis_Rosales_con_figuras_revision.docx` | Revisión con el asesor: figuras, citas y correcciones como control de cambios (autor «Claude») |
| `Protocolo_Alexis_Rosales_con_figuras.docx` | Entrega: los mismos cambios ya aceptados |
| `Protocolo_Alexis_Rosales_con_figuras.pdf` | Vista previa exportada con Microsoft Word (80 páginas) |

No se guardan en el repositorio, que es público.

## Cómo insertar las figuras en otro documento Word

1. **Inserta las imágenes.** Diagramas: el `.png` de `diagrams/`. Capturas: el `.png` de `figures/capturas/`. Usa siempre el PNG, porque Word no dibuja el texto de los SVG de Mermaid.
2. **Agrega el pie.** Debajo de cada imagen, con **Referencias → Insertar título**, etiqueta «Figura». Copia el texto del pie de la ficha correspondiente.
3. **Pega el párrafo de referencia.** Cada ficha indica en qué sección va.
4. **Reordena los anexos.** Intercambia el orden de los anexos C y D del índice preliminar ([figures_index.md, sección 3](figures_index.md#3-orden-de-los-anexos)).

## Estado

| Figuras | Estado |
|---|---|
| 4 a 7 (diagramas) | Insertadas en el protocolo (anexos C y D) |
| 8, 9, 11, 12, 13 y 14 (capturas) | Insertadas en el protocolo (anexo E); tomadas el 10 de octubre de 2026 con el corpus oficial de 15 documentos |
| 10 (pantalla inicial) | Insertada, con las sugerencias corregidas |

Antes de dar por cerrado el documento, revisa también las decisiones de texto de [figures_index.md](figures_index.md), secciones 4 a 6.
