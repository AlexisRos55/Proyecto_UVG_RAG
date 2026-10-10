# Fase 9 (continuación) — Capa de inteligencia de recuperación

**Fecha:** 2026-09-24 · **Decisión:** [ADR-0015](adr/0015-retrieval-intelligence-layer.md) · **Antecedente:** [12-fase9-evolucion-motor-rag.md](12-fase9-evolucion-motor-rag.md)

El motor RAG ya recuperaba bien una pregunta aislada. Este documento describe cómo se le enseñó a **pensar antes de buscar** dentro de una conversación, y cómo se midió. Todas las cifras son reproducibles con los scripts indicados, sobre el corpus oficial real (16 PDF).

---

## 1. Componentes nuevos implementados

| Componente | Capa | Responsabilidad |
|---|---|---|
| `ConversationState`, `TurnInterpretation`, `TurnMode` | dominio (VO) | Foco de la conversación (tema, entidad, aspecto, documentos, artículo, aspectos tratados) e interpretación del turno actual |
| `ConversationTracker` | dominio (servicio) | Reconstruye el estado reproduciendo el historial; interpreta el turno (nuevo, seguimiento, profundizar, retomar, artículo contiguo); reescribe la consulta |
| `conversation_lexicon` | dominio | Temas, aspectos y marcadores de discurso del dominio (anáforas, enclíticos, pronombres átonos, «continuemos», «profundiza») |
| `EntityExtractor`, `CorpusEntity` | dominio | Entidades con nombre: programas, instancias, campus, carreras, eventos fechados, autoridades; artículo que define cada una |
| `evidence_reranker` | dominio | Reordenamiento por entidad en foco, aspecto en el título (acotado al tema), artículos que definen entidades; anclaje de seguimientos a su foco |
| `answer_planner` | dominio | Forma de la respuesta decidida con la evidencia: panorama, por programa, consecuencias, explicación |
| `voice_guard` | dominio | Retiro determinista de vocabulario de «maquinaria» en la respuesta |
| `document_card` (ficha del documento) | infraestructura | Conserva una vez el membrete (código, versión, vigencia, quién elaboró, revisó y autorizó) |
| `table_annotations` | infraestructura | Advierte en cada pieza de las tablas cuyas marcas por programa se pierden al extraer texto |
| `CorpusCatalogPort.entities / vocabulary / co_occur` | puerto | Conocimiento del corpus para la capa conversacional |
| Intención `CONTINUATION`, habilidad `RESUME_CONVERSATION`, estilos `OVERVIEW` y `PER_ITEM` | dominio | Retomar tras una pausa; nuevas formas de respuesta |
| `scripts/evaluate_conversations.py` + dos bancos | evaluación | Medición offline y gratuita de conversaciones multiturno |

## 2. Decisiones arquitectónicas

- **Determinista y sin llamadas adicionales.** La interpretación podría pedírsele al modelo, pero costaría una llamada por turno (NFR-02, ADR-0005), añadiría latencia y no sería reproducible ni probable exhaustivamente. Toda la capa cuesta cero tokens.
- **El estado se deriva, no se almacena.** Se reconstruye reproduciendo los mensajes persistidos (ventana de 24). Sin tabla, sin migración, sin posibilidad de desincronizarse; dos ejecuciones sobre la misma conversación dan el mismo estado.
- **La pregunta del estudiante nunca se modifica.** Al modelo llega el texto literal más una glosa de la interpretación; la consulta optimizada solo se usa para buscar.
- **El historial no entra al prompt.** Se mantiene la decisión de la capa de agencia: el modelo no puede fundamentarse en sus propias respuestas anteriores. Del historial solo se extraen nombres de entidades del corpus y las fuentes citadas.
- **Conocimiento desde el corpus.** Las expansiones de un panorama (Programa Regular, Beca Despega, Becas CONADER…) y la pertenencia de una palabra a un tema (coocurrencia en fragmentos) se obtienen del índice, no de listas escritas a mano.
- **Hexagonal intacta.** Los servicios nuevos son puros; el único acceso a datos es por `CorpusCatalogPort`, ampliado con tres operaciones. Sin catálogo, el caso de uso se comporta exactamente como antes; la capa se puede desactivar (`conversation_intelligence=False`) para ablaciones.

## 3. Cómo evolucionó el pipeline RAG

```
Antes:   pregunta ─► clasificación ─► (anteponer la pregunta anterior si hay anáfora) ─► búsqueda ─► LLM

Ahora:   pregunta ─► saneamiento ─► clasificación
                         │
                         ▼
         ┌──────── CAPA DE INTELIGENCIA DE RECUPERACIÓN ────────┐
         │ estado (replay del historial) → interpretación del turno │
         │ nuevo · seguimiento · profundizar · retomar · artículo ± │
         │ reescritura (palabras + foco) · expansión desde el corpus │
         │ foco requerido · aspecto · artículos que definen entidades│
         │ prioridad de fuentes (calendario para fechas)             │
         └───────────────────────────────────────────────────────────┘
                         │
                         ▼
         híbrida (coseno + BM25) ─► reordenamiento ─► gate anclado al foco
                         │
                         ▼
         contexto adaptativo (×1.5 panorama · ×0.7 dato puntual)
                         │
                         ▼
         planificación de la forma ─► 1 llamada (pregunta literal + glosa)
                         │
                         ▼
         guardia de voz ─► respuesta con citas por artículo y página
```

## 4. Mejoras del retrieval

Banco de 50 preguntas aisladas (`scripts/evaluate_retrieval.py`):

| Métrica | Línea base congelada | Fase 9 (antes de esta capa) | **Ahora** |
|---|---:|---:|---:|
| hit@1 | 0.109 | 0.457 | **0.565** |
| recall@5 | 0.326 | 0.783 | **0.815** |
| MRR | 0.186 | 0.618 | **0.689** |
| Recall del contexto final | 0.391 | 0.891 | **0.891** |
| Abstención previa al LLM fuera de dominio | 0/4 | 4/4 | **4/4** |

La mejora en esta etapa viene de la prioridad de fuentes por tipo de pregunta (el calendario para «¿cuándo?») y de la lematización de infinitivos.

## 5. Mejoras de la continuidad conversacional

Banco de conversaciones (`scripts/evaluate_conversations.py`):

| Conjunto | Antes | **Ahora** |
|---|---:|---:|
| Desarrollo (8 conversaciones, 25 turnos) — turnos correctos | 28 % | **100 %** |
| Desarrollo — referencias resueltas | 0 % | **100 %** |
| Reservado (6 conversaciones, 16 turnos) — primera y única medición antes de corregir | — | **62.5 %** |
| Reservado — tras corregir causas generales | — | 87.5 % |

La cifra honesta de generalización es la del conjunto reservado en su primera medición (62.5 %); la segunda ya no es independiente. De los dos fallos restantes, uno es una paráfrasis que ningún canal une («fuera de tiempo» ↔ «anticipación de 48 horas») y el otro exige abstención previa al modelo donde lo correcto es que la abstención la haga la verificación (el folleto menciona «parqueo» pero no su costo).

Conversación del enunciado, resuelta de extremo a extremo y verificada en vivo con Claude Haiku 4.5:

| Turno | Consulta interna | Resultado en vivo |
|---|---|---|
| Háblame de las becas. | becas ayudas financieras + los programas del corpus | Panorama de 5 programas, 8 artículos citados |
| ¿Cuánto cubre esa? | cubre becas ayudas financieras (+ cobertura porcentaje) | Tabla por programa (Trasciende 5–25 %, Despega hasta 15 %), cobertura parcial declarada |
| ¿Y cuáles son los requisitos? | requisitos becas ayudas financieras | Lista de requisitos por campus, advirtiendo que la correspondencia por programa se verifica en la oficina |
| ¿Hasta cuándo puedo aplicar? | aplicar becas ayudas financieras (+ plazo) | Abstención natural: «La normativa sobre las becas y ayudas financieras no establece plazos o fechas…» |
| ¿Pierdo la beca si bajo mi promedio? | pregunta autosuficiente (antes: declinada como dato personal) | Respuesta acotada por campus con los artículos 18, 19, 25 y 26 |

Además: «Hola» → «Becas» → «Requisitos» → «Cobertura» → «Gracias» → «Hola» («¿Seguimos con las becas…?») → «Continuemos» (recapitula lo visto y ofrece lo pendiente) funciona sin perder el tema; «¿Y el siguiente?» navega al artículo contiguo; «¿Quién decide eso?» resuelve al Consejo Electoral; «¿Cuánto cuesta el parqueo?» tras hablar de elecciones se reconoce como pregunta nueva.

## 6. Mejoras de la comprensión documental

Cada documento aporta ahora, además de su índice (capítulos, artículos, páginas, resumen extractivo y términos distintivos):

- **Entidades**: 15 programas de ayuda (incluidas Becas CONADER y Becas AVE), 15 instancias (Consejo Electoral, Comité de Ayudas Financieras, Registro Académico…), 4 campus, 8 carreras, 56 eventos fechados del calendario y 10 autoridades.
- **Artículo que define cada entidad** (p. ej. Beca Despega → Artículo 29), usado para priorizar esos artículos en un panorama.
- **Ficha del documento**: código, versión, vigencia, elaboró, revisó y autorizó. Antes el membrete se descartaba entero y «¿quién revisó el reglamento?» era irrespondible.
- **Tablas con marcas perdidas**: las piezas de las tablas de requisitos, condiciones y penalizaciones llevan una advertencia explícita.

## 7. Impacto esperado en precisión y experiencia de usuario

- **Precisión.** La prueba en vivo reveló un caso grave que la evaluación offline no podía ver: ante «¿Y cuáles son los requisitos?», el modelo completó una matriz con ✓ en todas las celdas, porque las marcas reales del PDF son dibujos vectoriales que no llegan como texto. Tras anotar las tablas y endurecer las reglas, la respuesta enumera los requisitos y advierte que la correspondencia por programa debe verificarse. También se eliminaron un ejemplo numérico inventado y una generalización a «todos los programas».
- **Experiencia.** Las preguntas de una o dos palabras, las elípticas («¿y si hay empate?») y las que dependen de la anterior se responden sin que el estudiante tenga que repetir el tema. Los saludos y agradecimientos intermedios ya no borran la conversación. Las abstenciones dicen qué tema y qué aspecto no están establecidos. Un fallo del proveedor produce un mensaje natural en lugar de un error HTTP 400.

## 8. Impacto esperado en consumo de tokens

| Medida | Valor |
|---|---|
| Llamadas adicionales introducidas | **0** (una por consulta fundamentada) |
| Turnos que no llaman al modelo | navegación, «continuemos», saludo con tema activo, abstención previa |
| Costo de la glosa de interpretación | ≈ 20–30 tokens de entrada por seguimiento |
| Tokens de entrada por llamada (medido en vivo) | 3 300 – 4 600 |
| Salida de «¿cuáles son los requisitos?» | 1 213 → **499** tokens al eliminar la matriz inventada |
| Contexto adaptativo | ×1.5 en panoramas, ×0.7 en datos puntuales |
| Tope de salida | 2 048 (antes 1 024); solo se factura lo generado |

## 9. Limitaciones que aún permanecen

- **Bancos pequeños y etiquetados por el equipo.** 25 + 16 turnos. La diferencia entre desarrollo (100 %) y reservado (62.5 % en primera medición) muestra sobreajuste; hace falta un banco más grande validado por personal institucional.
- **Léxico de temas y aspectos escrito a mano.** Cubre el dominio actual; un tema nuevo en el corpus funciona con menor precisión hasta que se añada.
- **Paráfrasis lejanas** que no comparten palabras ni cercanía en el espacio del modelo de embeddings actual (entrenado en inglés).
- **Tablas con marcas gráficas**: se advierte la pérdida, pero no se recupera la correspondencia requisito–programa.
- **«Esa» con varias candidatas** se responde a nivel de tema (una respuesta por programa) en lugar de preguntar cuál; es una elección de diseño documentada.
- **El resumen de la última respuesta** se basa en las entidades que nombró; si el modelo no nombra la entidad, «esa» puede no resolverse a ella.

## 10. Recomendaciones para una Fase 10

1. **Banco validado por expertos** de conversaciones reales (registros anonimizados de consultas en ventanilla), con evaluación de extremo a extremo y juez LLM (RAGAS) sobre la conversación completa.
2. **Modelo de embeddings multilingüe** (requiere aprobación del asesor): con él, el recall del contexto pasa de 0.891 a 0.935 sin otro cambio (anexo A del documento 12) y cerraría buena parte de las paráfrasis.
3. **Extracción geométrica de tablas** para recuperar a qué programa aplica cada requisito.
4. **Aprendizaje del léxico conversacional** a partir de los registros (qué palabras usan los estudiantes para cada tema), con revisión humana antes de incorporarlo.
5. **Pregunta de aclaración** cuando «esa» tenga varias candidatas y el estudiante haya mostrado interés en una sola, medida con usuarios reales.
6. **Caché semántica** de respuestas a preguntas frecuentes, ya viable porque la consulta interna reescrita es estable entre formulaciones.

---

## Verificación

| Suite | Resultado |
|---|---|
| Backend (unitarias, integración con PostgreSQL/ChromaDB/MiniLM reales, e2e) | **298 aprobadas** |
| Frontend (Vitest) | 58 aprobadas |
| `mypy src` / `ruff` | sin errores |
| Prueba en vivo (Claude Haiku 4.5) | 2 hilos completos + 3 re-verificaciones tras correcciones |

**Reproducir:**

```bash
python scripts/evaluate_retrieval.py --corpus-dir <PDF oficiales>
python scripts/evaluate_conversations.py --corpus-dir <PDF oficiales>
python scripts/evaluate_conversations.py --corpus-dir <PDF oficiales> --benchmark scripts/conversation_benchmark_holdout.json
```
