# Fase 9.2 — Experiencia conversacional de nivel profesional

**Fecha:** 2026-09-25 · **Decisión:** [ADR-0016](adr/0016-conversation-guide.md) · **Antecedente:** [13-capa-inteligencia-recuperacion.md](13-capa-inteligencia-recuperacion.md)

La Fase 9 enseñó al motor a resolver referencias. Esta fase se trabajó desde el otro extremo: **leer conversaciones completas como las leería un estudiante** y corregir lo que se siente mal, aunque técnicamente «funcione». No se añadió ningún componente cuyo único motivo fuera la arquitectura. Todas las cifras son reproducibles con los scripts de `scripts/` sobre el corpus oficial real (16 PDF).

Método, en cada cambio: simulador de conversaciones + banco etiquetado + banco reservado + benchmark de recuperación + pruebas unitarias; no se aceptó ninguna regresión. Además, tres corridas en vivo de los cinco casos del enunciado contra Claude Haiku 4.5, leídas turno por turno.

---

## 1. Problemas encontrados

Encontrados al auditar los casos 1–5 del enunciado y 120 conversaciones simuladas (2 696 turnos), antes de corregir nada:

| # | Problema | Cómo se veía | Medición inicial |
|---|---|---|---|
| 1 | El tema se olvidaba al pausar | «Continuemos mañana» → una despedida genérica, sin mencionar las becas | memoria_pausa **0.410** |
| 2 | Seguimientos que buscaban fuera del tema | «¿Qué pasa si no cumplo?» tras hablar de becas buscaba sanciones de clubes | continuidad **0.813** |
| 3 | Cortesías que llamaban al modelo | «Perfecto gracias», «super», «jaja» gastaban una llamada | cortesía **0.814** |
| 4 | Un tema sin respaldo «se respondía» | «¿Qué cubre el seguro estudiantil?» pasaba con un folleto que dice «seguridad de la información» (misma raíz *segur*) | abstención honesta **0.656** |
| 5 | Reanudación y saludo de regreso sin memoria en conversaciones largas | Tras unos 12 turnos el tema desaparecía: la ventana de reproducción era de 24 mensajes | reanudación **0.923**, memoria_saludo **0.923** |
| 6 | «¿Por qué?», «dame un ejemplo», «¿qué pasa después?», «el anterior» | Se trataban como preguntas nuevas sin sujeto | — (casos 3 y 4) |
| 7 | «Artículo 20» a secas | Se buscaba por similitud; el modelo recibía artículos vecinos y a veces se negaba | caso 3 |
| 8 | «¿Y para Tecnología?» | Mezclaba Ingeniería y Tecnología en la misma búsqueda | caso 4 |
| 9 | «¿Y esa tiene requisitos?» tras «¿Cuál cubre más?» | «esa» no se ligaba a la beca ganadora | caso 1 |
| 10 | Abstenciones inútiles | «No encontré información» sin decir qué sí hay; idénticas al repetirse; prometían «la oficina correspondiente» sin poder nombrarla | caso 5 |
| 11 | Doble ofrecimiento | El modelo cerraba con «¿Quieres conocer más…?» y el sistema añadía «Si quieres, también puedo…» | casos 1 y 4 (en vivo) |
| 12 | Ofertas imposibles | Se ofrecía «la cobertura» del cambio de carrera porque el reglamento de ayudas la trata para las becas | caso 2 (en vivo) |
| 13 | Dudas del modelo sobre el campus del estudiante | «Si estás en el Campus Central…» a un estudiante del Altiplano | caso 1 (en vivo) |
| 14 | Negaciones falsas | «La normativa no establece un promedio mínimo» (sí lo establece: 65 puntos) | caso 1 (en vivo) |

## 2. Decisiones tomadas

- **Pensar como asesor, no como buscador.** Cada respuesta determinista (cortesía, pausa, saludo de regreso, reanudación, abstención) nombra el tema activo. Es lo que haría una persona que recuerda la conversación.
- **Ofrecer solo lo que se puede cumplir.** Los aspectos que se ofrecen salen de los títulos de los artículos que tratan el tema: todo el documento si el tema es el documento, el capítulo si el tema es un capítulo (clubes), y solo los artículos recuperados si el tema es un apartado de otro documento (cambio de carrera). Como máximo tres.
- **Una sola invitación por respuesta.** La instrucción al modelo («no cierres con preguntas») no bastó; el sistema reemplaza de forma determinista el último párrafo interrogativo del modelo por su propia oferta, que es la única que sabe qué cubre la normativa.
- **Una abstención también orienta, y no se repite.** Primera vez: qué no está, qué sí describe la normativa (máximo tres aspectos) y qué puedo hacer. Segunda: breve («tampoco encontré…»). Tercera: redirige a lo que el corpus sí trata y recomienda confirmarlo en el campus, sin inventar una oficina. Siguientes: cortas y variadas.
- **Memoria útil que olvida con naturalidad.** El estado se reproduce sobre hasta 120 mensajes (antes 24) y caduca a los 7 días: «hasta mañana» se recuerda, un tema de hace un mes no. Un tema nuevo reemplaza al anterior; una palabra del mismo tema lo continúa (coocurrencia en el corpus).
- **La navegación por artículos es exacta.** «Artículo 20», «el siguiente», «el anterior» recuperan el artículo por número desde el catálogo, y al modelo se le da la lectura explícita («Se refiere al Artículo 20 del Reglamento de grupos estudiantiles: explica qué establece»).
- **Anclas sin homónimos.** El ancla de un tema usa palabras cuya raíz no colisiona con otras del corpus.
- **Reglas de redacción en el prompt, no pasos adicionales.** Estudiante del Altiplano («campus externos» en la normativa), cobertura parcial en vez de negativa cuando la norma no distingue el caso, ejemplos ilustrativos permitidos si aplican la norma, prohibido afirmar «no establece» salvo que se pregunte. Se mantiene una sola llamada por consulta (ADR-0005).
- **Refactorización.** Se retiraron del caso de uso cuatro redacciones sueltas (`_no_retrieval_text`, `_not_grounded_text`, `_resume_text`, `_enumerate`) a favor de `conversation_guide`; el léxico de temas pasó a declarar sus anclas explícitamente.

## 3. Conversaciones corregidas

Fragmentos reales de la tercera corrida en vivo (Claude Haiku 4.5, corpus oficial).

**Caso 1 — becas, pausa y regreso al día siguiente**

> **¿Cuál cubre más?** → compara Trasciende (5–25 %) y Despega (hasta 15 %).
> **¿Y esa tiene requisitos?** → «Sí. Para acceder a una **Beca Trasciende** debes…» (antes: requisitos genéricos de todas las becas).
> **¿Qué pasa si bajo mi promedio?** → «…debes mantener un promedio mínimo de 65 puntos…» (antes: «la normativa no establece un promedio mínimo»).
> **Continuemos mañana** → «Claro. Cuando vuelvas, retomamos Becas Trasciende donde lo dejamos.» (antes: una despedida sin mencionar el tema)
> **Hola** → «Hola de nuevo. ¿Seguimos con Becas Trasciende o necesitas otra cosa?»
> **Sigamos con las becas** → «Claro, sigamos con las becas y ayudas financieras. Hasta ahora vimos la cobertura, los requisitos, las penalizaciones y los plazos. Si quieres, también puedo explicarte cómo se solicita, las condiciones para mantenerla o quién lo decide. ¿Qué te interesa?»

**Caso 2 — cambio de carrera**: cada seguimiento («¿Cuál es el proceso?», «¿Necesito autorización?», «¿Quién la da?») se responde sobre el cambio de carrera, distinguiendo campus central, campus externos y AVE. «¿Y cuánto tarda?» se abstiene diciendo qué sí describe la normativa sobre ese apartado. «Ahora háblame del seguro» cambia de tema limpiamente.

**Caso 3 — navegación**: «Artículo 20» → los fines de las asociaciones; «¿Y el siguiente?» → Artículo 21; «¿Y el anterior?» → Artículo 20; «Explícalo» → el porqué; «Dame un ejemplo» → un voluntariado que cumple los incisos e, f e i. Antes, el modelo recibía artículos vecinos por similitud y a veces se negaba a explicar el pedido.

**Caso 4 — comparaciones**: «¿Cuál conviene más para Ingeniería?» y luego «¿Y para Tecnología?» buscan cada carrera por separado; «¿Cuál recomendarías revisar primero?» da una recomendación razonada con los porcentajes de la normativa.

**Caso 5 — tema sin respaldo**

> **Háblame del seguro** → «No encontré en los documentos oficiales que consulto información sobre el seguro estudiantil. Los documentos que consulto tratan sobre…»
> **¿Cuánto cubre?** → «Sobre el seguro estudiantil tampoco encontré la cobertura en la normativa que consulto.»
> **¿Y si ocurre fuera del campus?** → redirige a lo que sí puede responder.
> **¿Qué exclusiones tiene?** → «Tampoco tengo respaldo oficial para ese punto del seguro estudiantil. Si quieres, cambiamos a otro tema en el que sí pueda ayudarte.»
> **¿Y enfermedades?** → «Eso tampoco lo recoge la documentación oficial que tengo sobre el seguro estudiantil; conviene confirmarlo en el campus.»

Antes, desde la tercera todas eran la misma frase y prometían una oficina que el sistema no sabe nombrar.

## 4. Evolución del benchmark

**Simulador de conversaciones** (`simulate_conversations.py`, 120 conversaciones, semilla 7, 2 696 turnos; el modelo se sustituye por un registrador):

| Invariante | Línea base | Final |
|---|---|---|
| continuidad | 0.813 | **1.000** |
| cortesía | 0.814 | **1.000** |
| memoria_pausa | 0.410 | **1.000** |
| memoria_saludo | 0.923 | **1.000** |
| reanudación | 0.923 | **1.000** |
| abstención honesta | 0.656 | **1.000** |
| cambio de tema | 1.000 | **1.000** |
| fuera de dominio | 1.000 | **1.000** |
| voz | 1.000 | **1.000** |
| **Global** | **0.863** | **1.000** |

Evolución del global por iteración: 0.863 → 0.977 (memoria, cortesías, léxico de temas) → 0.995 (anclaje de todo el contexto, referencias ampliadas) → 0.997 (guía conversacional) → **1.000** (anclas sin homónimos).

Semillas nuevas, nunca usadas para ajustar: semilla 13 (2 717 turnos) y semilla 29 (2 894 turnos), ambas **1.000**. En total, 360 conversaciones y 8 307 turnos sin fallos ni errores.

**Bancos etiquetados y regresiones:**

| Medición | Antes de la fase | Después |
|---|---|---|
| Banco de conversaciones de desarrollo, con los cinco casos del enunciado (63 turnos) | 0.828 | **1.000** |
| Banco reservado (17 turnos, sin ajustar) | 0.875 | 0.875 (sin regresión) |
| Recuperación: hit@1 / recall@5 / recall del contexto | 0.565 / 0.815 / 0.891 | 0.565 / 0.815 / 0.891 (sin regresión) |
| Recuperación: abstención previa al modelo sin evidencia | 1.000 | 1.000 |
| Pruebas unitarias | — | **282** en verde (nuevas: guía conversacional, referencias ampliadas, ranking, carrera, pausa), mypy y ruff limpios |

## 5. Porcentaje de mejora

- Simulador global: 0.863 → 1.000, **+15.9 %** relativo; los fallos bajan de 524 a **0** en 2 696 turnos.
- Memoria al pausar: 0.410 → 1.000, **+144 %**.
- Abstención honesta: 0.656 → 1.000, **+52 %**.
- Continuidad: 0.813 → 1.000, **+23 %**; cortesía sin llamar al modelo: 0.814 → 1.000, **+23 %**.
- Casos del enunciado: 0.828 → 1.000, **+20.8 %**.
- Costo: las cortesías, pausas, saludos de regreso y reanudaciones (alrededor de uno de cada cinco turnos simulados) se resuelven sin llamar al modelo. Ninguna llamada adicional en el resto.

Cualitativamente, de la lectura de las corridas en vivo: ninguna respuesta con doble oferta, ninguna abstención repetida, ninguna negación falsa del promedio mínimo, y el tema activo se nombra en cada cierre y regreso.

## 6. Limitaciones restantes

- **El simulador no evalúa la redacción generada.** Sustituye el modelo por un registrador; la calidad del texto se verificó con tres corridas en vivo de los cinco casos, no con miles de turnos.
- **Paráfrasis fuera del léxico.** El banco reservado conserva un fallo por una paráfrasis que el léxico de temas no reconoce («residencias»), y otro caso («¿Cuánto cuesta el parqueo?») que solo el modelo abstiene, no la recuperación. Se dejaron sin ajustar a propósito para que el banco siga siendo honesto.
- **Léxico mantenido a mano.** Temas, aspectos, anclas y frases de oferta son conocimiento del dominio; un documento nuevo sobre un tema nuevo funciona, pero sin memoria de tema ni ofertas hasta añadirlo al léxico.
- **Homónimos por raíz.** Se corrigió «seguro/seguridad»; puede haber otros sin detectar en documentos futuros.
- **Etiqueta del foco.** Tras hablar de una beca concreta, la pausa y el saludo nombran esa beca («Becas Trasciende») y no el tema general. Es deliberado, pero discutible.
- **Tablas con marcas gráficas.** Siguen sin poder leerse qué programas marca cada fila; el sistema lo advierte, no lo resuelve (Fase 9).
- **Datos que la normativa no trae.** Plazos de solicitud de becas o duración del cambio de carrera: el asistente se abstiene con orientación, pero no puede nombrar la oficina responsable porque ningún documento la identifica.

## 7. Recomendaciones para la Fase 10

1. **Validación con estudiantes reales**: diez conversaciones reales por semana, leídas con los mismos criterios de este documento; los fallos alimentan el banco reservado, nunca el de desarrollo.
2. **Directorio de oficinas** como documento del corpus (quién atiende becas, registro, cambio de carrera): convertiría las abstenciones en «consulta en X, en el edificio Y».
3. **Léxico asistido**: proponer temas y anclas nuevos a partir de los títulos de artículo de cada documento ingerido, para revisión del administrador, en lugar de editarlos en código.
4. **Detector de homónimos por raíz** en la ingesta: listar raíces de anclas que aparecen en contextos ajenos al tema.
5. **Evaluación de la redacción** con un conjunto pequeño en vivo (≈ 30 turnos) puntuado con RAGAS o rúbrica humana en cada versión, para complementar al simulador.
6. **Sugerencias interactivas en la interfaz**: la oferta de aspectos ya es estructurada; mostrarla como botones reduciría la escritura en móvil.

---

## Verificación

```bash
cd scripts
PYTHONPATH=../backend/src python simulate_conversations.py --corpus-dir <PDF> --seed 7      # y --seed 13, --seed 29
PYTHONPATH=../backend/src python evaluate_conversations.py --corpus-dir <PDF>
PYTHONPATH=../backend/src python evaluate_conversations.py --corpus-dir <PDF> --benchmark conversation_benchmark_holdout.json
PYTHONPATH=../backend/src python evaluate_retrieval.py --corpus-dir <PDF>
cd ../backend && pytest tests/unit
```
