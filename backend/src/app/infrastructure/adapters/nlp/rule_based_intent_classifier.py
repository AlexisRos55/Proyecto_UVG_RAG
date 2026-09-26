from __future__ import annotations

import re
from typing import Final

from app.domain.services.conversation_lexicon import (
    DEEPEN,
    EXAMPLE,
    LATER,
    RESUME,
    WHY,
    detect_topics,
)
from app.domain.value_objects.conversation_intent import ConversationIntent, IntentClassification

# Confianzas por tipo de evidencia. Una coincidencia exacta con una fórmula social
# cerrada es mucho más segura que una palabra suelta dentro de una frase larga.
_EXACT: Final = 0.98
_STRONG: Final = 0.92
_MODERATE: Final = 0.78
_WEAK: Final = 0.55

# Léxico del dominio institucional. Su presencia es la señal más fuerte de que el
# mensaje es una consulta real, y tiene prioridad sobre cualquier regla social.
_DOMAIN_TERMS = re.compile(
    r"\b(beca|becas|reglamento|reglamentos|normativa|seguro|colegiatura|inscripcion|"
    r"inscribir|admision|graduacion|graduar|titulacion|curso|cursos|credito|creditos|"
    r"examen|examenes|nota|notas|promedio|indice|arancel|pago|pagos|descuento|"
    r"beneficio|beneficios|requisito|requisitos|tramite|constancia|certificacion|"
    r"campus|altiplano|facultad|carrera|semestre|matricula|ayuda\s+financiera|"
    r"estudiantil|academic\w*|universidad|uvg)\b"
)

# «¿Pierdo la beca si bajo mi promedio?» plantea un supuesto normativo, no pide
# ver el expediente: con un condicional o una consecuencia, el posesivo no convierte
# la consulta en una solicitud de datos personales.
_HYPOTHETICAL = re.compile(
    r"\bsi\s+(?:\w+\s+){0,3}(?:mi|mis)\b|\bpierdo\b|\bpuedo\s+perder\b|\bque\s+(?:pasa|sucede)\s+si\b"
    r"|\bme\s+quitan\b|\ben\s+caso\s+de\b"
)

# Solo posesivos: «me» en «cómo me inscribo» es reflexivo y describe un proceso
# general, no una consulta sobre el expediente del estudiante.
_PERSONAL_MARKERS = re.compile(
    r"\b(?:mi|mis)\s+(?:\w+\s+){0,2}(nota|notas|promedio|saldo|deuda|cuenta|expediente|"
    r"situacion|beca|inscripcion|horario|carne|estado|indice|pago|pagos)\b"
    r"|\bcuanto\s+(?:debo|me\s+falta|tengo\s+que\s+pagar)\b"
    r"|\b(?:tengo|gane|perdi)\s+(?:yo\s+)?(?:la\s+)?beca\b"
    r"|\bestoy\s+inscrito\b|\bme\s+gradu[oe]\b"
)

# (patrón, intención, confianza). El orden importa: se evalúa de arriba abajo.
_RULES: Final[tuple[tuple[re.Pattern[str], ConversationIntent, float], ...]] = (
    # --- Manipulación de instrucciones -------------------------------------
    (
        re.compile(
            r"\bignora\w*\s+(?:tus|las|todas)\b|\bolvida\w*\s+(?:todo|tus|las)\b"
            r"|\bactua\s+como\b|\beres\s+ahora\b|\bsystem\s*prompt\b"
            r"|\bignore\s+(?:all\s+)?(?:previous\s+)?instructions?\b"
        ),
        ConversationIntent.PROMPT_INJECTION,
        _STRONG,
    ),
    # --- Navegación documental (ADR-0013) ----------------------------------
    # Antes que DOCUMENT_SCOPE: «¿qué documentos hablan de becas?» pregunta por
    # un tema, mientras que «¿qué documentos manejas?» pregunta por el alcance.
    (
        re.compile(
            r"\b(?:que|cuales?)\s+(?:otros\s+)?(?:documentos?|reglamentos?|normativas?|normas?)\s+"
            r"(?:estan\s+)?relacionad\w*\b|\b(?:documentos?|reglamentos?)\s+relacionad\w*\s+con\b"
        ),
        ConversationIntent.RELATED_DOCUMENTS,
        _STRONG,
    ),
    (
        re.compile(
            r"\b(?:que|cual(?:es)?)\s+(?:documentos?|reglamentos?|normativas?|normas?)\s+(?:se\s+)?"
            r"(?:habla\w*|trata\w*|menciona\w*|regula\w*|cubre\w*|aplica\w*|dice\w*|contiene\w*|incluye\w*"
            r"|explica\w*|establece\w*|debo|tengo\s+que|puedo|me\s+sirve\w*|consult\w*)\b"
            r"|\bque\s+(?:debo|tengo\s+que|puedo)\s+(?:consultar|revisar|leer)\b"
            r"|\ben\s+que\s+(?:documento|reglamento)\b"
            # Elíptica, tras una pregunta por documentos: «¿y cuáles hablan de graduación?».
            r"|^(?:y\s+)?cuales\s+(?:hablan|tratan|mencionan|regulan)\b"
            r"|\bdonde\s+(?:puedo\s+)?(?:consulto|encuentro|busco|reviso|consultar|encontrar|buscar|revisar)\b"
        ),
        ConversationIntent.DOCUMENT_ROUTING,
        _STRONG,
    ),
    (
        re.compile(
            r"\bdonde\s+(?:se\s+)?(?:habla\w*|trata\w*|menciona\w*|aparece\w*|dice\w*|regula\w*|establece\w*|explica\w*)\b"
            r"|\b(?:que|cuales?)\s+(?:articulos?|capitulos?|secciones?|apartados?|partes?|paginas?)\s+"
            r"(?:se\s+)?(?:habla\w*|trata\w*|menciona\w*|regula\w*|establece\w*|aplica\w*|dice\w*|son\s+sobre|sobre|de\s+la|del|de\s+los)\b"
            r"|\ben\s+que\s+(?:articulo|capitulo|seccion|apartado|parte|pagina)\b"
        ),
        ConversationIntent.TOPIC_LOCATION,
        _STRONG,
    ),
    (
        re.compile(
            r"\b(?:cuales|que)\s+son\s+(?:los|las)\s+(?:capitulos|secciones|partes|apartados|articulos)\b"
            r"|\b(?:capitulos|indice|tabla\s+de\s+contenidos?|estructura)\s+(?:del|de\s+la|de\s+este|de\s+ese|de\s+esta)\b"
            r"|\bcomo\s+esta\s+(?:organizad|estructurad|dividid)\w*\b|\bque\s+capitulos\b"
            r"|\bcuantos\s+(?:capitulos|articulos)\b"
        ),
        ConversationIntent.DOCUMENT_STRUCTURE,
        _STRONG,
    ),
    (
        re.compile(
            r"^(?:hablame|cuentame|explicame|informame)\s+(?:de|del|sobre)\s+(?:el\s+|la\s+)?"
            r"(?:reglamento|documento|calendario|normativa|guia|folleto|proceso\s+de\s+admision)\b"
            r"|\b(?:de\s+)?que\s+(?:se\s+)?(?:trata|habla|va)\s+(?:(?:el|la|este|esta|ese|esa)\s+)?"
            r"(?:reglamento|documento|calendario|normativa|guia|folleto|archivo|pdf|proceso)\b"
            r"|^de\s+que\s+(?:se\s+)?trata$"
            r"|\b(?:resumen|resume\w*|resumir)\s+(?:de\s+)?(?:el|la|del|este|esta|ese|esa)\s+"
            r"(?:reglamento|documento|calendario|normativa|guia|proceso)\b"
            r"|\bque\s+(?:es|contiene)\s+(?:el|la|este|esta|ese|esa)\s+(?:reglamento|documento|calendario|normativa|guia|folleto)\b"
            r"|\btemas\s+principales\b|\bde\s+que\s+temas\b"
        ),
        ConversationIntent.DOCUMENT_OVERVIEW,
        _STRONG,
    ),
    # --- Meta: sobre el propio asistente ------------------------------------
    (
        re.compile(r"^(?:quien|que)\s+eres\b|^eres\s+(?:un|una|humano|robot|persona|real)\b|^(?:tu\s+)?nombre\b"),
        ConversationIntent.IDENTITY,
        _STRONG,
    ),
    (
        re.compile(
            r"\bque\s+(?:puedes|sabes|podes)\s+hacer\b|\ben\s+que\s+(?:me\s+)?(?:puedes\s+)?ayuda"
            r"|\bpara\s+que\s+sirves\b|\bcuales\s+son\s+tus\s+(?:funciones|capacidades)\b"
            r"|\bque\s+no\s+puedes\s+(?:hacer|responder)\b|\btus\s+limitaciones\b"
        ),
        ConversationIntent.CAPABILITIES,
        _STRONG,
    ),
    (
        re.compile(
            r"\bque\s+(?:informacion|documentos|datos)\s+(?:tienes|manejas|conoces)\b"
            # «¿Qué documentos piden?» pregunta por papeles de un trámite, no por el alcance del asistente.
            r"|\bque\s+documentos\b(?!\s+(?:me\s+|se\s+|te\s+)?(?:pide\w*|necesit\w*|requier\w*|debo|deb\w+|hay\s+que"
            r"|entreg\w*|present\w*|llev\w*|solicit\w*|ocup\w*|son\s+necesarios))"
            r"|\bsobre\s+que\s+puedes\s+responder\b"
            r"|\bcuantos\s+documentos\b"
        ),
        ConversationIntent.DOCUMENT_SCOPE,
        _STRONG,
    ),
    (
        re.compile(
            r"\bcomo\s+funciona\w*\b|\bde\s+donde\s+(?:sacas|obtienes|viene)\b"
            r"|\bque\s+son\s+(?:esas\s+)?(?:las\s+)?fuentes\b|\bpor\s+que\s+citas\b"
            r"|\bcomo\s+(?:es\s+que\s+)?(?:tu\s+)?(?:trabajas|respondes)\b"
            r"|\busas\s+(?:ia|inteligencia\s+artificial|chatgpt|claude)\b"
        ),
        ConversationIntent.HOW_IT_WORKS,
        _STRONG,
    ),
    (
        re.compile(
            r"\bcomo\s+(?:te\s+)?(?:debo\s+)?(?:pregunt|consult)\w*\b"
            r"|\bcomo\s+uso\b|\bcomo\s+funciona\s+esto\s+para\s+mi\b"
            r"|^(?:necesito\s+)?ayuda$|^ayudame$|^help$"
        ),
        ConversationIntent.USAGE_HELP,
        _STRONG,
    ),
    (
        re.compile(
            r"\bguardas\s+(?:lo\s+que|mis|mi)\b|\bes\s+privado\b|\bprivacidad\b"
            r"|\bquien\s+(?:ve|lee)\s+(?:esto|mis)\b|\bse\s+guarda\w*\s+mis\b"
        ),
        ConversationIntent.PRIVACY,
        _STRONG,
    ),
    # --- Social --------------------------------------------------------------
    (
        re.compile(
            r"^(?:hola|buenas|buenos\s+dias|buenas\s+tardes|buenas\s+noches|que\s+tal|"
            r"saludos|hey|holi|ola|hi|hello|buen\s+dia)(?:\s+\w+){0,2}$"
        ),
        ConversationIntent.GREETING,
        _EXACT,
    ),
    (
        re.compile(
            r"^(?:adios|hasta\s+luego|hasta\s+pronto|nos\s+vemos|bye|chao|chau|"
            r"me\s+voy|hasta\s+manana|buenas\s+noches\s+gracias)(?:\s+\w+){0,2}$"
        ),
        ConversationIntent.FAREWELL,
        _EXACT,
    ),
    (
        re.compile(
            r"^(?:muchas\s+|muchisimas\s+|mil\s+)?gracias(?:\s+\w+){0,3}$|^te\s+(?:lo\s+)?agradezco\b|^thank"
            r"|^(?:\w+\s+){0,2}(?:muchas\s+)?gracias$"
        ),
        ConversationIntent.THANKS,
        _EXACT,
    ),
    (
        re.compile(
            r"^(?:ok|oka|okay|vale|listo|entendido|entiendo|perfecto|excelente|genial|super|muy\s+bien|"
            r"va|dale|bien|de\s+acuerdo|correcto|claro|ya|aja|jaja\w*|sale|de\s+lujo)(?:\s+\w+){0,2}$"
        ),
        ConversationIntent.ACKNOWLEDGEMENT,
        _EXACT,
    ),
    (
        re.compile(r"^como\s+estas\b|^que\s+onda\b|^todo\s+bien\b|^como\s+te\s+va\b|^como\s+has\s+estado\b"),
        ConversationIntent.SMALL_TALK,
        _STRONG,
    ),
    (
        re.compile(
            r"\bno\s+(?:me\s+)?sirve\w*\b|\bno\s+(?:me\s+)?(?:entiendes|ayudas|funciona)\b"
            r"|\bes(?:t[oa])?\s+(?:es\s+)?(?:malisimo|pesimo|inutil|terrible)\b"
            r"|\bque\s+mal\b|\bya\s+te\s+pregunte\b|\bsiempre\s+dices\s+lo\s+mismo\b"
            r"|\bno\s+me\s+has\s+ayudado\b"
        ),
        ConversationIntent.FRUSTRATION,
        _MODERATE,
    ),
    # --- Fuera de dominio ----------------------------------------------------
    (
        re.compile(
            r"\bcapital\s+de\b|\bquien\s+(?:invento|escribio|gano|descubrio)\b"
            r"|\bescribe\w*\s+(?:un|una)\s+(?:poema|cuento|codigo|ensayo|cancion)\b"
            r"|\btraduce\w*\b|\bcalcula\w*\s+\d|\breceta\s+de\b|\bclima\b"
            r"|\bquien\s+es\s+(?:el\s+)?president\w*\b|\bcuanto\s+es\s+\d"
        ),
        ConversationIntent.OUT_OF_DOMAIN,
        _STRONG,
    ),
)

_MAX_AMBIGUOUS_WORDS: Final = 2
_NOISE = re.compile(r"^[^a-z0-9]*$|^(.)\1{3,}$|^[bcdfghjklmnpqrstvwxyz]{5,}$")


class RuleBasedIntentClassifier:
    """Clasificador determinista: léxico y reglas, sin llamadas al modelo.

    Implementa `IntentClassifierPort`. La decisión de no usar un modelo es de
    diseño y no de conveniencia: costaría una llamada por consulta —anulando el
    ahorro y chocando con ADR-0005 y NFR-02— y sería irreproducible, lo que
    impediría reportar precisión y exhaustividad sobre un conjunto etiquetado.

    Ante la duda nunca inventa: devuelve `INSTITUTIONAL_QUERY` con confianza baja
    para que la política enrute al comportamiento actual.
    """

    def classify(self, normalized_message: str) -> IntentClassification:
        # La puntuación interna no cambia la intención: «vale, gracias» es un acuse.
        message = " ".join(re.sub(r"[,;.:!¡¿?]+", " ", normalized_message).split())

        if not message or _NOISE.match(message):
            return IntentClassification(ConversationIntent.NOISE, _STRONG, "empty_or_noise")

        # El léxico institucional gana a cualquier regla social: «gracias, ¿qué becas
        # hay?» es una consulta, no un agradecimiento. Los temas del léxico
        # conversacional (elecciones, clubes, cuotas…) también cuentan como dominio.
        has_domain_terms = bool(_DOMAIN_TERMS.search(message)) or bool(detect_topics(message))

        if LATER.search(message) and len(message.split()) <= 6:
            return IntentClassification(ConversationIntent.FAREWELL, _STRONG, "later")
        if (WHY.match(message) or EXAMPLE.match(message)) and not has_domain_terms:
            return IntentClassification(ConversationIntent.FOLLOW_UP, _STRONG, "why_or_example")
        if RESUME.match(message) and not has_domain_terms:
            return IntentClassification(ConversationIntent.CONTINUATION, _STRONG, "resume")
        if DEEPEN.match(message):
            return IntentClassification(ConversationIntent.FOLLOW_UP, _STRONG, "deepen")

        if _PERSONAL_MARKERS.search(message) and not _HYPOTHETICAL.search(message):
            return IntentClassification(
                ConversationIntent.PERSONAL_DATA, _MODERATE, "personal_markers"
            )

        for pattern, intent, confidence in _RULES:
            if not pattern.search(message):
                continue
            if has_domain_terms and intent in _SOCIAL_INTENTS:
                # Hay saludo pero también sustancia: se trata como consulta.
                break
            if has_domain_terms and intent is ConversationIntent.HOW_IT_WORKS:
                # «¿Cómo funciona el crédito educativo?» pregunta por la normativa,
                # no por el asistente.
                continue
            return IntentClassification(intent, confidence, pattern.pattern[:40])

        words = message.split()
        if len(words) <= _MAX_AMBIGUOUS_WORDS and has_domain_terms:
            return IntentClassification(ConversationIntent.AMBIGUOUS, _MODERATE, "too_short")

        if not has_domain_terms and len(words) <= _MAX_AMBIGUOUS_WORDS:
            return IntentClassification(ConversationIntent.NOISE, _WEAK, "short_no_domain")

        return IntentClassification(
            ConversationIntent.INSTITUTIONAL_QUERY,
            _STRONG if has_domain_terms else _WEAK,
            "default_query",
        )


_SOCIAL_INTENTS: Final = frozenset(
    {
        ConversationIntent.GREETING,
        ConversationIntent.FAREWELL,
        ConversationIntent.THANKS,
        ConversationIntent.ACKNOWLEDGEMENT,
        ConversationIntent.SMALL_TALK,
    }
)
