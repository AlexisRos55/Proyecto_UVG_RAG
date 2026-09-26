"""Vocabulario institucional: sinónimos, siglas y abreviaturas del dominio UVG.

Es conocimiento del dominio —cómo llaman los estudiantes a lo que el
reglamento llama de otra forma— y por eso vive aquí y no en un adaptador. Las
expansiones solo alimentan la búsqueda léxica con peso reducido: amplían lo que
se encuentra, pero nunca pesan más que lo que el estudiante escribió.
"""

from __future__ import annotations

import re

from app.domain.services.spanish_text import fold

# Cada grupo reúne formas que el corpus y los estudiantes usan para lo mismo.
# «beca» ↔ «ayuda financiera» es el caso que motivó la lista: el documento que
# regula las becas se llama «Reglamento de ayudas financieras» y en todo su
# articulado dice «ayuda financiera» mucho más que «beca».
_SYNONYM_GROUPS: tuple[tuple[str, ...], ...] = (
    ("beca", "ayuda financiera", "apoyo financiero"),
    ("credito educativo", "prestamo", "financiamiento"),
    ("colegiatura", "cuota de estudios", "mensualidad", "cuota mensual"),
    ("inscripcion", "inscribirse", "matricula", "asignacion de cursos"),
    ("graduacion", "obtencion de grado", "titulo", "acto de graduacion", "egreso"),
    ("retiro de cursos", "retirar un curso", "dar de baja"),
    ("sancion", "penalizacion", "castigo", "consecuencia"),
    ("requisitos", "condiciones", "requerimientos"),
    ("elecciones", "votacion", "sufragio", "planilla"),
    ("votar", "voto", "sufragio"),
    ("asociacion estudiantil", "asociacion de estudiantes", "junta directiva"),
    ("club", "agrupacion estudiantil", "grupo estudiantil"),
    ("examen de suficiencia", "suficiencia"),
    ("calendario", "fechas", "cronograma"),
    ("admision", "primer ingreso", "nuevo ingreso"),
    ("horas beca", "horas de servicio"),
    ("carne", "carnet"),
    ("fecha limite", "ultimo dia", "plazo"),
    ("duracion", "dura", "durar", "periodo"),
    ("miembro", "integrante", "socio", "membresia"),
    ("crear", "formar", "fundar", "conformacion", "constitucion"),
    ("incumplimiento", "no cumplir", "no cumplo"),
)

# Preguntas por consecuencias: el reglamento responde en sus artículos de
# penalizaciones y sanciones, que casi nunca repiten las palabras de la pregunta.
_CONSEQUENCE_QUESTION = re.compile(
    r"\bque\s+(?:pasa|sucede|ocurre)\s+si\b|\bconsecuencias?\b|\bpuedo\s+perder\b|\bpierdo\b|\bpierden?\b|\bperdida\b|\bme\s+quitan\b"
)
_CONSEQUENCE_EXPANSIONS = ("penalizaciones", "sanciones", "incumplimiento")

# Siglas del corpus y abreviaturas frecuentes en mensajes de estudiantes.
_ABBREVIATIONS: dict[str, str] = {
    "ave": "aprendizaje virtual de excelencia",
    "paa": "prueba de aptitud academica",
    "dgd": "direccion general de desarrollo",
    "fjbg": "fundacion juan bautista gutierrez",
    "ce": "campus externos",
    "daf": "direccion de ayudas financieras",
    "aeuvg": "asociacion de estudiantes universidad del valle",
    "cuae": "colegio universitario y asuntos estudiantiles",
    "sis": "sistema de registro academico",
    "insc": "inscripcion",
    "inscrip": "inscripcion",
    "reglam": "reglamento",
    "regl": "reglamento",
    "ing": "ingenieria",
    "lic": "licenciatura",
    "prof": "profesorado",
    "admin": "administracion",
    "info": "informacion",
    "mate": "matematica",
    "req": "requisitos",
}

# Escritura de chat: se reescribe antes de analizar para que no contamine la
# consulta con tokens que ningún documento contiene.
_CHAT_SPEAK = (
    (re.compile(r"\b(?:xq|pq|porq)\b"), "por que"),
    (re.compile(r"\bq\b"), "que"),
    (re.compile(r"\b(?:tmb|tb|tbn)\b"), "tambien"),
    (re.compile(r"\bk\b"), "que"),
    (re.compile(r"\bx\b"), "por"),
)

_FOLDED_GROUPS = tuple(tuple(fold(term) for term in group) for group in _SYNONYM_GROUPS)


def normalize_chat_speak(folded_text: str) -> str:
    for pattern, replacement in _CHAT_SPEAK:
        folded_text = pattern.sub(replacement, folded_text)
    return folded_text


def expansions_for(folded_query: str) -> tuple[str, ...]:
    """Sinónimos y desarrollos de siglas presentes en la consulta (ya plegada)."""
    found: list[str] = []
    padded = f" {folded_query} "
    for group in _FOLDED_GROUPS:
        if any(_contains_phrase(padded, term) for term in group):
            found.extend(term for term in group if not _contains_phrase(padded, term))
    for token in re.findall(r"[a-z0-9]+", folded_query):
        expansion = _ABBREVIATIONS.get(token)
        if expansion and expansion not in found:
            found.append(expansion)
    if _CONSEQUENCE_QUESTION.search(folded_query):
        found.extend(_CONSEQUENCE_EXPANSIONS)
    return tuple(dict.fromkeys(found))


def _contains_phrase(padded_text: str, phrase: str) -> bool:
    # Coincidencia por prefijo de palabra: «becas» contiene «beca», «inscribirme»
    # contiene «inscrib…». Así un grupo no necesita listar todas las flexiones.
    words = phrase.split()
    pattern = r"\b" + r"\w*\s+".join(re.escape(word[: max(4, len(word) - 2)]) for word in words) + r"\w*"
    return re.search(pattern, padded_text) is not None
