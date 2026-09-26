"""Análisis léxico del español institucional, compartido por indexación y consulta.

Existe en el dominio, y no dentro del adaptador de búsqueda, por una razón de
corrección: el índice léxico y el analizador de consultas deben transformar el
texto **exactamente igual**. Si cada lado tuviera su propia normalización, una
diferencia mínima (una tilde, un plural) haría que «becas» dejara de coincidir
con «beca» sin que ninguna prueba lo detectara.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

_TOKEN = re.compile(r"[a-z0-9]+")

# Lista compacta y deliberadamente conservadora. Se excluyen de ella términos
# que en este dominio sí discriminan: «no» (exclusiones), números, «cada».
STOPWORDS = frozenset(
    ["a", "al", "algo", "algun", "alguna", "algunas", "alguno", "algunos", "ante", "antes", "aqui", "asi", "aun", "aunque", "bajo", "cabe", "como", "con", "contra", "cual", "cuales", "cuando", "de", "del", "desde", "donde", "dos", "durante", "e", "el", "ella", "ellas", "ellos", "en", "entre", "era", "eran", "es", "esa", "esas", "ese", "eso", "esos", "esta", "estan", "estas", "este", "esto", "estos", "fue", "fueron", "ha", "han", "hasta", "hay", "la", "las", "le", "les", "lo", "los", "mas", "me", "mi", "mis", "mucho", "muy", "nos", "o", "os", "otra", "otras", "otro", "otros", "para", "pero", "poco", "por", "porque", "que", "quien", "quienes", "se", "sea", "sean", "segun", "ser", "si", "sido", "sin", "sobre", "solo", "son", "su", "sus", "tal", "tambien", "te", "tiene", "tienen", "toda", "todas", "todo", "todos", "tu", "tus", "u", "un", "una", "unas", "uno", "unos", "y", "ya", "yo", "usted", "ustedes", "puedo", "puede", "pueden", "debo", "debe", "deben", "tengo", "quiero", "saber", "dime", "informacion", "favor", "hola", "gracias", "necesito", "cuanto", "cuanta", "cuantos", "cuantas", "cuando", "tener", "hacer", "pasa", "sucede", "ocurre", "existe", "existen", "quiero", "podria"]
)


def fold(text: str) -> str:
    """Forma canónica: NFKC (ligaduras «ﬁ» → «fi»), minúsculas y sin diacríticos.

    NFKC importa más de lo que parece: PyMuPDF entrega «suﬁciencia» con la
    ligadura tipográfica, y sin plegarla esa palabra nunca coincidiría con lo
    que escribe un estudiante.
    """
    compatible = unicodedata.normalize("NFKC", text).lower()
    decomposed = unicodedata.normalize("NFD", compatible)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


@lru_cache(maxsize=65536)
def light_stem(word: str) -> str:
    """Lematización ligera para español (enfoque de Savoy, 2002).

    Elimina número y género, y el infinitivo. En lenguas romances la
    lematización ligera rinde en recuperación casi igual que la agresiva y
    produce muchas menos colisiones, que es la propiedad que importa en texto
    normativo. El infinitivo se trata porque es como preguntan los estudiantes
    («¿cómo puedo retirar…?») frente al sustantivo del reglamento («retiro»).
    El orden importa: primero el plural, para que «lugares» y «lugar» converjan.
    """
    if len(word) <= 3 or word.isdigit():
        return word
    if word.endswith("ces") and len(word) > 5:
        word = word[:-3] + "z"
    elif word.endswith("es") and len(word) > 5 and word[-3] not in "aeiou":
        word = word[:-2]
    elif word.endswith("s") and len(word) > 4:
        word = word[:-1]
    # «-er» exige más longitud: «primer», «mujer» o «taller» no son infinitivos.
    if (len(word) >= 5 and word[-2:] in ("ar", "ir")) or (len(word) >= 7 and word.endswith("er")):
        return word[:-2]
    # Desde cuatro letras, para que «pago» y «pagar» (o «voto» y «votar»)
    # converjan en la misma raíz de tres.
    if len(word) >= 4 and word[-1] in "aeo":
        word = word[:-1]
    return word


def tokenize(text: str) -> list[str]:
    """Tokens plegados, sin filtrar. Útil cuando la posición importa."""
    return _TOKEN.findall(fold(text))


def analyze(text: str) -> list[str]:
    """Términos indexables: plegados, sin palabras vacías y lematizados."""
    return [light_stem(token) for token in tokenize(text) if token not in STOPWORDS and (len(token) > 1 or token.isdigit())]


def content_words(text: str) -> list[str]:
    """Palabras con contenido, sin lematizar: sirven para mostrar y comparar títulos."""
    return [token for token in tokenize(text) if token not in STOPWORDS and len(token) > 2]


_ACRONYM_CANDIDATE = re.compile(r"^[A-ZÁÉÍÓÚÑ]{2,6}$")


def sentence_case(text: str, keep_upper: frozenset[str] = frozenset()) -> str:
    """«PROGRAMAS DE AYUDAS FINANCIERAS» → «Programas de ayudas financieras».

    Los documentos escriben los títulos en mayúsculas sostenidas; mostrarlos así
    en una cita se lee como un grito. Se conservan en mayúsculas las siglas
    conocidas (UVG, AVE) para no convertirlas en palabras.
    """
    words = text.split()
    if not words:
        return text
    rebuilt: list[str] = []
    for index, word in enumerate(words):
        core = word.strip("()-–,.;:")
        # Un numeral romano solo se reconoce tras «Capítulo», «Título»…: fuera de
        # ese contexto «CIVIL» o «MI» son palabras, no números.
        after_division = index > 0 and fold(words[index - 1]).strip(".:") in _DIVISION_WORDS
        if core and (core.upper() in keep_upper or (after_division and _ROMAN.fullmatch(core.upper()))):
            rebuilt.append(word.upper())
        else:
            rebuilt.append(word.lower())
    first = rebuilt[0]
    rebuilt[0] = first[:1].upper() + first[1:]
    return " ".join(rebuilt)


_DIVISION_WORDS = frozenset({"capitulo", "titulo", "seccion", "parte", "libro"})
_ROMAN = re.compile(r"M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})")


def looks_like_acronym(token: str) -> bool:
    return bool(_ACRONYM_CANDIDATE.match(token))
