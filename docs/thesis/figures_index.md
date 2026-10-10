# Índice de figuras del protocolo

Material gráfico del protocolo *Diseño y desarrollo de un prototipo de asistente virtual basado en arquitectura RAG… en UVG Altiplano* (versión oficial `Protocolo_Alexis_Rosales_actualizado.docx` de la carpeta Descargas, del 10 de octubre de 2026, 00:59), contrastado con el código del repositorio en la rama `feat-modo-invitado`.

**Estado:** todo el material está insertado en `~/Downloads/Protocolo_Alexis_Rosales_con_figuras.docx` (versión limpia) y en `~/Downloads/Protocolo_Alexis_Rosales_con_figuras_revision.docx` (los mismos cambios como control de cambios, autor «Claude»). Esos archivos no se guardan en el repositorio porque es público y el protocolo se mantiene fuera a propósito (`.gitignore`).

## 1. Lista definitiva de figuras

Las Figuras 1 a 3 ya existían en el protocolo: son los gráficos de la encuesta del capítulo IX (canal de consulta, tiempo de atención manual y distribución de respuestas por ítem) y no se modificaron. El material gráfico del sistema continúa la numeración en el orden en que aparece en el documento, en los anexos C, D y E (Figuras 4 a 14). En el cuerpo, cada cita indica el anexo, por ejemplo «Figura 4 (Anexo C)». Los diagramas se generan desde los archivos Mermaid de [`diagrams/`](diagrams/); las capturas se toman siguiendo la [guía de capturas](capture_guide.md).

| N.º | Título definitivo | Tipo | Ubicación en el protocolo | Se cita en | Ficha | Archivo |
|---|---|---|---|---|---|---|
| 4 | Arquitectura hexagonal del prototipo | Diagrama | Anexo C | VI.H.1 y VIII.D | [Figure04](figures/Figure04_Arquitectura_hexagonal.md) | `diagrams/architecture.png` |
| 5 | Arquitectura de despliegue con Docker Compose | Diagrama | Anexo C | VII.C y VII.D | [Figure05](figures/Figure05_Despliegue.md) | `diagrams/deployment.png` |
| 6 | Pipeline de ingesta documental | Diagrama | Anexo D | VIII.A | [Figure06](figures/Figure06_Pipeline_ingesta.md) | `diagrams/ingestion.png` |
| 7 | Flujo de atención de una consulta | Diagrama | Anexo D | VIII.C | [Figure07](figures/Figure07_Flujo_consulta.md) | `diagrams/flow.png` |
| 8 | Pantalla de inicio de sesión | Captura | Anexo E | VIII.D.2 | [Figure08](figures/Figure08_Inicio_sesion.md) | `figures/capturas/Figura08_inicio_sesion.png` |
| 9 | Consulta en modo invitado | Captura | Anexo E | VIII.D.2 | [Figure09](figures/Figure09_Modo_invitado.md) | `figures/capturas/Figura09_modo_invitado.png` |
| 10 | Pantalla inicial del asistente | Captura | Anexo E | VIII.D.4 | [Figure10](figures/Figure10_Pantalla_inicial.md) | `figures/capturas/Figura10_pantalla_inicial.png` |
| 11 | Respuesta fundamentada con citación de la fuente | Captura | Anexo E | VIII.D.4 (y VIII.C.9) | [Figure11](figures/Figure11_Respuesta_citada.md) | `figures/capturas/Figura11_respuesta_citada.png` |
| 12 | Abstención ante una consulta sin respaldo documental | Captura | Anexo E | VIII.D.4 (y VIII.C.8) | [Figure12](figures/Figure12_Abstencion.md) | `figures/capturas/Figura12_abstencion.png` |
| 13 | Historial persistente de la conversación | Captura | Anexo E | VIII.D.4 | [Figure13](figures/Figure13_Historial.md) | `figures/capturas/Figura13_historial.png` |
| 14 | Panel administrativo de documentos | Captura | Anexo E | VIII.D.4 (y VII.B) | [Figure14](figures/Figure14_Panel_administrativo.md) | `figures/capturas/Figura14_panel_administrativo.png` |

### Cambios respecto de la lista inicial de seis figuras

| Lista inicial | Decisión | Justificación |
|---|---|---|
| Figura 1 · Arquitectura general del sistema RAG | Se divide en las **Figuras 4 y 5** | Una sola figura no puede mostrar a la vez la regla de dependencias de la Arquitectura Hexagonal (VI.H.1–2) y los contenedores, puertos y volúmenes de Docker Compose (VII.D). Juntas, cualquiera de las dos vistas pierde legibilidad. |
| Figura 2 · Inicio de sesión | Se mantiene como **Figura 8** | Respalda VIII.D.2 (dominio institucional, JWT y modo invitado). |
| Figura 3 · Interfaz principal | Se mantiene como **Figura 10** | Respalda VI.K y VIII.D.4 (sugerencias, panel lateral, indicador de conexión). |
| Figura 4 · Respuesta con citación | Se mantiene como **Figura 11** | Es la evidencia visual del objetivo específico 2: respuesta fundamentada con fuente. |
| Figura 5 · Panel administrativo | Se mantiene como **Figura 14** | Respalda el objetivo específico 1 («administrable desde la propia aplicación») y VII.B. |
| Figura 6 · Historial | Se mantiene como **Figura 13**, con otro enfoque | El backend conserva **una** conversación activa por usuario: no existe una lista de varias conversaciones que capturar. La figura muestra lo que sí existe y es verificable: el hilo se recupera intacto tras cerrar e iniciar sesión. Ver discrepancia D7. |
| — | **Nueva: Figura 6**, pipeline de ingesta | El protocolo pide un diagrama de flujo (Anexo C), pero el flujo de la consulta no cubre el objetivo específico 1 ni la Fase I. Sin este diagrama, la Fase I solo se describe en prosa. |
| — | **Nueva: Figura 7**, flujo de la consulta | Es el diagrama de flujo que pide el Anexo C, dibujado desde `AnswerStudentQueryUseCase`. |
| — | **Nueva: Figura 9**, modo invitado | El protocolo lo destaca en la justificación, en VII.A y en VIII.D.2, y es la diferencia visible entre perfiles de acceso. Sin figura, el lector no sabe qué ve un visitante. |
| — | **Nueva: Figura 12**, abstención | La abstención explícita es una contribución central (objetivo 2, VI.B.6) y una métrica del estudio (exactitud de abstención, H₁ y Cuadro 5). Sin ella, el documento solo muestra el caso exitoso. |

No se proponen más figuras: los parámetros, la API y el diseño experimental ya están en los Cuadros 1 a 5, y repetirlos como figura sería redundante.

## 2. Lista definitiva de diagramas

| Archivo | Figura | Representa |
|---|---|---|
| [`diagrams/architecture.mmd`](diagrams/architecture.mmd) | 1 | Capas, nueve pares puerto/adaptador y servicios externos |
| [`diagrams/deployment.mmd`](diagrams/deployment.mmd) | 2 | Tres contenedores, volúmenes, `.env` y la única salida a Internet |
| [`diagrams/ingestion.mmd`](diagrams/ingestion.mmd) | 3 | Registro, extracción, limpieza, fragmentación estructural, vectorización e indexación |
| [`diagrams/flow.mmd`](diagrams/flow.mmd) | 4 | De la pregunta a la respuesta: autenticación, comprensión, recuperación híbrida, verificación y citación |

Las versiones listas para insertar (`.png` y `.svg`) están junto a cada `.mmd` en [`diagrams/`](diagrams/). Ver [`diagrams/README.md`](diagrams/README.md).

## 3. Orden de los anexos

**Aplicado en el documento.** Se intercambiaron los anexos C y D en el índice preliminar y en los títulos de los anexos, para que la numeración de las figuras avance en orden:

- C. Diagramas de arquitectura del sistema (Figuras 4 y 5)
- D. Diagramas de flujo del sistema (Figuras 6 y 7)
- E. Capturas de pantalla del prototipo (Figuras 8 a 14)

## 4. Discrepancias entre el protocolo y la implementación

Al dibujar los diagramas desde el código aparecieron afirmaciones del protocolo que ya no describían el sistema. **Las once están corregidas en el documento** (como control de cambios en la versión de revisión), siguiendo el criterio de actualizar el protocolo al sistema desplegado. Esa es la configuración que mide `evaluate.py` y la que muestran las figuras; la configuración anterior (fragmentos fijos, Top-K 10 y umbral 0.35) queda descrita en el texto como configuración de referencia. Además, se añadieron a la bibliografía las fuentes de BM25 (Robertson y Zaragoza, 2009) y de Reciprocal Rank Fusion (Cormack et al., 2009), que el texto corregido cita.

| # | Protocolo dice | El sistema hace | Sección afectada | Gravedad |
|---|---|---|---|---|
| D1 | Fragmentación de tamaño fijo, 1000 caracteres con solapamiento de 100 | Fragmentación estructural: el artículo es la unidad, hasta 600 caracteres, solapamiento de 100, con sección y páginas (ADR-0012). Antes, además, se retiran encabezados y firmas repetidos | VI.C.3, VIII.A.3–4, Cuadro 3 | **Alta** |
| D2 | Recuperación densa: Top-K = 10 y umbral 0.35 | Recuperación híbrida: 30 candidatos densos + BM25, fusión RRF (k = 60), reordenamiento estructural, admisión en dos niveles (0.55/0.5 y 0.35/0.25) y ensamblado de hasta 8 pasajes / 6000 caracteres | VI.C.5, VI.D, VIII.B.4–5, Cuadro 3 | **Alta** |
| D3 | El experimento usa los parámetros del Cuadro 3 | `scripts/evaluate.py` construye el pipeline con `rag_factory` y la configuración desplegada (D1 y D2), no con la del Cuadro 3 | VIII.E.2, Cuadro 3 | **Alta**: hay que decidir qué se evalúa |
| D4 | La citación identifica el documento, no la página ni la sección | Cada fuente muestra documento, sección (p. ej., «Artículo 7») y páginas | VIII.I (limitaciones), VIII.C.9 | Media |
| D5 | Se citan los documentos de todos los fragmentos recuperados | Se citan solo los pasajes que el modelo declara haber usado (`cited_fragments`) | VIII.C.9 | Media |
| D6 | La salida estructurada tiene cuatro campos | Tiene además `coverage` (cobertura completa, parcial o ninguna) y `cited_fragments`; la abstención también ocurre con cobertura «ninguna» | VI.B.5, VIII.C.7–8 | Media |
| D7 | Panel lateral de «conversaciones agrupadas por fecha» | Una conversación activa por usuario; «Nueva conversación» solo limpia la vista en el navegador | VIII.D.4 | Media |
| D8 | El modo invitado no guarda historial | Las conversaciones del invitado se guardan, para la memoria conversacional, y se eliminan a los 7 días (ADR-0019); el invitado no ve historial ni panel | VI.F.2, VI.F.3, VIII.D.2 | Media |
| D9 | El Cuadro 2 lista las rutas de la API | Falta `POST /auth/guest` (inicio de sesión de invitado) | Cuadro 2 | Baja |
| D10 | «El contenido del historial nunca se incluye en el prompt» | En preguntas de seguimiento se añade un extracto de la respuesta anterior (hasta 320 caracteres; 1400 al pedir una reformulación), marcado como no fuente | VI.E.3 | Media |
| D11 | 11 ADR · 81 pruebas de backend · 39 de frontend · 3 migraciones | 19 ADR · 450 pruebas de backend · 64 de frontend · 5 migraciones (medido el 9 de octubre de 2026) | VI.H.2, VIII.D.3, VIII.D.5 | Baja |

**Sobre D1–D3.** Se eligió el primero de estos dos caminos; el asesor puede revertirlo rechazando esos cambios en la versión de revisión:

- **Actualizar el protocolo al sistema desplegado (recomendado).** Es lo que se construyó, lo que se usa en las capturas y lo que mide `evaluate.py`; además, la línea base de 0.35 se abandonó porque no separaba nada en el corpus real (ver `KnowledgeRetriever`).
- **Evaluar la línea base congelada.** Habría que ejecutar `evaluate.py` con `RAG_CHUNKING_STRATEGY=fixed`, `RAG_RETRIEVAL_MODE=dense` y `RAG_CONTEXT_CHAR_BUDGET=0`, y aun así las Figuras 6, 7 y 11 no representarían lo evaluado.

## 5. Problemas del sistema que afectan a las capturas

Los puntos 1, 2 y 3 se resolvieron el 10 de octubre de 2026 (pasos en la [guía](capture_guide.md#0-preparación-del-sistema); el punto 3, con el commit «fix(chat): sugerencias de la pantalla inicial sobre el corpus oficial»). El punto 4 queda explicado en el texto del protocolo:

1. **El corpus ficticio está indexado.** `becas_y_beneficios.pdf`, `reglamento_estudiantil.pdf` y `seguro_estudiantil.pdf` aparecen como «Indexado» en la base de datos; el protocolo (VII.B) promete retirarlos antes de la evaluación. Además, el backend los vuelve a indexar en cada arranque desde `/app/documents` si no están registrados.
2. **Documento duplicado.** «Administración de Empresas 2025.pdf» está registrado dos veces: el panel mostraría 19 documentos en lugar de 15.
3. **Sugerencias de la pantalla inicial.** Las cuatro sugerencias (`frontend/src/features/chat/components/empty-state.tsx`, líneas 8–11) y el subtítulo («Pregunta por reglamentos, becas, seguro estudiantil…») vienen del corpus ficticio. «¿Qué cubre el seguro estudiantil?» es la pregunta Q33 del banco, que está **fuera** del corpus, y el corpus oficial tampoco trata «requisitos de graduación» ni un «reglamento de inscripción». Un miembro del tribunal que las pulse obtendrá abstenciones. Corregirlas es un cambio de cuatro líneas, fuera del alcance de esta tarea.
4. **Botón «Ingresar con Microsoft».** Aparece en el inicio de sesión, pero solo muestra el aviso de que no está habilitado. El texto del protocolo no debe presentarlo como funcional.

## 6. Problemas detectados fuera del material gráfico

**Seguimiento mal interpretado (detectado al capturar la Figura 13).** En la conversación de demostración, después de dos preguntas sobre becas y crédito, la consulta «¿Qué cubre la ayuda en los campus externos?» se interpretó como «cobertura del Comité de Ayudas Financieras», y el asistente se abstuvo. El Reglamento sí regula la cobertura para campus externos (Capítulo V, Artículo 24). No afecta a ninguna figura (se usó un encuadre de dos turnos), pero es un caso real para el banco de conversaciones de regresión.


**`scripts/analyze.py` no convierte bien los rangos del Anexo F.** El protocolo (VIII.E.4) define [T1] como una pregunta de opción múltiple con rangos y puntos medios fijos. El conversor de texto libre que se integró en `analyze.py` los interpreta mal:

| Opción del Anexo F | Debe valer (min) | `analyze.py` devuelve |
|---|---|---|
| Menos de 30 minutos | 15 | 30 |
| Entre 30 minutos y 1 hora | 45 | 90 |
| Entre 1 y 4 horas | 150 | 241 |
| Entre 4 y 24 horas (1 día hábil) | 840 | 2884 |
| Entre 1 y 3 días hábiles | 2880 | 4321 |
| Más de 3 días hábiles | 4320 | 4320 |

Tampoco implementa el análisis de sensibilidad con el límite inferior de cada rango (VIII.G.3). Por su parte, los encabezados de `scripts/encuesta_plantilla.csv` no coinciden con el texto del Anexo F ([D1] pregunta la carrera y no la facultad; [T1] pide minutos y no un rango). Debe corregirse antes de aplicar la encuesta; no se modificó porque esta tarea excluye cambios de código.

## 7. Matriz de cobertura

| Elemento del protocolo | Figura que lo respalda |
|---|---|
| Objetivo específico 1 (ingesta administrable) | 3, 11 |
| Objetivo específico 2 (comprensión, RAG, verificación, abstención, citación) | 4, 8, 9 |
| Objetivo específico 3 (evaluación) | 1 (componente de evaluación); resultados en cuadros del capítulo IX |
| VI.H Arquitectura Hexagonal y Clean Architecture | 1 |
| VI.K Interacción humano-computadora | 7, 8 |
| VII.B Base documental | 11 |
| VII.C–D Ecosistema y despliegue | 1, 2 |
| VIII.A Fase I | 3 |
| VIII.B Fase II | 3, 4 |
| VIII.C Fase III | 4, 8, 9 |
| VIII.D Fase IV | 5, 6, 7, 8, 9, 10, 11 |
| Anexo C | 1, 2 (tras el intercambio recomendado) |
| Anexo D | 3, 4 (tras el intercambio recomendado) |
| Anexo E | 5 a 11 |
