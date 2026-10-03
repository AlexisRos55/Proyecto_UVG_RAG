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
    r"\bno\s+(?:se\s+si\s+)?(?:me|nos)\s+alcanza\b|\bno\s+(?:puedo|podre|podria|podemos|pueden|puede)\s+(?:pagar|costear|cubrir)\b"
    r"|\bno\s+(?:tengo|tenemos|tienen)\s+(?:dinero|plata|pisto|lana|recursos|para\s+pagar)\b"
    r"|\b(?:problemas|limitaciones|dificultades|situacion)\s+economic\w*|\bcomo\s+(?:voy\s+a\s+)?pagar\s+la\s+(?:carrera|universidad|u)\b"
    r"|\b(?:bajos|escasos|pocos)\s+recursos\b|\bayuda\s+economica\b|\b(?:es|esta)\s+muy\s+car[ao]\b|\bnecesito\s+(?:dinero|plata)\b"
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
          _rx(r"\badmisi\w+|\bprimer\s+ingreso\b|\bnuevo\s+ingreso\b|\bprueba\s+de\s+aptitud\b|\bpaa\b"
              # La necesidad dicha con palabras propias: «quiero estudiar», «¿cómo entro a la UVG?».
              r"|^(?:yo\s+)?(?:quiero|quisiera|me\s+gustaria|deseo)\s+(?:estudiar|entrar|ingresar)(?:\s+(?:en|a)\s+(?:la\s+)?(?:u|uvg|uni|universidad|aqui))?$"
              r"|\b(?:entrar|ingresar|entro|ingreso)\s+(?:a|en)\s+(?:la\s+)?(?:u|uvg|uni|universidad)\b"
              r"|\b(?:salgo|saldre|voy\s+a\s+salir|termino|terminare|ya\s+termine)\s+(?:del|de)\s+(?:colegio|diversificado|bachillerato)\b"),
          "admision primer ingreso", ("admision",), anchors="admision ingreso paa"),
    # Quien dejó de estudiar y quiere volver: tema propio, porque «inscripción» en este corpus
    # también es la de planillas y clubes; el calendario fija las «inscripciones de reingreso».
    Topic("reingreso", "el reingreso",
          _rx(r"\breingres\w*|\bdeje\s+de\s+estudiar\b|\bvolver\s+a\s+estudiar\b"
              r"|\bregres\w*\s+a\s+(?:estudiar|la\s+(?:u|uni|universidad))\b"),
          "reingreso inscripciones de reingreso", anchors="reingreso"),
    Topic("inscripcion", "la inscripción", _rx(r"\binscri\w+|\bmatricul\w+|\basignaci\w+\s+de\s+cursos\b"),
          "inscripcion asignacion de cursos", ("inscripcion",), anchors="inscripcion asignacion matricula"),
    Topic("graduacion", "la graduación",
          _rx(r"\bgradua\w+|\bceremonia\b|\b(?:terminar|termino|acabar|acabo|cerrar|cierro)\s+(?:la|mi)\s+carrera\b|\bcierre\s+de\s+pensum\b"), "graduacion ceremonia de graduacion",
          anchors="graduacion"),
    # «Cuotas» a secas no abre el tema: «¿en cuántas cuotas se paga el crédito?»
    # habla de plazos del crédito, no de la cuota de estudios.
    Topic("pagos", "los pagos y cuotas de estudios",
          _rx(r"\bcuotas?\s+de\s+estudios?\b|\bcolegiatura\b|\brecargo\b|\bmensualidad\w*|\bpag\w*\s+(?:la\s+|mi\s+)?cuota\b"
              r"|\bpagos?\s+(?:de\s+)?(?:la\s+)?(?:universidad|colegiatura|inscripcion|matricula)\b"),
          "cuota de estudios pago recargo", anchors="cuota colegiatura recargo pago"),
    Topic("calendario", "el calendario académico",
          _rx(r"\bcalendario\b|\bferiados?\b|\basuetos?\b|\bfechas\s+importantes\b|\b(?:inici\w+|empiez\w+|comienz\w+|arranc\w+)\s+(?:las\s+)?clases\b"),
          "calendario academico fechas", anchors="calendario feriado asueto"),
    Topic("suficiencia", "los exámenes de suficiencia", _rx(r"\bsuficiencia\b"), "examen de suficiencia",
          anchors="suficiencia"),
    Topic("retiro", "el retiro de cursos",
          _rx(r"\bretir\w*\s+(?:de\s+|un\s+|el\s+|los\s+)?cursos?\b|\bretirarme\b|\bretirarse\b|\bme\s+retiro\b"
              r"|\b(?:salir\w*|dejar|abandonar|darme\s+de\s+baja)\s+(?:de\s+)?(?:un|el|una|la|mi|los)\s+(?:curso|clase|materia)s?\b"),
          "retiro de cursos",
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
    Aspect("cobertura", _rx(r"\bcubre\w*|\bcobertura\b|\bporcentaje\b|\bcuanto\s+(?:es|da|dan|otorga\w*|paga\w*)\b|\bmonto\b"
                            r"|\bcuanto\s+(?:me|nos|le|les)\s+(?:da\w*|dar\w*|cubr\w*|pag\w*|toca\w*)\b"),
           "cobertura porcentaje", "cuánto cubre", ("cobertura",)),
    Aspect("requisitos", _rx(r"\brequisitos?\b|\bque\s+(?:necesito|piden|se\s+necesita|debo\s+presentar)\b"
                             r"|\bquien(?:es)?\s+(?:puede|pueden)\s+(?:solicitar|aplicar|optar|obtener)\w*|\bdocumentos\s+(?:necesito|piden)\b"),
           "requisitos", "los requisitos", ("requisitos",)),
    Aspect("consecuencias", _rx(r"\bpierdo\b|\bpierde\w*|\bperder\w*|\bperdida\b|\bquita\w*|\bquitan\b|\bcancela\w*\s+(?:la|mi)\s+beca\b|\bretiran\s+(?:la|mi)\s+beca\b|\bque\s+(?:pasa|sucede|ocurre)\s+si\b|\bsanci\w+|\bpenaliz\w+|\bincumpl\w+"
                                r"|\bbajo\s+(?:el\s+|mi\s+)?promedio\b|\breprueb\w*|\breprob\w*|\bno\s+(?:\w+\s+){0,2}cumpl\w*"
                                # «¿Y si no pago?», «¿y si me atraso?»: el supuesto de incumplimiento.
                                r"|^(?:y\s+)?(?:que\s+pasa\s+)?si\s+(?:no\s+\w+|me\s+atraso|dejo\s+de\s+\w+)$"),
           "penalizaciones sanciones incumplimiento", "consecuencias", ("penalizaciones", "sanciones", "faltas")),
    Aspect("plazo", _rx(r"\bhasta\s+cuando\b|\bcuando\b|\bplazos?\b|\bfechas?\b|\bfecha\s+limite\b|\bconvocatoria\w*"),
           "plazo fecha convocatoria", "plazos o fechas", ("plazo", "calendario", "convocatoria")),
    Aspect("procedimiento", _rx(r"\b(?:como|donde)\s+(?:la\s+|lo\s+|las\s+|los\s+|me\s+|se\s+)?(?:solicito|aplico|tramito|obtengo|inscribo|pido|consigo|hago|solicita|tramita)\b"
                                r"|\bque\s+(?:pasa|sigue|hago)\s+despues\b|\bsiguiente\s+paso\b|\bautorizaci\w+"
                                r"|\bpasos?\b|\bprocedimiento\b|\bproceso\s+para\b|\baplicar\b|\bsolicitar\w*|\bsolicitud\b"
                                r"|\bque\s+(?:tengo|debo|hay|tiene)\s+que\s+hacer\b|\bpara\s+(?:pedir|obtener|tramitar|conseguir)\w*"),
           "solicitud procedimiento", "el procedimiento", ("procedimiento", "solicitud")),
    Aspect("condiciones", _rx(r"\bcondiciones?\b|\bmantener\w*|\bconservar\w*|\brenova\w+|\bpromedio\b"
                              r"|\bme\s+(?:dieron|otorgaron|aprobaron)\s+(?:la\s+)?beca\b|\bya\s+tengo\s+(?:la\s+)?beca\b"),
           "condiciones mantener",
           "las condiciones para mantenerla", ("condiciones",)),
    Aspect("horario", _rx(r"\ba\s+que\s+hora\b|\bhorarios?\b"), "horario", "el horario", ("horario",)),
    Aspect("duracion", _rx(r"\bcuanto\s+(?:tiempo\s+)?(?:dura|tarda)\w*|\bduracion\b|\bcuantos\s+anos\b|\bvigencia\b|\bcada\s+cuanto\b|\bvence\w*|\bvencimiento\b"), "duracion vigencia plazo maximo",
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

# El mismo aspecto se dice distinto según el tema: en el crédito, «¿cuánto?» es el interés,
# el plazo y las mensualidades, no un porcentaje de beca. Sirve para el seguimiento elíptico.
_TOPIC_ASPECT_TERMS = {
    ("credito", "cobertura"): "interes plazo mensualidades",
    ("credito", "costo"): "interes plazo mensualidades",
}


def aspect_terms(aspect: Aspect, topic_key: str | None) -> str:
    """Términos de búsqueda de un aspecto, con el vocabulario propio del tema si lo tiene."""
    extra = _TOPIC_ASPECT_TERMS.get((topic_key or "", aspect.key))
    return f"{aspect.retrieval_terms} {extra}" if extra else aspect.retrieval_terms


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
    r"^(?:y\s+|pero\s+|es\s+que\s+|nel\s+|ah\s+|mmm+\s+|uy\s+|pues\s+|la\s+verdad\s+|perdon\s+|disculpa\s+)?(?:no\s+(?:le\s+|lo\s+|la\s+)?(?:entiendo|entendi|comprendo|capto|me\s+queda\s+claro)"
    r"|no\s+me\s+quedo\s+claro|no\s+le\s+entiendo\s+a\s+nada.*"
    r"|(?:me\s+)?(?:lo\s+)?(?:puedes\s+)?explica\w*\s+(?:de\s+forma\s+|de\s+manera\s+)?(?:mas\s+)?(?:facil|simple|sencill\w+)"
    r"|(?:me\s+)?(?:lo\s+)?(?:puedes\s+)?explica\w*\s+(?:de\s+)?(?:otra\s+(?:forma|manera)|diferente|distinto|con\s+otras\s+palabras)"
    r"|(?:en\s+)?palabras\s+(?:mas\s+)?(?:simples|sencillas)|mas\s+(?:simple|sencillo|facil)|que\s+quiere\s+decir\s+eso)\b.*$"
)
# El estudiante no sabe por dónde empezar: se le orienta, no se busca.
LOST = re.compile(
    r"\b(?:estoy\s+(?:perdid|confundid|desorientad)\w*|no\s+se\s+(?:que|por\s+donde|como)\s+(?:preguntar|empezar|comenzar|hacer|buscar)"
    r"|por\s+donde\s+(?:empiezo|comienzo|empezamos|empiezo)|no\s+le\s+entiendo\s+a\s+nada|orientame|me\s+puedes\s+orientar"
    r"|necesito\s+(?:orientacion|que\s+me\s+orientes)|que\s+me\s+recomiendas\s+preguntar"
    # El que llega nuevo o angustiado sin decir de qué: «no entiendo cómo funciona la u», «estoy desesperada».
    r"|que\s+me\s+recomiendas(?:\s+hacer)?\s+primero|que\s+hago\s+primero|(?:estoy\s+)?desesperad[oa]"
    r"|ayudeme|ayudenme|ayuda\s+urgente|no\s+entiendo\s+(?:nada\s+)?(?:de\s+)?como\s+funciona"
    r"|^(?:y\s+)?(?:ahora\s+)?que\s+hago$)\b"
)
# Quien llega nuevo: se le orienta empezando por lo que necesita quien recién ingresa.
NEWCOMER = re.compile(
    r"\b(?:soy|somos)\s+nuev[oa]s?\b|\bacabo\s+de\s+(?:entrar|ingresar)\b|\brecien\s+(?:ingres|entr)\w*"
    r"|\bmi\s+primer\s+(?:dia|semestre|ciclo|ano)\b"
)
# Ya obtuvo la beca: lo que sigue es mantenerla, no solicitarla.
AWARDED = re.compile(r"\bme\s+(?:dieron|otorgaron|aprobaron)\s+(?:la\s+)?beca\b|\bya\s+tengo\s+(?:la\s+)?beca\b|\bgane\s+(?:la\s+)?beca\b")
# Cómo se siente quien escribe: cambia el tono de la respuesta, nunca lo que se busca.
MOODS = (
    ("angustia", re.compile(
        r"\burgente\b|\bdesesperad\w*|\bpreocupad\w*|\bangustiad\w*|\bnervios\w*|\basustad\w*|\bestresad\w*"
        r"|\bme\s+(?:la|lo)\s+van\s+a\s+quitar\b|\bme\s+van\s+a\s+quitar\b|\bno\s+se\s+que\s+hacer\b|!!!")),
    ("alegria", re.compile(
        r"\bme\s+(?:dieron|otorgaron|aprobaron|aceptaron)\b|\bgane\s+(?:la\s+)?beca\b|\bque\s+emocion\b|\bestoy\s+feliz\b"
        r"|\U0001F389|\U0001F973")),
)
# «Necesito ayuda con algo de la u», «tengo una duda»: pide ayuda sin decir con qué.
HELP_REQUEST = re.compile(
    r"^(?:hola|buenas(?:\s+tardes|\s+dias|\s+noches)?)?[\s,]*(?:necesito|ocupo|quisiera|quiero)\s+(?:una\s+|un\s+poco\s+de\s+)?ayuda"
    r"(?:\s+con\s+algo(?:\s+de\s+la\s+(?:u|uni|universidad))?)?(?:\s+por\s+favor)?$"
    r"|^(?:hola|buenas)?[\s,]*tengo\s+una\s+(?:duda|pregunta|consulta)$"
    r"|^(?:hola[\s,]*)?(?:me\s+)?(?:ayudas|puedes\s+ayudar(?:me)?|podrias\s+ayudarme|ayudame)(?:\s+(?:por\s+favor|porfa))?$"
)
# «¿Puedes resumir?», «en pocas palabras»: lo último dicho, en corto.
SUMMARIZE = re.compile(
    r"^(?:y\s+)?(?:(?:me\s+)?(?:lo\s+)?(?:puedes|podrias)\s+resumir\w*|resum[ei]\w*|dame\s+un\s+resumen|hazme\s+un\s+resumen"
    r"|en\s+resumen|en\s+pocas\s+palabras|version\s+corta|lo\s+mas\s+importante)(?:\s+(?:por\s+favor|porfa))?$"
)
# «Continúa», «sigue»: si no hubo pausa, es seguir explicando, no retomar un tema.
CONTINUE = re.compile(
    r"^(?:y\s+)?(?:continua|continue|continuemos|sigue|sigamos|seguimos|y\s+luego|que\s+mas|algo\s+mas"
    # «¿Y después?», «tons?»: qué sigue de lo que se estaba explicando.
    r"|despues|luego|entonces|y\s+entonces|que\s+sigue|y\s+que\s+sigue|y\s+ahora)(?:\s+(?:por\s+favor|porfa))?$|^y$"
)
# «¿Qué más debo saber?»: lo que falta del tema en foco, no la última pregunta repetida.
MORE_TO_KNOW = re.compile(
    r"^(?:y\s+)?(?:que\s+mas\s+(?:debo|deberia|necesito|tengo\s+que|hay\s+que)\s+saber|hay\s+algo\s+mas(?:\s+que\s+(?:deba|deberia)\s+saber)?"
    r"|algo\s+mas\s+que\s+(?:deba|deberia|tenga\s+que)\s+saber|que\s+(?:otra\s+cosa|otras\s+cosas)\s+(?:debo|deberia)\s+saber)$"
)
# Respuesta a un ofrecimiento («Si quieres, también puedo explicarte…»).
AFFIRM = re.compile(
    r"^(?:si|sip|sep|simon|claro|dale|va|sale|orale|de\s+una|por\s+favor|porfa|ok\s+va|ok\s+dale|si\s+claro|claro\s+que\s+si"
    r"|me\s+interesa|si\s+me\s+interesa|eso\s+mero)(?:\s+(?:por\s+favor|porfa|pls|plis|gracias))?$"
)
# Respuestas que no son pregunta («sí», «no», «ok», «xd», un emoji): nada que buscar.
BARE_REPLY = re.compile(
    r"^(?:si|no|nop|nel|simon|sip|sep|ok|oka|okay|okey|okis|oki|va|dale|sale|orale|exacto|correcto|claro|listo|vale|bien"
    r"|perfecto|entendido|ya|aja|xd+|lol|ja(?:ja)+\w*|je(?:je)+\w*|jsjs\w*|ah|eh|mmm+|ok\s+ok|ah\s+ok|ah\s+ya|ya\s+veo"
    r"|esta\s+bien|ta\s+bien|asi\s+esta\s+bien|de\s+acuerdo|cool|nice|great|sure|yes|thanks|ok\s+thanks|thank\s+you|"
    r"(?:ja(?:ja)+\w*\s+)?que\s+(?:emocion|bien|alegria|padre|chilero|nitido|buena\s+onda|bueno)|"
    # Negaciones y afirmaciones completas: «no por ahora», «sí porfa» sin nada ofrecido.
    r"no\s+(?:por\s+ahora|ahorita|todavia|gracias|es\s+necesario)|si\s+(?:porfa|por\s+favor|claro|gracias)|claro\s+que\s+si|)$"
)
DECLINE = re.compile(r"^(?:no|nop|nel|no\s+(?:por\s+ahora|ahorita|todavia|ya\s+no|asi\s+esta\s+bien|es\s+necesario)|asi\s+esta\s+bien|ya\s+no)$")
# «¿La primera?», «¿y la segunda?», «¿la otra?»: una opción de la lista recién dada.
ORDINAL = re.compile(
    r"\b(?:la|el|los|las)?\s*(?P<ordinal>primer[oa]?|segund[oa]|tercer[oa]?|cuart[oa]|ultim[oa])\b"
    # «Otra» solo con artículo: «la otra» es una opción; «otra pregunta» no.
    r"|\b(?:la|el)\s+(?P<other>otr[oa])\b"
)
ORDINAL_INDEX = {"primer": 0, "primero": 0, "primera": 0, "segundo": 1, "segunda": 1, "tercer": 2, "tercero": 2,
                 "tercera": 2, "cuarto": 3, "cuarta": 3, "ultimo": -1, "ultima": -1}
# «Ese reglamento», «este documento»: el documento en consulta.
DOCUMENT_REFERENCE = re.compile(r"\b(?:ese|este|dicho|el\s+mismo|aquel)\s+(?:reglamento|documento|calendario|folleto)\b")
# «Ese artículo», «este artículo»: el artículo en consulta.
ARTICLE_REFERENCE = re.compile(r"\b(?:ese|este|dicho|el\s+mismo|aquel)\s+articulo\b")
# Quién escribe, cuando no es un estudiante: cambia el trato, no el contenido.
AUDIENCES = (
    ("padre de familia", re.compile(
        r"\b(?:soy|como)\s+(?:(?:el|la|un|una)\s+)?(?:papa|mama|padre|madre|encargad[oa]|tutor[a]?)\b|\bpadre\s+de\s+familia\b"
        r"|\bmi\s+(?:hijo|hija)\b")),
    ("docente", re.compile(r"\b(?:soy|como)\s+(?:(?:un|una|el|la)\s+)?(?:docente|profesor[a]?|catedratic[oa]|maestr[oa])\b")),
    ("personal administrativo", re.compile(
        r"\b(?:soy|trabajo\s+en)\s+(?:(?:el|la|un|una)\s+)?(?:area\s+administrativ\w*|administrativ[oa]|personal\s+administrativo"
        r"|colaborador[a]?\s+de\s+la\s+universidad)\b")),
)
# «Soy papá de un estudiante, …»: la presentación no se busca en los reglamentos.
PERSONA_CLAUSE = re.compile(
    r"^\s*(?:hola[,\s]+|buen[oa]s?\s+\w+[,\s]+)?(?:soy|trabajo\s+en)\s+[^,.¿?]{2,60}?(?:,\s*|\.\s+|\s+y\s+(?=\w)|\s*(?=¿))",
    re.IGNORECASE,
)
# Mensaje escrito en inglés: se responde en español y se orienta al tema que mencione.
ENGLISH = re.compile(r"\b(?:what|how|when|where|which|who|is|are|the|can|do|does|i\s+need|please|about|scholarships?)\b")
SPANISH_HINT = re.compile(r"\b(?:que|como|cuando|donde|el|la|los|las|de|del|es|son|hay|quiero|puedo|necesito|para|por|una?|becas?)\b")
ENGLISH_TOPICS = (
    ("becas", r"scholarship|financial\s+aid|grant"), ("admision", r"admission|enroll\w*|apply"),
    ("calendario", r"calendar|schedule|classes\s+start"), ("credito", r"loan"), ("carreras", r"degree|major|program"),
)
# Cortesías al inicio y al final de un mensaje largo: no son la pregunta.
COURTESY = re.compile(
    r"^\s*(?:(?:hola|buen(?:as|os)?\s+(?:dias|tardes|noches)|buen\s+dia|que\s+tal|saludos)[\s,.!]*)+"
    r"(?:(?:mire|mira|fijese|disculpe|perdone)[\s,]+)?(?:le\s+escribo\s+porque|les\s+escribo\s+porque|te\s+escribo\s+porque)?\s*"
    r"|[\s,.]*(?:(?:muchas\s+)?gracias(?:\s+de\s+antemano)?|saludos(?:\s+cordiales)?|bendiciones|que\s+tenga\s+buen\s+dia)[\s.!]*$",
    re.IGNORECASE,
)
# Pedir que el asistente haga un trámite («¿me puedes inscribir?»): no puede; sí puede explicarlo.
ACTION_REQUEST = re.compile(
    r"\b(?:me\s+)?(?:puedes|podrias)\s+(?:inscribir|asignar|matricular|registrar|pagar|tramitar|solicitar|cancelar|"
    r"enviar|mandar|cambiar|reservar|aprobar|dar\s+de\s+baja)(?:me|la|lo|las|los)?\b"
    r"|\b(?:hazme|hagame|haz)\s+(?:el|la|mi)\s+(?:tramite|inscripcion|solicitud|pago)\b"
)
# Fórmulas de entrada que no son la pregunta: «Cambiando de tema, …», «Quiero saber…».
LEAD_IN = re.compile(
    r"^\s*(?:(?:y\s+)?(?:cambiando\s+de\s+tema|otra\s+pregunta|otra\s+cosa|una\s+pregunta|una\s+duda|una\s+consulta|ahora|oye|mira|bueno"
    # Disculpas y llamadas de atención de quien escribe con nervios o con respeto: «Disculpe la
    # molestia, …», «Perdón que pregunte, …», «Mire, disculpe, …». Pueden encadenarse.
    r"|disculpe?(?:\s+la\s+molestia)?|perd[oó]n(?:\s+(?:la\s+molestia|que\s+(?:pregunte|moleste|insista)))?"
    r"|con\s+todo\s+respeto|oiga|mire|f[ií]jese(?:\s+que)?|es\s+que|sorry)[\s,:]+)*"
    r"(?:(?:quiero|quisiera|queria|necesito|me\s+gustaria|me\s+interesa)\s+saber\s+|(?:me\s+puedes|puedes|podrias)\s+decir(?:me)?\s+)?",
    re.IGNORECASE,
)
# «Volviendo a las becas, …»: regreso explícito a un tema anterior.
RETURN_TO = re.compile(r"^(?:y\s+)?(?:volviendo|regresando|retomando|volvamos|regresemos)\s+(?:a|al|con)\s+(?P<rest>.+)$")
# «Esa oficina», «esa beca de antes», «ese programa»: un sustantivo de categoría
# con demostrativo señala una entidad ya nombrada de esa clase.
CATEGORY_REFERENCE = re.compile(
    r"\b(?:esa|ese|aquella|aquel|dicha|dicho|la\s+misma|el\s+mismo|(?=(?:la|el)\s+\w+\s+(?:de\s+antes|anterior)\b)(?:la|el))\s+"
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
EXAMPLE = re.compile(
    r"^(?:y\s+)?(?:dame|pon|ponme|muestrame|tienes|me\s+das|me\s+(?:puedes|podrias)\s+dar|me\s+pones)\s+(?:un\s+|algun\s+)?(?:ejemplos?|caso)\b"
    r"|^(?:un\s+|por\s+)?ejemplo\s*$"
    r"|^(?:y\s+)?(?:me\s+lo\s+)?explica\w*\s+con\s+(?:un\s+)?ejemplo\b|^(?:con\s+)?un\s+ejemplo\s+(?:por\s+favor|porfa)?$"
)
# Nombres de carrera: califican la pregunta en curso, no abren un tema nuevo.
CAREER_WORDS = re.compile(
    r"\b(ingenieria|tecnologia|administracion|mercadeo|educacion\s+fisica|educacion|informatica|agroforest\w*|agricola"
    r"|pecuaria|alimentos|mecatronica|turismo|musica|maestria|profesorado|licenciatura)\b"
)
# Navegación por artículos: «¿y el siguiente?», «el artículo anterior».
ARTICLE_STEP = re.compile(r"\b(?:el\s+)?(siguiente|proximo|anterior|previo)(?:\s+articulo)?\b")
# Palabras de petición que no aportan contenido a la búsqueda.
DISCOURSE_WORDS = frozenset(
    ["dame", "muestrame", "ponme", "ahora", "otra", "pregunta", "cambiando", "tema", "mas", "hablame", "hablar", "cuentame", "contar", "explicame", "explicar", "dime", "digame", "quisiera", "quiero", "gustaria", "conocer", "saber", "info", "informacion", "acerca", "respecto", "sobre", "necesito", "queria", "podrias", "puedes", "favor", "ayudame", "y", "entonces", "pues", "tambien", "ademas", "oye", "mira", "bueno", "ok", "vale", "antes", "volviendo", "regresando", "retomando",
     "mire", "fijese", "fijate", "oiga", "vea", "porfa", "xfa", "pls", "plis", "tons", "simon", "sip", "dale", "sale", "jaja", "jeje", "xd",
     "disculpe", "disculpa", "molestia", "perdon", "please", "thanks", "thank", "thx", "sorry", "cool"]
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
