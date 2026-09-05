# ADR-0002: Usar el SDK de Anthropic directamente, sin LangChain

**Estado:** Aceptado

**Fecha:** 2026-09-02

## Contexto

El documento del asesor menciona LangChain como parte del stack tecnológico original (junto con FastAPI). Sin embargo, el equipo decidió conscientemente no utilizarlo, sustituyéndolo por el SDK oficial de Anthropic invocado directamente desde los adaptadores de la capa de infraestructura.

## Decisión

No se utiliza LangChain en ninguna capa del sistema. Toda interacción con el LLM se realiza mediante el SDK oficial de Anthropic (`anthropic` para Python), encapsulado detrás de `LLMPort`.

## Alternativas consideradas

| Alternativa | Ventajas | Desventajas | Por qué se descartó |
|---|---|---|---|
| LangChain (como pide el documento original) | Abstracciones ya construidas para chains, prompts y memoria; posiblemente menos código propio | Superficie de API históricamente cambiante entre versiones (riesgo real de romper el proyecto a mitad de las 3 semanas disponibles); oculta el conteo exacto de tokens y llamadas, dificultando el control de costo (NFR-02); introduce una capa de abstracción genérica sobre un caso de uso muy específico (RAG institucional con verificación), que en la práctica hexagonal ya se resuelve con `LLMPort` | El control de costo/latencia y la estabilidad durante un desarrollo de 3 semanas pesan más que la conveniencia de abstracciones prearmadas |
| LlamaIndex | Alternativa similar a LangChain, orientada específicamente a RAG | Mismos riesgos de acoplamiento y de superficie de API cambiante que LangChain; añade una dependencia pesada para un pipeline que el equipo puede implementar directamente sobre ChromaDB y Sentence Transformers | Mismo argumento que LangChain: la arquitectura hexagonal ya provee la abstracción necesaria sin depender de un framework de terceros |
| SDK de Anthropic directo (elegido) | Control total sobre tokens, prompts, reintentos y manejo de errores; una dependencia menos que puede introducir breaking changes; el `LLMPort` ya aísla el detalle de "qué SDK se usa" | Hay que escribir a mano lo que LangChain daría "gratis" (p. ej. utilidades de prompting) | — |

## Consecuencias

**Positivas:**
- Visibilidad total y control directo sobre tokens consumidos por llamada, indispensable dado el presupuesto personal limitado (NFR-02).
- Una dependencia externa menos que pueda romper el proyecto con una actualización durante las 3 semanas de desarrollo.
- El prompt engineering y la estrategia de Chain-of-Verification quedan expresados explícitamente en código propio, auditable y explicable en la defensa de tesis (en vez de vivir dentro de la implementación interna de un framework de terceros).

**Negativas / trade-offs aceptados:**
- Se debe implementar a mano la construcción de prompts y el parseo de la salida estructurada del modelo, en vez de reutilizar utilidades de LangChain.
- Si en el futuro se requiere orquestación multi-paso compleja (p. ej. el `MultiCallVerificationAdapter` futuro), se implementará con código propio en vez de un framework de orquestación — decisión consistente y no contradictoria con esta ADR.

## Cómo se ajusta a las restricciones del proyecto

Dado el presupuesto de tiempo (~21 horas) y de dinero (personal, limitado), reducir dependencias externas reduce superficie de fallas inesperadas (p. ej. un breaking change de LangChain a mitad del desarrollo) y da control directo sobre el consumo de tokens, que es la variable de costo más sensible del proyecto. No modifica el alcance funcional: el asesor especificó *qué* debe hacer el agente (Claude, temperatura 0, Chain-of-Verification), no *cómo* se invoca el SDK.
