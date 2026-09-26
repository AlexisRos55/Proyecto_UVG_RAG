"""Vocabulario conversacional del dominio: temas, aspectos y marcadores de discurso.

La resolución de referencias necesita distinguir tres cosas en un mensaje:

- **Tema**: de qué se habla («becas», «elecciones», «clubes»). Un mensaje que
  nombra un tema es autosuficiente y puede cambiar el tema de la conversación.
- **Aspecto**: qué se quiere saber del tema («requisitos», «cuánto cubre»,
  «hasta cuándo»). Un mensaje que solo trae un aspecto depende del tema activo.
- **Marcadores de discurso**: anáforas («esa», «eso»), continuación
  («continuemos», «profundiza») y navegación («el siguiente artículo»).

Es conocimiento del dominio, no de una tecnología, y por eso vive aquí. Todo se
evalúa sobre texto plegado (minúsculas, sin tildes).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain.services.spanish_text import analyze


@dataclass(frozen=True, slots=True)
class Topic:
    key: str
    label: str
    trigger: re.Pattern[str]
    retrieval_terms: str
    # Palabras con que el estudiante alude a un elemento concreto del tema
    # («la beca» cuando se habla de la Beca Despega).
    category_words: tuple[str, ...] = ()
    # Palabras que identifican el tema en un texto: la evidencia que no contiene
    # ninguna no es de él. Explícitas, porque los términos de búsqueda incluyen
    # descriptores («cobertura», «médica») que aparecen en cualquier otro tema.
    anchors: str = ""


@dataclass(frozen=True, slots=True)
class Aspect:
    key: str
    trigger: re.Pattern[str]
    retrieval_terms: str
    # Cómo se nombra el aspecto en una frase: «no establece {phrase}».
    phrase: str
    # Palabras que, en el título de un artículo, delatan que el artículo trata el aspecto.
    title_words: tuple[str, ...] = ()


def _rx(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern)


# Necesidad económica dicha con palabras del estudiante: apunta a becas y crédito.
_FINANCIAL_NEED = (
    r"\bno\s+(?:se\s+si\s+)?me\s+alcanza\b|\bno\s+(?:puedo|podre|podria)\s+pagar\b|\bno\s+tengo\s+(?:dinero|para\s+pagar)\b"
    r"|\b(?:problemas|limitaciones|dificultades)\s+economic\w*|\bcomo\s+(?:voy\s+a\s+)?pagar\s+la\s+(?:carrera|universidad|u)\b"
)
FINANCIAL_NEED = re.compile(_FINANCIAL_NEED)

TOPICS: tuple[Topic, ...] = (
    Topic("horas_beca", "las horas beca", _rx(r"\bhoras?\s+becas?\b|\bhoras\s+de\s+servicio\b"),
          "horas beca horas de servicio", anchors="horas beca servicio"),
    Topic("credito", "el crédito educativo", _rx(r"\bcredito\s+educativo\b|\bprestamo\s+(?:educativo|estudiantil)\b"),
          "credito educativo", ("credito",), anchors="credito educativo"),
    Topic("becas", "las becas y ayudas financieras",
          # También la necesidad dicha con palabras propias: «no me alcanza para pagar la carrera».
          _rx(r"\bbecas?\b|\bbecad[oa]s?\b|\bayudas?\s+financieras?\b|\bapoyos?\s+(?:economicos?|financieros?)\b|"
              + _FINANCIAL_NEED),
          "becas ayudas financieras", ("beca", "programa", "ayuda"), anchors="beca ayuda financiera"),
    Topic("elecciones", "las elecciones estudiantiles",
          _rx(r"\belecci\w+|\bvotacion\w*|\bvotar\b|\bsufragio\b|\bplanillas?\b|\bcomicios\b|\belectoral\b"
              r"|\belig\w+|\belegi\w+|\brepresentantes?\s+estudiantiles?\b"),
          "elecciones proceso electoral", ("eleccion", "votacion"), anchors="eleccion electoral votacion sufragio planilla"),
    Topic("asociaciones", "las asociaciones estudiantiles",
          _rx(r"\basociaci\w+\s+(?:de\s+)?estudiant\w+|\basociaciones\b|\baeuvg\b"),
          "asociacion de estudiantes junta directiva", ("asociacion",), anchors="asociacion"),
    Topic("clubes", "los clubes y agrupaciones", _rx(r"\bclub\w*|\bagrupaci\w+"), "clubes agrupaciones estudiantiles",
          ("club", "agrupacion"), anchors="club agrupacion"),
    Topic("admision", "la admisión",
          _rx(r"\badmisi\w+|\bprimer\s+ingreso\b|\bnuevo\s+ingreso\b|\bprueba\s+de\s+aptitud\b|\bpaa\b"),
          "admision primer ingreso", ("admision",), anchors="admision ingreso paa"),
    Topic("inscripcion", "la inscripción", _rx(r"\binscri\w+|\bmatricul\w+|\basignaci\w+\s+de\s+cursos\b"),
          "inscripcion asignacion de cursos", ("inscripcion",), anchors="inscripcion asignacion matricula"),
    Topic("graduacion", "la graduación", _rx(r"\bgradua\w+|\bceremonia\b"), "graduacion ceremonia de graduacion",
          anchors="graduacion"),
    # «Cuotas» a secas no abre el tema: «¿en cuántas cuotas se paga el crédito?»
    # habla de plazos del crédito, no de la cuota de estudios.
    Topic("pagos", "los pagos y cuotas de estudios",
          _rx(r"\bcuotas?\s+de\s+estudios?\b|\bcolegiatura\b|\brecargo\b|\bmensualidad\w*|\bpag\w*\s+(?:la\s+|mi\s+)?cuota\b"
              r"|\bpagos?\s+(?:de\s+)?(?:la\s+)?(?:universidad|colegiatura|inscripcion|matricula)\b"),
          "cuota de estudios pago recargo", anchors="cuota colegiatura recargo pago"),
    Topic("calendario", "el calendario académico",
          _rx(r"\bcalendario\b|\bferiados?\b|\basuetos?\b|\bfechas\s+importantes\b"),
          "calendario academico fechas", anchors="calendario feriado asueto"),
    Topic("suficiencia", "los exámenes de suficiencia", _rx(r"\bsuficiencia\b"), "examen de suficiencia",
          anchors="suficiencia"),
    Topic("retiro", "el retiro de cursos", _rx(r"\bretir\w*\s+(?:de\s+|un\s+|el\s+|los\s+)?cursos?\b"), "retiro de cursos",
          anchors="retiro"),
    Topic("seguro", "el seguro estudiantil",
          _rx(r"\bseguro\s+(?:medico|estudiantil|de\s+accidentes?)\b|\bseguro\b(?!\s+que)"),
          # «seguro» y «seguridad» comparten raíz (segur): el ancla usa las palabras
          # propias de una póliza para no aceptar «seguridad de la información».
          "seguro estudiantil cobertura medica accidentes", anchors="poliza aseguradora asegurado"),
    Topic("idiomas", "los cursos de idiomas", _rx(r"\bingles\b|\bidiomas?\b"), "centro de idiomas ingles",
          anchors="idioma ingles"),
    Topic("cambio_carrera", "el cambio de carrera",
          _rx(r"\bcambi\w*\s+(?:de\s+)?carrera\b|\btraslad\w*\s+(?:de\s+|a\s+otra\s+)?carrera\b|\botra\s+carrera\b"),
          "cambio de carrera", ("cambio",), anchors="carrera"),
    # Los nombres de carrera («Ingeniería», «Tecnología») no abren tema: califican
    # la pregunta en curso («¿cuál conviene más para Ingeniería?»). Ver CAREER_WORDS.
    Topic("carreras", "las carreras", _rx(r"\bcarreras?\b|\bpensum\b|\bplan\s+de\s+estudios?\b"),
          "carreras licenciatura ingenieria plan de estudios", ("carrera",), anchors="carrera pensum"),
)

ASPECTS: tuple[Aspect, ...] = (
    Aspect("cobertura", _rx(r"\bcubre\w*|\bcobertura\b|\bporcentaje\b|\bcuanto\s+(?:es|da|dan|otorga\w*|paga\w*)\b|\bmonto\b"),
           "cobertura porcentaje", "cuánto cubre", ("cobertura",)),
    Aspect("requisitos", _rx(r"\brequisitos?\b|\bque\s+(?:necesito|piden|se\s+necesita|debo\s+presentar)\b"
                             r"|\bquien(?:es)?\s+(?:puede|pueden)\s+(?:solicitar|aplicar|optar|obtener)\w*|\bdocumentos\s+(?:necesito|piden)\b"),
           "requisitos", "los requisitos", ("requisitos",)),
    Aspect("consecuencias", _rx(r"\bpierdo\b|\bpierde\w*|\bperder\w*|\bperdida\b|\bque\s+(?:pasa|sucede|ocurre)\s+si\b|\bsanci\w+|\bpenaliz\w+|\bincumpl\w+"
                                r"|\bbajo\s+(?:el\s+|mi\s+)?promedio\b|\brepruebo\b|\bno\s+(?:\w+\s+){0,2}cumpl\w*"),
           "penalizaciones sanciones incumplimiento", "consecuencias", ("penalizaciones", "sanciones", "faltas")),
    Aspect("plazo", _rx(r"\bhasta\s+cuando\b|\bcuando\b|\bplazos?\b|\bfechas?\b|\bfecha\s+limite\b|\bconvocatoria\w*"),
           "plazo fecha convocatoria", "plazos o fechas", ("plazo", "calendario", "convocatoria")),
    Aspect("procedimiento", _rx(r"\bcomo\s+(?:la\s+|lo\s+|las\s+|los\s+|me\s+)?(?:solicito|aplico|tramito|obtengo|inscribo|pido|consigo|hago)\b"
                                r"|\bque\s+(?:pasa|sigue|hago)\s+despues\b|\bsiguiente\s+paso\b|\bautorizaci\w+"
                                r"|\bpasos?\b|\bprocedimiento\b|\bproceso\s+para\b|\baplicar\b|\bsolicitar\w*|\bsolicitud\b"),
           "solicitud procedimiento", "el procedimiento", ("procedimiento", "solicitud")),
    Aspect("condiciones", _rx(r"\bcondiciones?\b|\bmantener\w*|\bconservar\w*|\brenova\w+|\bpromedio\b"), "condiciones mantener",
           "las condiciones para mantenerla", ("condiciones",)),
    Aspect("horario", _rx(r"\ba\s+que\s+hora\b|\bhorarios?\b"), "horario", "el horario", ("horario",)),
    Aspect("duracion", _rx(r"\bcuanto\s+(?:tiempo\s+)?(?:dura|tarda)\w*|\bduracion\b|\bcuantos\s+anos\b|\bvigencia\b|\bcada\s+cuanto\b"), "duracion plazo",
           "la duración", ("duracion", "vigencia")),
    Aspect("costo", _rx(r"\bcuanto\s+cuesta\b|\bcosto\w*|\bprecio\b|\bcuanto\s+se\s+paga\b"), "costo precio", "el costo"),
    Aspect("responsables", _rx(r"\bquien(?:es)?\s+(?:(?:la|lo|las|los)\s+)?(?:decide\w*|aprueba\w*|resuelve\w*|otorga\w*|se\s+encarga|autoriza\w*|evalua\w*|da|asigna\w*)"
                               r"|\bante\s+quien\b|\bdonde\s+(?:se\s+)?(?:presenta|entrega|solicita)\w*"),
           "comite consejo oficina encargado decide", "quién lo decide", ("comite", "consejo", "oficina")),
    Aspect("integrantes", _rx(r"\bmiembros?\b|\bintegrantes?\b|\bconformad\w+|\bcuantas\s+personas\b"),
           "integrantes conformada miembros", "quiénes lo integran", ("integrantes", "junta")),
    Aspect("definicion", _rx(r"\bque\s+(?:es|son|significa)\b|\ben\s+que\s+consiste\b"), "definicion", "en qué consiste",
           ("definiciones",)),
)

# «esa», «eso», «lo anterior»: la oración se apoya en algo ya dicho.
# Sin «esta/este»: plegados coinciden con el verbo «está» («¿dónde está la oficina?»).
ANAPHORA = re.compile(
    r"\b(?:esa|ese|eso|esas|esos|aquella|aquello|aquel|dicha|dicho|lo\s+anterior|la\s+anterior|el\s+anterior"
    r"|la\s+misma|el\s+mismo|lo\s+mismo|sus?)\b"
)
# Pronombre enclítico en un verbo: «solicitarla», «obtenerlas», «explícalo». Solo
# formas verbales: «escuela» o «regla» también terminan en «-la».
ENCLITIC = re.compile(
    r"\b\w{3,}(?:ar|er|ir)(?:la|lo|las|los)\b|\b(?:explica|detalla|resume|dime|aclara|amplia)(?:la|lo|las|los)\b"
)
# Pronombre átono antes del verbo: «lo pago», «la solicito» (primera persona,
# verbos en «-o» para no confundir «la ceremonia»); y, tras un interrogativo o con
# un verbo auxiliar, cualquier persona: «¿quién la da?», «¿quién las organiza?»,
# «¿dónde lo entrego?», «lo puedo cancelar».
PROCLITIC = re.compile(
    r"\b(?:lo|la|los|las)\s+(?:no\s+)?\w{3,}o\b"
    # «¿Quién la da?» admite cualquier verbo; tras otros interrogativos solo formas
    # en «-an/-en» («¿cómo la solicitan?»): «¿cuándo la ceremonia…?» no es pronombre.
    r"|\bquien(?:es)?\s+(?:me\s+|se\s+|te\s+)?(?:lo|la|los|las)\s+\w{2,}"
    r"|\b(?:como|donde|cuando|cuanto|que|por\s+que|para\s+que)\s+(?:me\s+|se\s+|te\s+)?(?:lo|la|los|las)\s+\w{2,}[ae]n\b"
    r"|\b(?:lo|la|los|las)\s+(?:puedo|puede|pueden|debo|debe|deben|tengo|tiene|necesito|necesita|hay\s+que)\b"
)
# «No entiendo»: la explicación anterior no llegó; se explica de otra forma.
CONFUSED = re.compile(
    r"^(?:y\s+|pero\s+|es\s+que\s+)?(?:no\s+(?:le\s+|lo\s+|la\s+)?(?:entiendo|entendi|comprendo|capto|me\s+queda\s+claro)"
    r"|no\s+me\s+quedo\s+claro|no\s+le\s+entiendo\s+a\s+nada.*"
    r"|(?:me\s+)?(?:lo\s+)?(?:puedes\s+)?explica\w*\s+(?:de\s+forma\s+|de\s+manera\s+)?(?:mas\s+)?(?:facil|simple|sencill\w+)"
    r"|(?:en\s+)?palabras\s+(?:mas\s+)?(?:simples|sencillas)|mas\s+(?:simple|sencillo|facil)|que\s+quiere\s+decir\s+eso)\b.*$"
)
# El estudiante no sabe por dónde empezar: se le orienta, no se busca.
LOST = re.compile(
    r"\b(?:estoy\s+(?:perdid|confundid|desorientad)\w*|no\s+se\s+(?:que|por\s+donde|como)\s+(?:preguntar|empezar|comenzar|hacer|buscar)"
    r"|por\s+donde\s+(?:empiezo|comienzo|empezamos|empiezo)|no\s+le\s+entiendo\s+a\s+nada|orientame|me\s+puedes\s+orientar"
    r"|necesito\s+(?:orientacion|que\s+me\s+orientes)|que\s+me\s+recomiendas\s+preguntar)\b"
)
# «Necesito ayuda con algo de la u», «tengo una duda»: pide ayuda sin decir con qué.
HELP_REQUEST = re.compile(
    r"^(?:hola|buenas(?:\s+tardes|\s+dias|\s+noches)?)?[\s,]*(?:necesito|ocupo|quisiera|quiero)\s+(?:una\s+|un\s+poco\s+de\s+)?ayuda"
    r"(?:\s+con\s+algo(?:\s+de\s+la\s+(?:u|uni|universidad))?)?(?:\s+por\s+favor)?$"
    r"|^(?:hola|buenas)?[\s,]*tengo\s+una\s+(?:duda|pregunta|consulta)$"
)
# «Volviendo a las becas, …»: regreso explícito a un tema anterior.
RETURN_TO = re.compile(r"^(?:y\s+)?(?:volviendo|regresando|retomando|volvamos|regresemos)\s+(?:a|al|con)\s+(?P<rest>.+)$")
# «Esa oficina», «esa beca de antes», «ese programa»: un sustantivo de categoría
# con demostrativo señala una entidad ya nombrada de esa clase.
CATEGORY_REFERENCE = re.compile(
    r"\b(?:esa|ese|aquella|aquel|dicha|dicho|la\s+misma|el\s+mismo)\s+"
    r"(?P<noun>becas?|programas?|creditos?|oficinas?|instancias?|consejos?|comites?|direccion|unidad|departamento|decanatura"
    r"|carreras?|campus|persona)\b"
)
# Continuar el hilo sin nuevo contenido: se retoma el tema activo.
RESUME = re.compile(
    r"^(?:y\s+)?(?:continuemos|continua\w*|sigamos|seguimos|sigue|retomemos|retoma\w*|en\s+que\s+(?:ibamos|quedamos)"
    r"|volvamos|donde\s+nos\s+quedamos)\b"
)
# Pedir más profundidad sobre lo último respondido.
DEEPEN = re.compile(
    r"^(?:y\s+)?(?:profundiza\w*|explica(?:lo|la|me(?:lo|la)?)?(?:\s+(?:mas|mejor))?|detalla\w*|amplia\w*"
    r"|(?:cuentame|dime|explicame|quiero\s+saber)\s+mas|mas\s+(?:sobre|de)\s+(?:eso|esa|ese|esto)"
    r"|(?:dame\s+)?mas\s+(?:detalles?|informacion)|(?:y\s+)?eso|continua|sigue\s+explicando)"
    # Solo si es todo el mensaje: «explícame los requisitos» es una pregunta nueva.
    r"(?:\s+(?:por\s+favor|porfa|sobre\s+eso|de\s+eso|un\s+poco))?$"
)
# Despedida con intención de volver: «continuemos mañana», «luego seguimos».
# Se evalúa antes que RESUME: «continuemos mañana» no es retomar ahora.
LATER = re.compile(
    r"\b(?:continuemos|seguimos|sigamos|hablamos|retomamos|lo\s+vemos|lo\s+seguimos)\s+"
    r"(?:manana|luego|despues|mas\s+tarde|otro\s+dia|en\s+otro\s+momento)\b"
    r"|^(?:luego|despues|mas\s+tarde)\s+(?:seguimos|continuamos|hablamos|te\s+escribo|sigo)\b"
    r"|^hasta\s+manana\b|^nos\s+vemos\b|^(?:me\s+tengo\s+que\s+ir|tengo\s+que\s+irme)\b"
)
# «¿Por qué?», «¿cómo así?»: pedir la razón de lo último dicho.
WHY = re.compile(r"^(?:y\s+)?(?:por\s+que|como\s+asi|como\s+es\s+eso|y\s+eso\s+por\s+que)\s*$")
# «Dame un ejemplo»: ilustrar lo último dicho.
EXAMPLE = re.compile(r"^(?:y\s+)?(?:dame|pon|ponme|muestrame|tienes)\s+(?:un\s+|algun\s+)?ejemplos?\b|^(?:un\s+|por\s+)?ejemplo\s*$")
# Nombres de carrera: califican la pregunta en curso, no abren un tema nuevo.
CAREER_WORDS = re.compile(
    r"\b(ingenieria|tecnologia|administracion|mercadeo|educacion\s+fisica|educacion|informatica|agroforest\w*|agricola"
    r"|pecuaria|alimentos|mecatronica|turismo|musica|maestria|profesorado|licenciatura)\b"
)
# Navegación por artículos: «¿y el siguiente?», «el artículo anterior».
ARTICLE_STEP = re.compile(r"\b(?:el\s+)?(siguiente|proximo|anterior|previo)(?:\s+articulo)?\b")
# Palabras de petición que no aportan contenido a la búsqueda.
DISCOURSE_WORDS = frozenset(
    ["dame", "muestrame", "ponme", "ahora", "otra", "pregunta", "cambiando", "tema", "mas", "hablame", "hablar", "cuentame", "contar", "explicame", "explicar", "dime", "digame", "quisiera", "quiero", "gustaria", "conocer", "saber", "info", "informacion", "acerca", "respecto", "sobre", "necesito", "queria", "podrias", "puedes", "favor", "ayudame", "y", "entonces", "pues", "tambien", "ademas", "oye", "mira", "bueno", "ok", "vale", "antes", "volviendo", "regresando", "retomando"]
)
# «Háblame de…», «¿qué hay sobre…?»: petición de panorama de un tema.
OVERVIEW_REQUEST = re.compile(
    r"^(?:y\s+)?(?:hablame|cuentame|explicame|dime|informame)\s+(?:de|del|sobre|acerca)\b"
    r"|\b(?:que\s+hay|que\s+sabes|informacion)\s+(?:de|del|sobre|acerca)\b|\bque\s+(?:becas|beneficios|programas)\s+(?:hay|ofrece\w*|existen)\b"
)


# Raíces que aparecen en casi cualquier tema institucional: no sirven para
# anclar evidencia a uno («proceso electoral» no debe anclar a «proceso»).
_GENERIC_STEMS = frozenset(
    ["proces", "estudiantil", "academic", "estudiant", "universidad", "plan", "program", "cicl", "curs", "fech", "informacion"]
)


def anchor_terms(topic: Topic) -> tuple[str, ...]:
    """Raíces que identifican el tema: una evidencia que no contiene ninguna no es de él."""
    source = topic.anchors or topic.retrieval_terms
    return tuple(stem for stem in dict.fromkeys(analyze(source)) if stem not in _GENERIC_STEMS)


def detect_topics(folded: str) -> list[Topic]:
    return [topic for topic in TOPICS if topic.trigger.search(folded)]


def detect_aspects(folded: str) -> list[Aspect]:
    return [aspect for aspect in ASPECTS if aspect.trigger.search(folded)]


def topic_by_key(key: str | None) -> Topic | None:
    return next((topic for topic in TOPICS if topic.key == key), None)


def aspect_by_key(key: str | None) -> Aspect | None:
    return next((aspect for aspect in ASPECTS if aspect.key == key), None)
