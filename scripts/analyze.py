"""Análisis estadístico de la Fase V del protocolo (contrastación de H₁a, H₁b y H₁c).

Lee el reporte de `scripts/evaluate.py` y, si se proporciona, la exportación de la encuesta a
estudiantes (CSV o Excel de Google Forms / Microsoft Forms), y produce las tablas que van al
capítulo de Resultados:

    H₁a  Cada métrica RAGAS (media por pregunta, n = preguntas respondibles) > umbral (0.70).
         Prueba unilateral para una muestra: t de Student si Shapiro-Wilk no rechaza la
         normalidad, Wilcoxon de rangos con signo en caso contrario. Ajuste de Holm por las
         cuatro comparaciones. H₀a se rechaza solo si las cuatro métricas superan el umbral.
    H₁b  Latencia del prototipo (media de las repeticiones, por pregunta) < tiempo de atención
         manual reportado en la encuesta (minutos convertidos a segundos). Muestras
         independientes: t de Welch si ambas son normales, U de Mann-Whitney en caso contrario.
    H₁c  Utilidad percibida (media de los ítems U de cada estudiante) > punto neutro (3).
         Igual que H₁a: t para una muestra o Wilcoxon.

Además reporta estadísticos descriptivos, tamaño del efecto (d de Cohen o r = Z/√N), el alfa de
Cronbach de cada escala y la exactitud de abstención.

Formato esperado de la encuesta: cada pregunta analizable lleva un código entre corchetes al
inicio de su título, que es lo que el script busca en los encabezados de columna:
    [T1] tiempo de atención manual en minutos (número)
    [U1]…[Un] ítems de utilidad percibida (Likert 1-5)
    [F1]…[Fn] ítems de facilidad de uso percibida (Likert 1-5)
Las respuestas Likert pueden venir como número (1-5) o como texto («Totalmente de acuerdo»…).
Ver `scripts/encuesta_plantilla.csv`.

Uso:
    python scripts/analyze.py --reporte scripts/evaluation_report.json
    python scripts/analyze.py --reporte scripts/evaluation_report.json --encuesta respuestas.xlsx

Salida (carpeta `scripts/resultados/` por defecto):
    resultados.md     tablas listas para el documento
    resultados.json   todos los valores, para trazabilidad
"""

from __future__ import annotations

import argparse
import json
import math
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

DEFAULT_THRESHOLD = 0.70
DEFAULT_NEUTRAL = 3.0
DEFAULT_ALPHA = 0.05

METRIC_LABELS = {
    "faithfulness": "Fidelidad",
    "answer_relevancy": "Relevancia de la respuesta",
    "response_relevancy": "Relevancia de la respuesta",
    "llm_context_precision_with_reference": "Precisión del contexto",
    "context_precision": "Precisión del contexto",
    "context_recall": "Exhaustividad del contexto",
}

LIKERT_TEXT = {
    "totalmente en desacuerdo": 1,
    "muy en desacuerdo": 1,
    "en desacuerdo": 2,
    "ni de acuerdo ni en desacuerdo": 3,
    "neutral": 3,
    "neutro": 3,
    "de acuerdo": 4,
    "totalmente de acuerdo": 5,
    "muy de acuerdo": 5,
}

CODE_PATTERN = re.compile(r"^\s*\[([A-Za-z]+)(\d+)\]")

# Unidades de tiempo aceptadas en [T1], por prefijo de la palabra ya sin tildes, y su valor
# en minutos. Una palabra que no empiece por ninguno («m», «aprox») se toma como minutos.
TIME_UNIT_MINUTES = (
    ("min", 1.0),
    ("seg", 1 / 60),
    ("h", 60.0),
    ("d", 1440.0),
    ("sem", 10080.0),
)
_NUMBER = r"(\d+(?:\.\d+)?)"
TIME_PART_PATTERN = re.compile(_NUMBER + r"\s*([a-z]*)")
TIME_RANGE_PATTERN = re.compile(_NUMBER + r"\s*(?:-|–|a|o)\s*" + _NUMBER + r"\s*([a-z]*)")

# Opciones de [T1] del Anexo F y su conversión (metodología, «Conversión de unidades»):
# (prefijo normalizado de la opción, punto medio en minutos, límite inferior en minutos).
# El límite inferior es el del análisis de sensibilidad de H₁b; «más de 3 días hábiles» no
# tiene límite superior, así que su punto medio es su límite inferior. Los días hábiles se
# cuentan como días de 24 horas.
T1_RANGES = (
    ("menos de 30 minutos", 15.0, 0.0),
    ("entre 30 minutos y 1 hora", 45.0, 30.0),
    ("entre 1 y 4 horas", 150.0, 60.0),
    ("entre 4 y 24 horas", 840.0, 240.0),
    ("entre 1 y 3 dias habiles", 2880.0, 1440.0),
    ("mas de 3 dias habiles", 4320.0, 4320.0),
)
T1_PENDING = "aun no he recibido respuesta"
NEVER_CONSULTED = "nunca"


# --------------------------------------------------------------------------- utilidades


@dataclass
class Descriptives:
    n: int
    mean: float
    sd: float
    median: float
    q1: float
    q3: float
    minimum: float
    maximum: float


@dataclass
class TestResult:
    """Resultado de una prueba de hipótesis unilateral."""

    label: str
    n: int
    normality_p: float | None
    test: str
    statistic: float
    p_value: float
    effect_size: float
    effect_size_name: str
    p_adjusted: float | None = None
    reject_h0: bool = False
    descriptives: dict[str, Any] = field(default_factory=dict)


def describe(values: np.ndarray) -> Descriptives:
    return Descriptives(
        n=int(values.size),
        mean=float(np.mean(values)),
        sd=float(np.std(values, ddof=1)) if values.size > 1 else float("nan"),
        median=float(np.median(values)),
        q1=float(np.percentile(values, 25)),
        q3=float(np.percentile(values, 75)),
        minimum=float(np.min(values)),
        maximum=float(np.max(values)),
    )


def shapiro_p(values: np.ndarray) -> float | None:
    """p-valor de Shapiro-Wilk; None si no aplica (n < 3 o datos constantes)."""
    if values.size < 3 or np.ptp(values) == 0:
        return None
    return float(stats.shapiro(values).pvalue)


def is_normal(p: float | None, alpha: float) -> bool:
    return p is not None and p > alpha


def _wilcoxon_z(differences: np.ndarray) -> float:
    """Z de la aproximación normal de Wilcoxon (sin corrección por empates) para r = Z/√n."""
    d = differences[differences != 0]
    n = d.size
    if n == 0:
        return 0.0
    ranks = stats.rankdata(np.abs(d))
    w_plus = float(ranks[d > 0].sum())
    mean = n * (n + 1) / 4
    sd = math.sqrt(n * (n + 1) * (2 * n + 1) / 24)
    return (w_plus - mean) / sd


def one_sample_greater(label: str, values: np.ndarray, reference: float, alpha: float) -> TestResult:
    """H₁: la media (o mediana) de `values` es mayor que `reference`."""
    p_norm = shapiro_p(values)
    differences = values - reference
    if is_normal(p_norm, alpha):
        res = stats.ttest_1samp(values, reference, alternative="greater")
        sd = float(np.std(values, ddof=1))
        effect = (float(np.mean(values)) - reference) / sd if sd > 0 else float("nan")
        return TestResult(label, int(values.size), p_norm, "t de Student (una muestra)",
                          float(res.statistic), float(res.pvalue), effect, "d de Cohen",
                          descriptives=asdict(describe(values)))
    if np.all(differences == 0):
        return TestResult(label, int(values.size), p_norm, "Wilcoxon (rangos con signo)",
                          0.0, 1.0, 0.0, "r", descriptives=asdict(describe(values)))
    res = stats.wilcoxon(differences, alternative="greater", zero_method="wilcox")
    nonzero = int(np.count_nonzero(differences))
    effect = _wilcoxon_z(differences) / math.sqrt(nonzero) if nonzero else float("nan")
    return TestResult(label, int(values.size), p_norm, "Wilcoxon (rangos con signo)",
                      float(res.statistic), float(res.pvalue), effect, "r",
                      descriptives=asdict(describe(values)))


def two_sample_less(label: str, a: np.ndarray, b: np.ndarray, alpha: float) -> TestResult:
    """H₁: los valores de `a` (prototipo) son menores que los de `b` (atención manual)."""
    p_a, p_b = shapiro_p(a), shapiro_p(b)
    both_normal = is_normal(p_a, alpha) and is_normal(p_b, alpha)
    known = [p for p in (p_a, p_b) if p is not None]
    normality = min(known) if known else None
    descriptives = {"prototipo": asdict(describe(a)), "manual": asdict(describe(b))}
    if both_normal:
        res = stats.ttest_ind(a, b, equal_var=False, alternative="less")
        pooled = math.sqrt((np.var(a, ddof=1) + np.var(b, ddof=1)) / 2)
        effect = (float(np.mean(a)) - float(np.mean(b))) / pooled if pooled > 0 else float("nan")
        return TestResult(label, int(a.size + b.size), normality, "t de Welch",
                          float(res.statistic), float(res.pvalue), effect, "d de Cohen",
                          descriptives=descriptives)
    res = stats.mannwhitneyu(a, b, alternative="less", method="asymptotic")
    n1, n2 = a.size, b.size
    mean_u = n1 * n2 / 2
    sd_u = math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
    z = (float(res.statistic) - mean_u) / sd_u
    effect = z / math.sqrt(n1 + n2)
    return TestResult(label, int(n1 + n2), normality, "U de Mann-Whitney",
                      float(res.statistic), float(res.pvalue), effect, "r",
                      descriptives=descriptives)


def holm(p_values: list[float]) -> list[float]:
    """Ajuste de Holm (1979): p ordenados de menor a mayor, multiplicados por (m - i + 1)."""
    m = len(p_values)
    order = np.argsort(p_values)
    adjusted = np.empty(m)
    running_max = 0.0
    for rank, idx in enumerate(order):
        value = min(1.0, (m - rank) * p_values[idx])
        running_max = max(running_max, value)
        adjusted[idx] = running_max
    return adjusted.tolist()


def cronbach_alpha(items: pd.DataFrame) -> float | None:
    """α = k/(k-1) · (1 - Σσ²ᵢ / σ²ₜ), con varianzas muestrales (Cronbach, 1951)."""
    items = items.dropna()
    k = items.shape[1]
    if k < 2 or len(items) < 2:
        return None
    item_var = items.var(axis=0, ddof=1).sum()
    total_var = items.sum(axis=1).var(ddof=1)
    if total_var == 0:
        return None
    return float(k / (k - 1) * (1 - item_var / total_var))


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", str(text).strip().lower())
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def likert_value(raw: Any) -> float | None:
    if raw is None or (isinstance(raw, float) and math.isnan(raw)):
        return None
    if isinstance(raw, (int, float)):
        return float(raw) if 1 <= raw <= 5 else None
    text = _normalize(raw)
    match = re.match(r"^([1-5])\b", text)
    if match:
        return float(match.group(1))
    return float(LIKERT_TEXT[text]) if text in LIKERT_TEXT else None


def _unit_minutes(word: str) -> float:
    """Minutos que vale la unidad escrita tras un número; sin unidad reconocible, minutos."""
    for prefix, factor in TIME_UNIT_MINUTES:
        if word.startswith(prefix):
            return factor
    return 1.0


def t1_range(raw: Any) -> tuple[float, float] | None:
    """(punto medio, límite inferior) si la respuesta es una de las opciones del Anexo F."""
    if not isinstance(raw, str):
        return None
    text = _normalize(raw).rstrip(".")
    for prefix, midpoint, lower in T1_RANGES:
        if text.startswith(prefix):
            return midpoint, lower
    return None


def is_pending(raw: Any) -> bool:
    return isinstance(raw, str) and _normalize(raw).startswith(T1_PENDING)


def minutes_lower_bound(raw: Any) -> float | None:
    """Límite inferior del rango (análisis de sensibilidad); un número libre es su propio límite."""
    bounds = t1_range(raw)
    return bounds[1] if bounds else minutes_value(raw)


def minutes_value(raw: Any) -> float | None:
    """Tiempo de atención manual en minutos.

    Primero reconoce las opciones de rango del Anexo F y devuelve su punto medio
    («Entre 1 y 4 horas» → 150), como fija la metodología. «Aún no he recibido
    respuesta» no tiene un tiempo asignable y devuelve None (se reporta aparte).
    Solo si la respuesta no es una de esas opciones se interpreta como texto libre:

    La pregunta [T1] pide un número de minutos, pero un campo de texto libre recibe también
    «2 horas», «1 día», «1 h 30 min» o «de 2 a 3 días»: se convierte la unidad escrita (un día
    son 24 horas), se suman las partes y de un rango se toma el punto medio. Sin ningún
    número («no me respondieron») la respuesta se descarta.
    """
    if raw is None or (isinstance(raw, float) and math.isnan(raw)):
        return None
    if isinstance(raw, (int, float)):
        return float(raw) if raw >= 0 else None
    bounds = t1_range(raw)
    if bounds:
        return bounds[0]
    if is_pending(raw):
        return None
    text = re.sub(r"(?<=\d),(?=\d)", ".", _normalize(raw))
    if re.match(r"^-\s*\d", text):
        return None
    range_match = TIME_RANGE_PATTERN.search(text)
    if range_match:
        low, high = float(range_match.group(1)), float(range_match.group(2))
        return (low + high) / 2 * _unit_minutes(range_match.group(3))
    parts = TIME_PART_PATTERN.findall(text)
    if not parts:
        return None
    return sum(float(number) * _unit_minutes(unit) for number, unit in parts)


# --------------------------------------------------------------------------- carga de datos


def load_report(path: Path) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if "cases" not in report:
        raise SystemExit(f"{path} no parece un reporte de evaluate.py (falta 'cases').")
    if not any(case.get("ragas") for case in report["cases"]):
        raise SystemExit(
            f"{path} no trae métricas RAGAS por pregunta. Genera el reporte con la versión "
            "actual de scripts/evaluate.py (guarda las puntuaciones de cada pregunta)."
        )
    return report


def load_survey(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    return pd.read_csv(path)


def coded_columns(frame: pd.DataFrame, prefix: str) -> list[str]:
    selected = []
    for column in frame.columns:
        match = CODE_PATTERN.match(str(column))
        if match and match.group(1).upper() == prefix:
            selected.append((int(match.group(2)), column))
    return [column for _, column in sorted(selected)]


# --------------------------------------------------------------------------- análisis


def analyze(report: dict[str, Any], survey: pd.DataFrame | None, threshold: float,
            neutral: float, alpha: float) -> dict[str, Any]:
    answerable = [case for case in report["cases"] if case["expect_grounded"]]
    metrics = sorted({m for case in answerable for m in case.get("ragas", {})})

    # H₁a
    h1a: list[TestResult] = []
    for metric in metrics:
        values = np.array([case["ragas"][metric] for case in answerable
                           if case["ragas"].get(metric) is not None], dtype=float)
        if values.size:
            h1a.append(one_sample_greater(METRIC_LABELS.get(metric, metric), values, threshold, alpha))
    for result, adjusted in zip(h1a, holm([r.p_value for r in h1a]), strict=True):
        result.p_adjusted = adjusted
        result.reject_h0 = adjusted < alpha
    h0a_rejected = bool(h1a) and all(r.reject_h0 for r in h1a)

    # Latencia sobre las preguntas respondibles: las de abstención esperada suelen terminar
    # sin llamar al modelo y sesgarían la media hacia abajo.
    latencies = np.array([case["latency_mean_seconds"] for case in answerable
                          if case.get("latency_mean_seconds") is not None], dtype=float)
    accuracy = float(np.mean([case.get("decision_accuracy", 0.0) for case in report["cases"]]))

    output: dict[str, Any] = {
        "parametros": {"umbral_ragas": threshold, "punto_neutro": neutral, "alpha": alpha,
                       "modelo": report.get("model"), "repeticiones": report.get("repetitions")},
        "h1a": {"pruebas": [asdict(r) for r in h1a], "h0_rechazada": h0a_rejected},
        "latencia_prototipo": asdict(describe(latencies)) if latencies.size else None,
        "exactitud_abstencion": {"valor": accuracy, "n_preguntas": len(report["cases"])},
        "h1b": None,
        "h1b_sensibilidad": None,
        "h1c": None,
        "encuesta": None,
    }

    if survey is None:
        return output

    time_cols = coded_columns(survey, "T")
    u_cols = coded_columns(survey, "U")
    f_cols = coded_columns(survey, "F")
    if not time_cols or not u_cols:
        raise SystemExit("La encuesta debe tener una columna [T1] y columnas [U1], [U2]… "
                         "Revisa los códigos al inicio de los títulos de las preguntas.")
    if survey.empty:
        raise SystemExit("La encuesta no tiene respuestas: el archivo solo trae los encabezados "
                         "(¿es la plantilla?). Exporta las respuestas del formulario.")

    # H₁b usa solo a quienes han hecho al menos una consulta ([D2] distinto de «Nunca»):
    # en el formulario aplicado, quienes nunca consultaron también respondieron [T1].
    consulted = survey
    frequency_cols = [c for c in coded_columns(survey, "D") if CODE_PATTERN.match(str(c)).group(2) == "2"]
    if frequency_cols:
        consulted = survey[survey[frequency_cols[0]].map(lambda v: _normalize(v) != NEVER_CONSULTED if isinstance(v, str) else True)]
    t1 = consulted[time_cols[0]]
    pending = int(t1.map(is_pending).sum())
    manual_minutes = t1.map(minutes_value).dropna().astype(float)
    manual_seconds = manual_minutes.to_numpy() * 60
    manual_lower_seconds = t1.map(minutes_lower_bound).dropna().astype(float).to_numpy() * 60
    u_items = survey[u_cols].map(likert_value)
    f_items = survey[f_cols].map(likert_value) if f_cols else None
    usefulness = u_items.mean(axis=1, skipna=True).dropna().to_numpy()
    ease = f_items.mean(axis=1, skipna=True).dropna().to_numpy() if f_items is not None else None

    if latencies.size and manual_seconds.size:
        h1b = two_sample_less("Latencia del prototipo frente a la atención manual",
                              latencies, manual_seconds, alpha)
        h1b.reject_h0 = h1b.p_value < alpha
        output["h1b"] = asdict(h1b)
        # Análisis de sensibilidad (VIII.G.3): el mismo contraste con el límite inferior de
        # cada rango, la estimación más baja posible de la espera.
        if manual_lower_seconds.size and np.ptp(manual_lower_seconds) > 0:
            low = two_sample_less("Sensibilidad: límite inferior de cada rango",
                                  latencies, manual_lower_seconds, alpha)
            low.reject_h0 = low.p_value < alpha
            output["h1b_sensibilidad"] = asdict(low)

    if usefulness.size:
        h1c = one_sample_greater("Utilidad percibida", usefulness, neutral, alpha)
        h1c.reject_h0 = h1c.p_value < alpha
        output["h1c"] = asdict(h1c)

    output["encuesta"] = {
        "respuestas": len(survey),
        "tiempo_manual_minutos": asdict(describe(manual_minutes.to_numpy())) if manual_minutes.size else None,
        "respuestas_tiempo_validas": int(manual_minutes.size),
        "con_consulta_previa": len(consulted),
        "sin_respuesta_aun": pending,
        "utilidad": asdict(describe(usefulness)) if usefulness.size else None,
        "facilidad_de_uso": asdict(describe(ease)) if ease is not None and ease.size else None,
        "alfa_cronbach_utilidad": cronbach_alpha(u_items),
        "alfa_cronbach_facilidad": cronbach_alpha(f_items) if f_items is not None else None,
        "items_utilidad": [str(c) for c in u_cols],
        "items_facilidad": [str(c) for c in f_cols],
    }
    return output


# --------------------------------------------------------------------------- reporte


def _f(value: float | None, digits: int = 3) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    return f"{value:.{digits}f}"


def _p(value: float | None) -> str:
    if value is None:
        return "—"
    return "< 0.001" if value < 0.001 else f"{value:.3f}"


def to_markdown(result: dict[str, Any]) -> str:
    params = result["parametros"]
    lines = ["# Resultados del análisis estadístico", "",
             (f"Nivel de significancia α = {params['alpha']}; umbral RAGAS = {params['umbral_ragas']}; "
             f"punto neutro Likert = {params['punto_neutro']}; modelo = {params['modelo']}; "
             f"repeticiones por pregunta = {params['repeticiones']}."), ""]

    lines += ["## H₁a — Calidad técnica (RAGAS)", "",
              "| Métrica | n | Media | DE | Mediana | Shapiro-Wilk p | Prueba | Estadístico | p | p (Holm) | Efecto | ¿Supera 0.70? |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for t in result["h1a"]["pruebas"]:
        d = t["descriptives"]
        lines.append(f"| {t['label']} | {t['n']} | {_f(d['mean'])} | {_f(d['sd'])} | {_f(d['median'])} | "
                     f"{_p(t['normality_p'])} | {t['test']} | {_f(t['statistic'])} | {_p(t['p_value'])} | "
                     f"{_p(t['p_adjusted'])} | {t['effect_size_name']} = {_f(t['effect_size'])} | "
                     f"{'Sí' if t['reject_h0'] else 'No'} |")
    lines += ["", (f"**H₀a {'se rechaza' if result['h1a']['h0_rechazada'] else 'no se rechaza'}** "
              "(se rechaza solo si las cuatro métricas superan significativamente el umbral)."), ""]

    acc = result["exactitud_abstencion"]
    lines += ["## Exactitud de abstención", "",
              f"{_f(acc['valor'] * 100, 1)} % de decisiones correctas sobre {acc['n_preguntas']} preguntas.", ""]

    lat = result["latencia_prototipo"]
    if lat:
        lines += ["## Latencia del prototipo (segundos, media por pregunta respondible)", "",
                  "| n | Media | DE | Mediana | Q1 | Q3 | Mín. | Máx. |", "|---|---|---|---|---|---|---|---|",
                  (f"| {lat['n']} | {_f(lat['mean'], 2)} | {_f(lat['sd'], 2)} | {_f(lat['median'], 2)} | "
                  f"{_f(lat['q1'], 2)} | {_f(lat['q3'], 2)} | {_f(lat['minimum'], 2)} | {_f(lat['maximum'], 2)} |"), ""]

    if result["encuesta"] is None:
        lines += ["_Sin datos de encuesta: H₁b y H₁c quedan pendientes. Ejecuta de nuevo con --encuesta._", ""]
        return "\n".join(lines)

    enc = result["encuesta"]
    tm = enc["tiempo_manual_minutos"]
    lines += ["## Encuesta", "",
              (f"Respuestas recibidas: {enc['respuestas']}; con al menos una consulta previa: "
               f"{enc['con_consulta_previa']}; tiempos válidos: {enc['respuestas_tiempo_validas']}; "
               f"«Aún no he recibido respuesta»: {enc['sin_respuesta_aun']} (se reportan aparte)."), ""]
    if tm:
        lines += [(f"Tiempo de atención manual reportado: media {_f(tm['mean'], 1)} min, "
                  f"mediana {_f(tm['median'], 1)} min (Q1 {_f(tm['q1'], 1)}, Q3 {_f(tm['q3'], 1)})."), ""]
    lines += [(f"Alfa de Cronbach — utilidad: {_f(enc['alfa_cronbach_utilidad'])}; "
              f"facilidad de uso: {_f(enc['alfa_cronbach_facilidad'])} (aceptable ≥ 0.70)."), ""]
    if enc["facilidad_de_uso"]:
        fu = enc["facilidad_de_uso"]
        lines += [(f"Facilidad de uso percibida (descriptiva): media {_f(fu['mean'], 2)}, "
                  f"DE {_f(fu['sd'], 2)}, mediana {_f(fu['median'], 2)}."), ""]

    for key, title in (("h1b", "H₁b — Latencia frente a la atención manual"),
                       ("h1b_sensibilidad", "H₁b — Sensibilidad con el límite inferior de cada rango"),
                       ("h1c", "H₁c — Utilidad percibida")):
        t = result.get(key)
        if not t:
            continue
        lines += [f"## {title}", "",
                  f"- Prueba: {t['test']} (normalidad Shapiro-Wilk, p mínimo = {_p(t['normality_p'])})",
                  (f"- Estadístico = {_f(t['statistic'])}; p = {_p(t['p_value'])}; "
                  f"{t['effect_size_name']} = {_f(t['effect_size'])}"),
                  f"- **H₀{'b' if key.startswith('h1b') else key[-1]} {'se rechaza' if t['reject_h0'] else 'no se rechaza'}**", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Análisis estadístico de la Fase V")
    parser.add_argument("--reporte", type=Path, default=Path(__file__).parent / "evaluation_report.json")
    parser.add_argument("--encuesta", type=Path, default=None, help="CSV o Excel exportado del formulario")
    parser.add_argument("--umbral", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--neutral", type=float, default=DEFAULT_NEUTRAL)
    parser.add_argument("--alpha", type=float, default=DEFAULT_ALPHA)
    parser.add_argument("--salida", type=Path, default=Path(__file__).parent / "resultados")
    args = parser.parse_args()

    report = load_report(args.reporte)
    survey = load_survey(args.encuesta) if args.encuesta else None
    result = analyze(report, survey, args.umbral, args.neutral, args.alpha)

    args.salida.mkdir(parents=True, exist_ok=True)
    (args.salida / "resultados.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    markdown = to_markdown(result)
    (args.salida / "resultados.md").write_text(markdown, encoding="utf-8")
    print(markdown)
    print(f"\nArchivos guardados en {args.salida}/")


if __name__ == "__main__":
    main()
