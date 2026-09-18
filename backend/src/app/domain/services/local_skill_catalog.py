from __future__ import annotations

from collections.abc import Sequence

from app.domain.value_objects.conversation_context import ConversationContext
from app.domain.value_objects.conversation_intent import ConversationIntent
from app.domain.value_objects.response_plan import ResponsePlan, SkillName

ASSISTANT_NAME = "Asistente Inteligente de la Universidad del Valle de Guatemala"

_DOMAINS = (
    "reglamentos estudiantiles",
    "becas y ayudas financieras",
    "seguro estudiantil",
    "procesos de inscripción y admisión",
    "requisitos académicos",
)


def _join(items: Sequence[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return f"{', '.join(items[:-1])} y {items[-1]}"


def _introduce(context: ConversationContext) -> str:
    if context.already_introduced:
        return "Hola de nuevo. ¿Qué necesitas consultar?"
    return (
        f"Hola. Soy el {ASSISTANT_NAME}, Campus Altiplano.\n\n"
        f"Puedo ayudarte con {_join(_DOMAINS)}, siempre con base en los documentos "
        "oficiales de la universidad. Cada respuesta que doy indica de qué documento proviene.\n\n"
        "¿Qué necesitas saber?"
    )


def _acknowledge(context: ConversationContext, intent: ConversationIntent) -> str:
    if intent is ConversationIntent.SMALL_TALK:
        return (
            "Aquí estoy, listo para ayudarte. ¿Hay algo de la normativa o los beneficios "
            "de la universidad que quieras consultar?"
        )
    if intent is ConversationIntent.ACKNOWLEDGEMENT:
        return "Perfecto. Si necesitas algo más, aquí sigo."
    if context.turn_count <= 1:
        return "Con gusto. Si te surge cualquier otra duda, aquí estoy."
    return (
        "Con gusto. Si más adelante necesitas revisar otro reglamento o beneficio, "
        "solo pregúntame."
    )


def _declare_identity() -> str:
    return (
        f"Soy el {ASSISTANT_NAME}, Campus Altiplano.\n\n"
        "Respondo consultas sobre la documentación oficial de la universidad, y únicamente "
        "con base en ella: no improviso ni completo con conocimiento general. Por eso cada "
        "respuesta indica el documento del que proviene, para que puedas verificarla."
    )


def _declare_capabilities() -> str:
    bullets = "\n".join(f"- {domain.capitalize()}" for domain in _DOMAINS)
    return (
        "Puedo ayudarte con:\n\n"
        f"{bullets}\n\n"
        "Todo con base en los documentos oficiales indexados.\n\n"
        "**Lo que no puedo hacer:** consultar tu expediente personal. No tengo acceso a tus "
        "notas, tu estado de cuenta ni tu situación académica particular, y tampoco puedo "
        "realizar trámites: te informo qué dice la normativa, pero los procesos se gestionan "
        "en la oficina correspondiente."
    )


def _declare_document_scope(document_names: Sequence[str]) -> str:
    total = len(document_names)
    if total == 0:
        return (
            "Por el momento no tengo documentos indexados, así que no puedo responder "
            "consultas normativas todavía. En cuanto se carguen los documentos oficiales "
            "podré ayudarte."
        )

    preview = "\n".join(f"- {name}" for name in document_names[:6])
    remainder = total - min(total, 6)
    tail = f"\n\n…y {remainder} documento{'s' if remainder != 1 else ''} más." if remainder else ""
    return (
        f"Tengo indexado{'s' if total != 1 else ''} {total} documento{'s' if total != 1 else ''} "
        f"oficial{'es' if total != 1 else ''}, entre ellos:\n\n"
        f"{preview}{tail}\n\n"
        "Si lo que buscas no está en esta documentación, no podré responderlo."
    )


def _explain_how_it_works() -> str:
    return (
        "Funciono en tres pasos.\n\n"
        "1. **Busco** en los documentos oficiales de la universidad los fragmentos "
        "relacionados con tu pregunta.\n"
        "2. **Redacto** la respuesta usando únicamente esos fragmentos, nunca conocimiento "
        "general.\n"
        "3. **Verifico** la respuesta contra los fragmentos antes de mostrártela. Si alguna "
        "afirmación no queda respaldada, prefiero decirte que no lo sé.\n\n"
        "Por eso al final de cada respuesta aparecen las fuentes: son los documentos de los "
        "que salió la información, para que puedas comprobarla tú mismo."
    )


def _explain_usage(context: ConversationContext) -> str:
    base = (
        "Entre más concreta sea tu pregunta, mejor puedo buscar. Por ejemplo, en lugar de "
        "«becas», prueba con «¿qué requisitos tiene la beca de excelencia académica?».\n\n"
        "También puedes preguntarme por un proceso completo («¿cómo solicito una beca?») o "
        "pedirme que compare dos opciones."
    )
    if context.is_struggling:
        return (
            "Veo que no hemos dado con lo que buscas.\n\n"
            f"{base}\n\n"
            "Si aun así no aparece, puede que el documento no esté indexado todavía."
        )
    return base


def _explain_privacy() -> str:
    return (
        "Tus consultas quedan asociadas a tu cuenta institucional para que puedas ver tu "
        "historial. No tengo acceso a tu expediente, tus notas ni tu información financiera: "
        "solo leo los documentos oficiales que la universidad ha indexado."
    )


def _disambiguate(original: str) -> str:
    return (
        f"Puedo buscarlo mejor con un poco más de detalle. Con «{original}» hay varios temas "
        "posibles.\n\n"
        "Por ejemplo, podrías preguntarme por los **requisitos**, los **plazos**, los "
        "**montos** o el **procedimiento** de lo que te interesa."
    )


def _decline_out_of_domain() -> str:
    return (
        "Eso queda fuera de lo que puedo consultar. Respondo únicamente sobre la documentación "
        f"oficial de UVG Altiplano: {_join(_DOMAINS)}.\n\n"
        "¿Hay algo de esos temas en lo que pueda ayudarte?"
    )


def _decline_personal_data() -> str:
    return (
        "No tengo acceso a tu información personal: ni a tus notas, ni a tu estado de cuenta, "
        "ni a tu situación académica.\n\n"
        "Lo que sí puedo hacer es explicarte qué dice la normativa al respecto. Por ejemplo, "
        "qué plazos de pago existen o qué condiciones debe cumplir un estudiante. Para tu caso "
        "particular tendrías que consultar con la oficina correspondiente."
    )


def _handle_noise() -> str:
    return (
        "No logré entender el mensaje. ¿Puedes escribirlo de otra forma?\n\n"
        "Puedo ayudarte con reglamentos, becas, beneficios y procesos académicos."
    )


def _resist_injection() -> str:
    return (
        "Solo puedo responder consultas sobre la documentación oficial de la universidad, y "
        "eso no cambia según lo que se me pida.\n\n"
        "Si tienes una duda sobre reglamentos, becas o procesos académicos, con gusto la reviso."
    )


def _contain_frustration(context: ConversationContext) -> str:
    if context.is_struggling:
        return (
            "Entiendo, y lamento no haber dado con lo que necesitas.\n\n"
            "Puede que el documento no esté indexado todavía, o que ayude preguntarlo con otras "
            "palabras: entre más específica sea la consulta, mejor puedo buscar. Si aun así no "
            "aparece, conviene consultarlo directamente con la oficina correspondiente."
        )
    return (
        "Entiendo. Si algo no salió como esperabas, dime con más detalle qué necesitas y lo "
        "reviso de nuevo."
    )


class LocalSkillCatalog:
    """Respuestas que no requieren recuperación ni modelo.

    El criterio de admisión es estricto: una habilidad entra aquí **solo si su
    respuesta correcta es siempre la misma**, independientemente del usuario y del
    momento. En cuanto dependa del contenido de los documentos, pertenece a la
    habilidad fundamentada. Esa frontera es lo único que impide que esta capa
    empiece a responder cosas que debería estar citando.

    Es un servicio de dominio puro: los datos que necesita —como los nombres de
    los documentos indexados— se le entregan, nunca los va a buscar.
    """

    @staticmethod
    def respond(
        plan: ResponsePlan,
        context: ConversationContext,
        *,
        original_message: str = "",
        document_names: Sequence[str] = (),
    ) -> str:
        skill = plan.skill

        if skill is SkillName.INTRODUCE:
            return _introduce(context)
        if skill is SkillName.ACKNOWLEDGE:
            return _acknowledge(context, plan.intent)
        if skill is SkillName.CLOSE:
            return "Hasta luego. Aquí estaré cuando necesites consultar algo más."
        if skill is SkillName.DECLARE_IDENTITY:
            return _declare_identity()
        if skill is SkillName.DECLARE_CAPABILITIES:
            return _declare_capabilities()
        if skill is SkillName.DECLARE_DOCUMENT_SCOPE:
            return _declare_document_scope(document_names)
        if skill is SkillName.EXPLAIN_HOW_IT_WORKS:
            return _explain_how_it_works()
        if skill is SkillName.EXPLAIN_USAGE:
            return _explain_usage(context)
        if skill is SkillName.EXPLAIN_PRIVACY:
            return _explain_privacy()
        if skill is SkillName.DISAMBIGUATE:
            return _disambiguate(original_message)
        if skill is SkillName.DECLINE_OUT_OF_DOMAIN:
            return _decline_out_of_domain()
        if skill is SkillName.DECLINE_PERSONAL_DATA:
            return _decline_personal_data()
        if skill is SkillName.HANDLE_NOISE:
            return _handle_noise()
        if skill is SkillName.RESIST_INJECTION:
            return _resist_injection()
        if skill is SkillName.CONTAIN_FRUSTRATION:
            return _contain_frustration(context)

        raise ValueError(f"La habilidad {skill} no es local y no tiene respuesta en el catálogo.")
