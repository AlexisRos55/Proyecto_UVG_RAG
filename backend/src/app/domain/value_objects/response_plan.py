from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.domain.value_objects.conversation_intent import ConversationIntent


class ResponseStyle(Enum):
    """Forma que debe tomar la respuesta fundamentada.

    Se decide antes de generar y viaja al prompt como directiva. No añade
    ninguna llamada: enmarca la que ya se hacía (US-2.2 sigue intacta). Cada
    directiva es deliberadamente breve: se paga en cada consulta que la usa.
    """

    DIRECT = "direct"
    YES_NO = "yes_no"
    LIST = "list"
    STEPS = "steps"
    COMPARISON = "comparison"
    DEFINITION = "definition"
    EXPLANATION = "explanation"
    SUMMARY = "summary"
    CONSEQUENCES = "consequences"
    RECOMMENDATION = "recommendation"
    ADVANTAGES = "advantages"
    TABLE = "table"
    FAQ = "faq"
    SECTIONED = "sectioned"
    OVERVIEW = "overview"
    RANKING = "ranking"
    EXAMPLE = "example"
    SIMPLER = "simpler"
    PER_ITEM = "per_item"
    UNSPECIFIED = "unspecified"

    @property
    def directive(self) -> str | None:
        """Instrucción en español para el prompt. `None` deja decidir al modelo."""
        return _DIRECTIVES.get(self)


_DIRECTIVES: dict[ResponseStyle, str] = {
    ResponseStyle.DIRECT: (
        "Responde de forma directa en una o dos frases. No uses listas ni encabezados: "
        "la pregunta busca un dato puntual."
    ),
    ResponseStyle.YES_NO: (
        "Empieza con «Sí», «No» o «Depende» y justifícalo en una o dos frases, nombrando "
        "el artículo que lo establece. Si depende de condiciones, enuméralas después."
    ),
    ResponseStyle.LIST: (
        "Presenta la respuesta como una lista con viñetas, un elemento por concepto, "
        "con el nombre del elemento en negrita seguido de su explicación."
    ),
    ResponseStyle.STEPS: (
        "Presenta la respuesta como una lista numerada de pasos en el orden en que el "
        "estudiante debe realizarlos."
    ),
    ResponseStyle.COMPARISON: (
        "Abre con una frase que diga la diferencia principal. Después, una tabla Markdown con una fila "
        "por opción y columnas para los criterios que la normativa permite comparar (a quién va dirigida, "
        "cobertura, requisitos clave, condiciones). Si falta un dato, escribe «No lo establece»; nunca lo "
        "infieras. Como máximo cuatro columnas y celdas de una línea: el detalle, fuera de la tabla. "
        "Cierra con una línea que empiece por **En resumen:** y diga a quién le conviene cada opción."
    ),
    ResponseStyle.DEFINITION: (
        "Comienza con una definición breve (qué es, para quién es y qué ofrece). Añade un ejemplo solo "
        "si la normativa trae uno; no inventes cifras ni casos."
    ),
    ResponseStyle.EXPLANATION: (
        "Explica en prosa clara: primero la idea central en una frase, después el cómo "
        "y el porqué que establece la normativa."
    ),
    ResponseStyle.SUMMARY: (
        "Resume en un párrafo breve; si ayuda, añade hasta cinco viñetas con lo esencial. "
        "Omite los detalles secundarios."
    ),
    ResponseStyle.CONSEQUENCES: (
        "Explica qué consecuencia establece la normativa (sanción, penalización, pérdida "
        "de un beneficio) y en qué condiciones se aplica. Si hay un plazo o condición "
        "crítica, cierra con una línea que empiece por **Importante:**."
    ),
    ResponseStyle.RECOMMENDATION: (
        "Recomienda como lo haría un asesor: tu primera frase nombra una opción concreta. Primero la opción "
        "que corresponde al caso del estudiante "
        "según la normativa y por qué; después, en una frase, la alternativa y cuándo convendría. "
        "No recomiendes nada que la normativa no respalde."
    ),
    ResponseStyle.ADVANTAGES: (
        "Presenta los beneficios como lista con viñetas, cada uno con la condición que "
        "lo acompaña, si la hay."
    ),
    ResponseStyle.TABLE: "Presenta la información en una tabla Markdown con encabezado.",
    ResponseStyle.FAQ: (
        "Organiza la respuesta como preguntas frecuentes: cada pregunta en negrita, "
        "seguida de su respuesta breve."
    ),
    ResponseStyle.OVERVIEW: (
        "Da un panorama que oriente: abre con un resumen de una o dos frases que diga lo esencial para un "
        "estudiante del Campus Altiplano (qué opciones le aplican). Después, cada opción en una viñeta breve "
        "con su rasgo principal (a quién va dirigida y qué ofrece): primero las que aplican a campus externos; "
        "las de otros campus o modalidades, en un bloque final más breve. Como máximo ocho viñetas."
    ),
    ResponseStyle.RANKING: (
        "Tu primera frase nombra una opción concreta: cuál es, según lo que la normativa permite comparar, "
        "con su dato (por ejemplo, el porcentaje), o cuál corresponde al caso del estudiante si no hay dato "
        "comparable. Si hay dos o más opciones con dato, añade una tabla corta (opción, dato, condición "
        "principal). Si la normativa no da el dato para algunas, dilo al final en una frase."
    ),
    ResponseStyle.EXAMPLE: (
        "Ilustra con un caso práctico cómo se aplica lo que establece la normativa a un estudiante. "
        "Preséntalo como ilustración («por ejemplo, si un estudiante…») y no introduzcas cifras, "
        "plazos ni condiciones que la normativa no mencione."
    ),
    ResponseStyle.SIMPLER: (
        "El estudiante no entendió la explicación anterior. Explícalo de nuevo, más corto y con palabras "
        "sencillas: la idea central en una frase y después como máximo tres puntos clave. Simplifica las "
        "palabras, no los hechos: todo debe seguir apoyado en los fragmentos, sin cifras, lugares ni tareas "
        "que no aparezcan en ellos. Si usas un término del reglamento, explícalo entre paréntesis."
    ),
    ResponseStyle.PER_ITEM: (
        "La normativa trata esto en varios artículos, uno por programa o caso: organiza la "
        "respuesta por programa. Usa una tabla solo si cada dato está atribuido explícitamente "
        "a su programa en el texto; nunca completes una celda por inferencia."
    ),
    ResponseStyle.SECTIONED: (
        "El estudiante hizo varias preguntas: responde cada una en su propia sección "
        "con un encabezado corto, para que ninguna quede sin responder."
    ),
}


class SkillName(Enum):
    """Habilidades del agente. Todas son locales salvo las dos fundamentadas."""

    GROUNDED_ANSWER = "grounded_answer"
    INTRODUCE = "introduce"
    DECLARE_IDENTITY = "declare_identity"
    DECLARE_CAPABILITIES = "declare_capabilities"
    DECLARE_DOCUMENT_SCOPE = "declare_document_scope"
    EXPLAIN_HOW_IT_WORKS = "explain_how_it_works"
    EXPLAIN_USAGE = "explain_usage"
    EXPLAIN_PRIVACY = "explain_privacy"
    ACKNOWLEDGE = "acknowledge"
    CLOSE = "close"
    DISAMBIGUATE = "disambiguate"
    DECLINE_OUT_OF_DOMAIN = "decline_out_of_domain"
    DECLINE_PERSONAL_DATA = "decline_personal_data"
    HANDLE_NOISE = "handle_noise"
    RESIST_INJECTION = "resist_injection"
    CONTAIN_FRUSTRATION = "contain_frustration"
    RESUME_CONVERSATION = "resume_conversation"
    # Navegación documental (ADR-0013): se apoyan en el corpus y citan, pero no generan.
    DESCRIBE_DOCUMENT = "describe_document"
    OUTLINE_DOCUMENT = "outline_document"
    LOCATE_TOPIC = "locate_topic"
    RECOMMEND_DOCUMENTS = "recommend_documents"
    RELATE_DOCUMENTS = "relate_documents"

    @property
    def needs_generation(self) -> bool:
        return self is SkillName.GROUNDED_ANSWER

    @property
    def is_navigational(self) -> bool:
        return self in {
            SkillName.DESCRIBE_DOCUMENT,
            SkillName.OUTLINE_DOCUMENT,
            SkillName.LOCATE_TOPIC,
            SkillName.RECOMMEND_DOCUMENTS,
            SkillName.RELATE_DOCUMENTS,
        }


@dataclass(frozen=True, slots=True)
class ResponsePlan:
    """Decisión del agente antes de actuar.

    Es la salida de `ResponsePolicy`, una función pura: mismas entradas, misma
    decisión. Esa pureza es lo que permite comprobarla exhaustivamente y
    reportarla como resultado medible.

    Conserva la intención que la originó para que el catálogo pueda matizar la
    redacción sin multiplicar habilidades casi idénticas.
    """

    skill: SkillName
    intent: ConversationIntent
    style: ResponseStyle = ResponseStyle.UNSPECIFIED
    resolved_query: str | None = None

    @property
    def is_local(self) -> bool:
        """Respondida por el catálogo local: sin corpus, sin modelo y sin fuentes."""
        return not self.skill.needs_generation and not self.skill.is_navigational
