"""Advertencias sobre tablas cuya información no sobrevive a la extracción de texto.

En el reglamento de ayudas financieras, las tablas de requisitos, condiciones y
penalizaciones indican **con marcas gráficas vectoriales** a qué programa aplica
cada fila. Esas marcas no son texto: la extracción conserva los encabezados de
columna y el texto de cada fila, pero no la correspondencia entre ambos. Sin
advertirlo, un modelo generativo tiende a completar la matriz y afirma, por
ejemplo, que todos los requisitos aplican a todas las becas (observado en la
prueba en vivo de la Fase 9). La advertencia viaja en el propio fragmento, que es
lo único que el modelo ve.
"""

from __future__ import annotations

import re

# Un encabezado de matriz enumera varias columnas con nombre propio en una sola línea.
_COLUMN_HEADER = re.compile(
    r"\b(?:Beca|Programa|Crédito|Liderazgo|Patrocinador|Olimpiada|Trasciende|Despega|Transforma|AVE"
    r"|Apoyo\s+Especial|Juan\s+Bautista|Potencia)\b"
)
_MIN_COLUMNS = 5

# Breve a propósito: se añade a cada pieza de la tabla y cuenta contra el presupuesto de contexto.
MATRIX_NOTICE = "[Tabla: sus marcas por programa no se conservan; no se sabe qué fila aplica a qué programa.]"


def has_matrix_header(text: str) -> bool:
    return any(len(_COLUMN_HEADER.findall(line)) >= _MIN_COLUMNS for line in text.splitlines())


def annotate_matrix_tables(text: str) -> str:
    if MATRIX_NOTICE in text or not has_matrix_header(text):
        return text
    return f"{text}\n{MATRIX_NOTICE}"


def annotate_matrix_units(texts: list[str], unit_keys: list[str]) -> list[str]:
    """Anota todas las piezas de una unidad (artículo) cuya tabla perdió las marcas.

    Una tabla larga se parte en varias piezas y solo la primera conserva la fila de
    encabezados; las filas siguientes («…promedio mínimo de 65 puntos») quedarían
    sin advertencia y el modelo podría atribuirlas a todos los programas.
    """
    lossy_units = {key for text, key in zip(texts, unit_keys, strict=True) if has_matrix_header(text)}
    return [
        f"{text}\n{MATRIX_NOTICE}" if key in lossy_units and MATRIX_NOTICE not in text else text
        for text, key in zip(texts, unit_keys, strict=True)
    ]
