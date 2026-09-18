from __future__ import annotations

import re
from typing import Final

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
            r"|\bque\s+documentos\b|\bsobre\s+que\s+puedes\s+responder\b"
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
        re.compile(r"^(?:muchas\s+|muchisimas\s+|mil\s+)?gracias(?:\s+\w+){0,3}$|^te\s+(?:lo\s+)?agradezco\b|^thank"),
        ConversationIntent.THANKS,
        _EXACT,
    ),
    (
        re.compile(
            r"^(?:ok|oka|okay|vale|listo|entendido|entiendo|perfecto|excelente|genial|"
            r"va|dale|bien|de\s+acuerdo|correcto|claro|ya|aja)(?:\s+\w+){0,2}$"
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
        message = normalized_message.strip()

        if not message or _NOISE.match(message):
            return IntentClassification(ConversationIntent.NOISE, _STRONG, "empty_or_noise")

        # El léxico institucional gana a cualquier regla social: «gracias, ¿qué becas
        # hay?» es una consulta, no un agradecimiento.
        has_domain_terms = bool(_DOMAIN_TERMS.search(message))

        if _PERSONAL_MARKERS.search(message):
            return IntentClassification(
                ConversationIntent.PERSONAL_DATA, _MODERATE, "personal_markers"
            )

        for pattern, intent, confidence in _RULES:
            if not pattern.search(message):
                continue
            if has_domain_terms and intent in _SOCIAL_INTENTS:
                # Hay saludo pero también sustancia: se trata como consulta.
                break
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
