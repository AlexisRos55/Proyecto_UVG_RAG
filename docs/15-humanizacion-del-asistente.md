# Fase 10 — Humanización del Asistente Inteligente UVG

**Fecha:** 2026-09-26 · **Decisión:** [ADR-0017](adr/0017-human-conversation-memory-and-voice.md) · **Antecedente:** [14-experiencia-conversacional.md](14-experiencia-conversacional.md)

El criterio de éxito de esta fase no fue técnico: que el estudiante sienta que conversa con un asesor de la universidad y no con un buscador. No se añadieron capas ni patrones; se ampliaron los componentes existentes (rastreador conversacional, guía, prompt, catálogo local) y se midió todo con los scripts de `scripts/` sobre el corpus oficial real (16 PDF) y con seis corridas en vivo contra Claude Haiku 4.5, leídas turno por turno.

**Método.** Antes de tocar el código se escribió un banco reservado con conversaciones nuevas (`h10-*`) y se midió. Después, en cada iteración: pruebas unitarias, banco de desarrollo, banco reservado, simulador (tres semillas), benchmark de recuperación y una corrida en vivo leída como la leería un estudiante. Ninguna regresión se aceptó; los fallos del banco reservado solo se corrigieron cuando tenían una causa general, nunca con una regla para ese caso.

**Principios conversacionales adoptados.** Se tomaron de la observación de asistentes generales (ChatGPT, Claude, Perplexity, Gemini, Copilot), no de su redacción ni de sus interfaces:
1. El contexto se da por sabido: nadie repite lo que dijo hace un turno.
2. Primero la respuesta, después el matiz.
3. Una sola invitación al final, relacionada con lo que el usuario intenta lograr.
4. Cuando algo no se sabe, se dice qué sí se sabe y cuál es el siguiente paso.
5. Al usuario desorientado se le dan caminos concretos, no instrucciones de uso.

---

## 1. Mejoras implementadas

| Mejora | Qué percibe el estudiante |
|---|---|
| Pronombres de tercera persona y objeto de la pregunta anterior | «¿Necesito autorización?» → «¿Quién **la** da?» → «La autorización la da la entidad patrocinadora.» |
| Referencias por categoría con memoria | «¿Y **esa oficina** qué más hace?» (el Consejo Electoral); «¿Y **esa beca de antes** pide promedio?» tras hablar de clubes → la Beca Despega |
| Comparaciones que siguen en juego | «¿Diferencia entre Despega y Trasciende?» → tabla con las dos; «¿Y cuál me conviene si trabajo en una empresa aliada?» → «la Beca Despega es la que te corresponde» |
| Regreso explícito a un tema | «Volviendo a las elecciones, ¿y si hay empate?» → el artículo del empate, no el crédito del que se hablaba |
| Orientación sin modelo | «Estoy perdido», «no sé qué preguntar», «necesito ayuda con algo de la u» → temas cubiertos, cada uno con una pregunta lista para usar |
| «No entiendo» | Se vuelve a explicar lo mismo, más corto y con palabras sencillas, sin inventar cifras |
| Necesidad dicha con palabras propias | «No sé si me alcanza para pagar la carrera» → panorama de ayudas que aplican al Altiplano |
| Una palabra de tema | «becas» → panorama del tema (antes: un índice de apartados) |
| Abstención premium | Nombra el documento que sí trata el tema, lo que describe, con quién confirmarlo y la siguiente pregunta útil; un tema sin respaldo nunca empieza con «No encontré información» |
| Voz de asesor | Resumen primero; en preguntas de elección, la opción primero y lo que falta al final; sin repetir lo dicho; sin ejemplos con cifras inventadas; oficinas solo si la normativa las nombra |
| Ofrecimientos útiles | No se ofrece lo que la respuesta ya explicó; al abrir un tema, en términos de metas («qué se necesita, cuánto cubre cada opción…») y, si hay varias opciones, «si me cuentas tu situación, te digo cuál se ajusta mejor a ti» |
| Textos locales fieles al corpus | Saludo, «¿qué puedes hacer?», fuera de dominio y ruido listan solo temas con respaldo (antes se ofrecía «seguro estudiantil», que no está en el corpus) |
| Nombres con artículo | «la Beca Despega», «las Becas Trasciende», «el Consejo Electoral», también en pausas y saludos |
| Recuperación | Una subconsulta por entidad comparada; las preguntas con dos temas ya no anclan la evidencia al primero; «¿qué documentos piden?» ya no se confunde con «¿qué documentos manejas?»; sinónimos «votar/sufragio» |

## 2. Decisiones de diseño conversacional

- **Una persona recuerda lo último, no todo.** La memoria nueva es de corto plazo y derivada del historial: última pregunta, entidades recientes (ocho), comparación en curso. Se olvida sola al cambiar de tema o tras siete días.
- **Un demostrativo elige; un pronombre habla del asunto.** «¿Cuánto cubre **esa**?» se liga a la opción nombrada; «¿Quién **lo** decide?» no se liga a una beca citada de paso. Una opción cuenta solo si la respuesta la nombra completa: «ayuda financiera» no nombra a la Dirección de Ayudas Financieras.
- **Elegir es comparar.** «¿Cuál recomendarías?» compara las opciones en juego (de la misma clase y tema), no supone una sola.
- **Al estudiante perdido se le dan preguntas, no instrucciones.** La orientación es local y cada tema viene con una pregunta que el corpus responde.
- **Primero lo que aplica, salvo cuando lo que falta es la respuesta.** «¿Cuál me conviene?» empieza por una opción; «¿Cuál es el proceso?», si no existe en la normativa, lo dice primero (es la respuesta directa) y luego lo que sí regula.
- **El modelo ve el hilo, no lo usa como fuente.** Un extracto de la respuesta anterior acompaña a cada seguimiento para que no se repita ni pierda el pronombre, marcado explícitamente como «no es fuente» (ADR-0005 intacto).
- **Solo se promete lo que se puede cumplir.** Menús, capacidades y ofertas se derivan de lo que el corpus cubre; un tema que solo aparece de paso (cambio de carrera) se describe así, sin sugerir preguntas sin sentido.

## 3. Conversaciones que antes fallaban y ahora funcionan

Fragmentos reales de las corridas en vivo (primera corrida de la fase frente a la última).

| Conversación | Antes (Fase 9.2 o primera corrida de esta fase) | Ahora (última corrida) |
|---|---|---|
| «¿Necesito autorización?» → «¿Quién la da?» | Re-explicaba el cambio de carrera sin decir quién autoriza | «La entidad patrocinadora es quien da la autorización.» |
| «¿Quién las organiza?» (elecciones) | Búsqueda sin tema: artículos de fines y clubes | «El Consejo Electoral organiza las elecciones estudiantiles…» |
| «¿Y esa beca de antes pide promedio?» tras hablar de clubes | Buscaba en clubes | «Sí, la Beca Despega pide promedio. Debes mantener un promedio mínimo de 65 puntos…» |
| Despega vs Trasciende → «¿Y cuál me conviene si trabajo en una empresa aliada?» | Solo recuperaba el artículo de Despega; el seguimiento olvidaba Trasciende | Tabla con ambas y «**En resumen:**»; luego «la Beca Despega es la que te corresponde» |
| «Volviendo a las elecciones, ¿y si hay empate?» | No recuperaba el artículo del empate | Voto de calidad del Consejo Electoral y segunda vuelta en 72 horas hábiles |
| «¿Cuál conviene más para Ingeniería?» | «No puedo recomendarte cuál conviene más porque la normativa no establece…» | «Para Ingeniería en el Altiplano, la opción que te aplica es el Programa Regular.» |
| «estoy perdido» | «No encontré normativa oficial que hable de eso.» | «Vamos paso a paso. Estábamos viendo las becas…: puedo explicarte qué se necesita…» |
| «hola, necesito ayuda con algo de la u» | Llamada al modelo con respuesta genérica | Temas cubiertos con una pregunta de ejemplo cada uno, sin modelo |
| «qué puedes hacer» | Ofrecía «Seguro estudiantil» | Solo temas con respaldo documental |
| «no sé si me alcanza para pagar la carrera» | «Lo mejor es que te acerques al campus» | Programa Regular y Apoyo Especial primero, luego las demás opciones |
| «¿Y cuánto tarda?» (cambio de carrera) | Ofrecía «la cobertura del cambio de carrera» | «El Reglamento de ayudas financieras menciona el cambio de carrera solo de paso… y no establece la duración» + con quién confirmarlo |
| «¿Qué documentos piden?» (admisión) | Listaba los documentos que consulta el asistente | Se responde como pregunta de admisión |
| «¿Qué es la beca Despega?» | Ejemplo inventado: «si tus cuotas suman 1000 quetzales…» | Definición fiel, sin cifras propias |

## 4. Mejoras del benchmark conversacional

| Medición | Inicio de la fase | Final |
|---|---|---|
| Banco de desarrollo completo (22 conversaciones, 86 turnos) | 0.878 | **1.000** |
| — solo los 23 turnos de Fase 10 | 0.61 | **1.00** |
| Banco reservado (31 turnos) | 0.800 | **0.920** |
| — solo los 14 turnos de Fase 10, escritos antes de implementar | 0.786 | **1.000** |
| Simulador: 14 invariantes, 3 semillas, 360 conversaciones, **8 722 turnos** | 9 invariantes | **1.000** en todos, 0 errores |

Los dos fallos que conserva el banco reservado son anteriores a la fase y se dejaron sin ajustar a propósito: una paráfrasis que el léxico no reconoce y «¿Cuánto cuesta el parqueo?», que solo el modelo abstiene (ver la sección 7).

Durante la fase, el simulador reveló además un defecto que venía de fases anteriores y que su invariante de continuidad no detectaba: aceptaba como continuidad una respuesta local sin búsqueda. Al endurecerlo aparecieron los «¿qué documentos piden?» mal clasificados. Se corrigió la causa y el invariante quedó estricto.

## 5. Mejoras del retrieval benchmark

El benchmark medía el analizador de consultas solo (`enhanced`), pero lo desplegado añade la interpretación del rastreador. Se agregó la configuración `conversational`, que mide el camino real de una primera pregunta.

| Métrica (46 preguntas con evidencia + 4 fuera de dominio) | `enhanced` (Fase 9) | `conversational` al inicio | `conversational` final |
|---|---|---|---|
| hit@1 | 0.565 | 0.587 | **0.587** |
| recall@5 | 0.815 | 0.804 | 0.804 |
| Recall del contexto final | 0.891 | 0.913 | **0.924** |
| Falsas abstenciones | 0.000 | 0.000 | 0.000 |
| Abstención fuera de dominio sin modelo | 1.000 | 1.000 | 1.000 |

La mejora en el camino desplegado viene de no anclar a un solo tema las preguntas con dos partes. En conversación, las comparaciones recuperan ahora el artículo de cada opción. Se probó y **se descartó** añadir sinónimos del aspecto a las primeras preguntas: desplazaba evidencia (recall del contexto de un caso 1.0 → 0.5). Nota metodológica: el índice aproximado de ChromaDB no es idéntico entre reconstrucciones y hit@1 varía ±1 caso (0.565–0.587) sin cambios de código; por eso la métrica principal es el recall del contexto.

## 6. Mejoras de la experiencia de usuario

- **Menos repeticiones:** el seguimiento sabe qué se acaba de decir («Como te comentaba…»); los ofrecimientos omiten lo ya explicado.
- **Respuestas que empiezan por lo útil:** en las cuatro preguntas de elección del caso 4, las respuestas que abren con una opción concreta pasaron de 0 de 4 (primera corrida de la fase) a 3 de 4 (última). La restante, «¿Y para Tecnología?», todavía abre con lo que la normativa no distingue.
- **Formatos según la pregunta:** tablas de no más de cuatro columnas con «**En resumen:**» para comparaciones, resumen previo en panoramas, explicación sencilla cuando el estudiante no entiende.
- **Nadie queda sin camino:** orientación en «estoy perdido» y «necesito ayuda»; abstenciones con documento, instancia y siguiente pregunta; tras varios «no» seguidos, el asistente redirige en lugar de repetirse.
- **Honestidad verificable:** no se ofrecen temas sin respaldo, no se inventan oficinas ni ejemplos numéricos, y un tema que la normativa solo menciona de paso se describe así.
- **Costo:** ninguna llamada adicional al modelo. La orientación, las cortesías, las pausas y el saludo siguen siendo locales, y el panorama de un tema en una sola palabra dejó de ser un índice. El hilo añade unos 150 tokens a cada seguimiento.

## 7. Limitaciones que siguen existiendo

- **Tablas con marcas gráficas.** En una corrida, el modelo atribuyó a campus externos un «máximo de 15 %» que es una celda de una tabla por programa cuyas marcas se pierden al extraer el texto. El sistema lo advierte en el prompt, pero no lo impide.
- **Paráfrasis del modelo.** Hay imprecisiones menores y ocasionales («horas que puedes cursar» por «horas de trabajo»). La verificación en una sola llamada no las detecta todas.
- **Profundidad de recuperación.** «¿Quiénes no pueden votar?» y «¿Cuándo pierde un estudiante la membresía de un club?» siguen sin traer su artículo. Los sinónimos ya están; falta ordenar mejor por relevancia.
- **Léxico mantenido a mano.** Categorías, necesidad económica, pedidos de ayuda, temas y anclas son conocimiento del dominio.
- **La negativa inicial solo se reordena en preguntas de elección.** En las demás, el prompt lo pide y el modelo casi siempre cumple, pero no siempre.
- **El simulador no evalúa la redacción.** La calidad del texto generado se verificó con seis corridas en vivo, no con miles de turnos.
- **Solo campus externos.** La normativa agrupa el Altiplano entre los campus externos y el asistente asume que el estudiante es de ahí; no hay perfil de usuario (carrera, programa, beca actual).

## 8. Propuestas para la Fase 11

1. **Perfil del estudiante** (con consentimiento): carrera, campus y programa de ayuda actuales, para que «¿cuál me conviene?» no tenga que preguntar y el asistente recuerde entre sesiones.
2. **Tablas estructuradas en la ingesta:** reconstruir las matrices por programa (marcas vectoriales) para que el modelo reciba celdas atribuidas y no texto plano.
3. **Evaluación de la redacción en cada versión:** un conjunto en vivo pequeño (≈ 40 turnos) puntuado con una rúbrica (fidelidad, primera frase útil, repetición, formato) o con RAGAS, como complemento del simulador.
4. **Reordenamiento con un modelo cruzado** para los casos de profundidad de recuperación, dentro del presupuesto de latencia.
5. **Sugerencias como botones en la interfaz:** los ofrecimientos y el menú de orientación ya son estructurados.
6. **Validación con estudiantes reales** del Campus Altiplano: sus fallos alimentan el banco reservado, nunca el de desarrollo.

---

## Verificación

```bash
cd scripts
PYTHONPATH=../backend/src python simulate_conversations.py --corpus-dir <PDF> --seed 7     # también 13 y 29
PYTHONPATH=../backend/src python evaluate_conversations.py --corpus-dir <PDF>
PYTHONPATH=../backend/src python evaluate_conversations.py --corpus-dir <PDF> --benchmark conversation_benchmark_holdout.json
PYTHONPATH=../backend/src python evaluate_retrieval.py --corpus-dir <PDF> --configs enhanced,conversational
cd ../backend && pytest
```
