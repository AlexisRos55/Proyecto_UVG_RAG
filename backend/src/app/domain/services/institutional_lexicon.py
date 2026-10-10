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
    # Quien dejó de estudiar y quiere volver: el calendario lo llama «inscripciones de reingreso».
    ("reingreso", "deje de estudiar", "volver a estudiar", "regresar a estudiar"),
    ("horas beca", "horas de servicio"),
    ("carne", "carnet"),
    ("fecha limite", "ultimo dia", "plazo"),
    ("duracion", "dura", "durar", "periodo"),
    ("miembro", "integrante", "socio", "membresia"),
    ("crear", "formar", "fundar", "conformacion", "constitucion"),
    ("incumplimiento", "no cumplir", "no cumplo"),
    # «¿Y si reprueba?» busca donde el reglamento dice «reprobación o retiro de cursos».
    ("reprobacion", "reprobar", "reprueba", "repruebo", "reprobado", "cursos reprobados"),
    ("aprobo", "aprobado", "autorizo", "autorizado", "elaboro"),
    # Los folletos dicen «Inversión: Inscripción Q.807.00»; el estudiante pregunta «cuánto cuesta».
    ("costo", "cuesta", "precio", "inversion", "cuanto se paga"),
    ("inician", "empiezan", "comienzan", "inicio", "comienzo", "arrancan"),
    ("reconsideracion", "revision", "revisen", "reconsiderar", "revisar mi beca"),
    ("ser miembro", "unirme", "formar parte", "inscribirme en un club"),
    ("futbol", "deportivo", "deporte", "baloncesto", "voleibol"),
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
    (re.compile(r"\btons\b"), "entonces"),
    (re.compile(r"\b(?:xfa|xfavor|pls|plis|plz)\b"), "por favor"),
)

# Errores de escritura frecuentes con palabras del dominio («bcas», «becaz»,
# «inscripsion»). Se corrigen solo hacia esta lista cerrada y a distancia de una
# edición: una lista abierta convertiría «clave» en «clase» o «cursor» en «curso».
_DOMAIN_WORDS = (
    "beca", "becas", "requisitos", "requisito", "inscripcion", "admision", "credito", "educativo", "reglamento",
    "elecciones", "calendario", "graduacion", "matricula", "promedio", "cobertura", "colegiatura", "mensualidad",
    "licenciatura", "ingenieria", "maestria", "suficiencia", "solicitud", "financiera", "financieras",
    "asociacion", "carrera", "carreras", "estudiante", "universidad", "reprobar", "beneficios", "beneficio",
)
_DOMAIN_SET = frozenset(_DOMAIN_WORDS)
# Faltas que no son de una sola edición o que afectan palabras comunes.
_SPELLING = {"saver": "saber", "nesesito": "necesito", "nesecito": "necesito", "kiero": "quiero", "aser": "hacer",
             "ise": "hice", "ola": "hola", "q": "que", "xfa": "por favor", "porfa": "por favor"}

_FOLDED_GROUPS = tuple(tuple(fold(term) for term in group) for group in _SYNONYM_GROUPS)


# Abreviaturas inequívocas que se escriben en lugar de la palabra («req beca», «info cred educ»).
# Se reescriben en el texto (no solo como expansión) porque son lo único que el estudiante dijo.
_INLINE_ABBREVIATIONS = {
    "req": "requisitos", "reqs": "requisitos", "insc": "inscripción", "inscrip": "inscripción", "cred": "crédito",
    "educ": "educativo", "info": "información", "reglam": "reglamento", "1er": "primer", "1ro": "primero",
    "pq": "porque", "xq": "porque", "tmb": "también", "tb": "también", "x": "por",
}


def expand_abbreviations(text: str) -> str:
    def fix(match: re.Match[str]) -> str:
        return _INLINE_ABBREVIATIONS.get(match.group(0).lower(), match.group(0))

    return re.sub(r"\b\w+\b", fix, text)


def correct_typos(text: str) -> str:
    """«quiero saver de las bcas» → «quiero saber de las becas».

    Solo palabras de cuatro letras o más que no son ya una palabra del dominio, y
    solo si la corrección es única: ante la duda se deja lo que se escribió.
    """

    def fix(match: re.Match[str]) -> str:
        word = match.group(0)
        folded = fold(word)
        if folded in _SPELLING:
            return _SPELLING[folded]
        if len(folded) < 4 or folded in _DOMAIN_SET:
            return word
        candidates = sorted({target for target in _DOMAIN_WORDS if _one_edit(folded, target)})
        if len({c.rstrip("s") for c in candidates}) == 1:
            # «becaz» está a una edición de «beca» y de «becas»: es la misma palabra.
            return min(candidates, key=lambda c: (abs(len(c) - len(folded)), c))
        return word

    return re.sub(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", fix, text)


def _one_edit(word: str, target: str) -> bool:
    """Una inserción, eliminación, sustitución o trasposición; «b» y «v» cuentan como iguales."""
    word, target = word.replace("v", "b"), target.replace("v", "b")
    if word == target:
        return True
    if abs(len(word) - len(target)) > 1 or word[0] != target[0]:
        return False
    if len(word) == len(target):
        diffs = [i for i, (a, b) in enumerate(zip(word, target, strict=True)) if a != b]
        if len(diffs) == 1:
            return True
        return len(diffs) == 2 and diffs[1] == diffs[0] + 1 and word[diffs[0]] == target[diffs[1]] and word[diffs[1]] == target[diffs[0]]
    short, long_ = (word, target) if len(word) < len(target) else (target, word)
    return any(long_[:i] + long_[i + 1 :] == short for i in range(len(long_)))


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
