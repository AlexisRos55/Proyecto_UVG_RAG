# Diagramas del protocolo

Fuentes Mermaid de las Figuras 4 a 7 y, junto a cada una, su versión exportada en PNG (para Word) y SVG.

| Archivo | Figura | Tipo de diagrama Mermaid | Exportado |
|---|---|---|---|
| `architecture.mmd` | 1. Arquitectura hexagonal del prototipo | `block-beta` | `architecture.{png,svg}` |
| `deployment.mmd` | 2. Arquitectura de despliegue con Docker Compose | `flowchart LR` | `deployment.{png,svg}` |
| `ingestion.mmd` | 3. Pipeline de ingesta documental | `flowchart TB` | `ingestion.{png,svg}` |
| `flow.mmd` | 4. Flujo de atención de una consulta | `flowchart TB` | `flow.{png,svg}` |

Cada `.mmd` empieza con un comentario que indica de qué archivos del código sale cada elemento. Si el código cambia, actualiza el diagrama y vuelve a exportarlo.

## Qué archivo insertar en Word

Usa el **PNG**. Se exportó a escala 3 (entre 2900 y 5700 px de ancho), suficiente para imprimir a 300 ppp al ancho de una página carta.

No insertes el SVG en Word. Mermaid escribe el texto de los nodos como HTML embebido (`foreignObject`), que Word no dibuja: la figura aparecería con las cajas vacías. El SVG sirve para verlo en un navegador o para editarlo en Inkscape o Illustrator.

## Cómo volver a exportar

Opción sin instalar nada: pega el contenido del `.mmd` en <https://mermaid.live>, comprueba el dibujo y descárgalo como PNG.

Opción reproducible, con la CLI de Mermaid (requiere Node.js; las exportaciones incluidas se generaron con `@mermaid-js/mermaid-cli` 11, Mermaid 11.17):

```bash
npm install -g @mermaid-js/mermaid-cli
cd docs/thesis/diagrams
mmdc -i architecture.mmd -o architecture.png -w 1900 -s 3 -b white
mmdc -i deployment.mmd   -o deployment.png            -w 1500 -s 3 -b white
mmdc -i ingestion.mmd    -o ingestion.png      -w 1500 -s 3 -b white
mmdc -i flow.mmd         -o flow.png        -w 1500 -s 3 -b white
```

Si `mmdc` no encuentra un navegador, crea un archivo `puppeteer.json` con `{"executablePath": "<ruta a Google Chrome>"}` y añade `-p puppeteer.json`.

## Convenciones visuales

Las mismas en los cuatro diagramas, para que se lean como un conjunto:

| Elemento | Color | Uso |
|---|---|---|
| Verde institucional oscuro `#004533` | relleno | Puertos del dominio y la única llamada al modelo |
| Verde institucional `#008c36` | borde | Capa de aplicación, contenedores, citación |
| Ámbar `#b7791f` | borde | Servicios externos, abstenciones y errores |
| Azul `#3b6ea8` | borde | Frontend, vías de entrada y decisiones |
| Gris | borde | Actores, respuestas sin el modelo, mantenimiento |
| Línea punteada | — | Artefactos (configuración, reporte) y caminos de error |

Los verdes son los del manual de identidad que usa el frontend (`--uvg-green-protocol` y `--uvg-green-institutional` en `frontend/src/index.css`). La fuente es Arial: una sans serif se lee mejor que Times New Roman (la del cuerpo del protocolo) cuando la figura se reduce al ancho de la página, y además distingue el texto de las figuras del texto corrido. Los textos van en español, salvo los nombres de clases y archivos, que se dejan como están en el código para que el lector pueda buscarlos.
