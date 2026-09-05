"""Genera un corpus de documentos de ejemplo para poder ejecutar la ingesta y la evaluación
RAGAS sin depender de los documentos oficiales reales de UVG Altiplano (que el asesor no
entregó junto con la especificación funcional, ver Project Charter, sección 7 - Supuestos).

Este contenido es FICTICIO, con fines de demostración y prueba del pipeline. Antes de una
demo real ante el asesor o el tribunal, debe reemplazarse por los documentos institucionales
reales a través del panel administrativo o de scripts/ingest.py.

Genera los PDF directamente en backend/documents/: el backend los indexa automáticamente al
arrancar (ver app/infrastructure/bootstrap.py, sprint 1 demo), sin pasos manuales adicionales.
"""

from __future__ import annotations

from pathlib import Path

import pymupdf

OUTPUT_DIR = Path(__file__).parent.parent / "backend" / "documents"

DOCUMENTS: dict[str, str] = {
    "reglamento_estudiantil.pdf": """Reglamento Estudiantil de UVG Altiplano (documento de ejemplo)

Articulo 1. Reincorporacion.
El estudiante que haya interrumpido sus estudios debera solicitar su reincorporacion en la
oficina de Registro Academico, presentando su solicitud por escrito con al menos 30 dias de
anticipacion al inicio del ciclo academico correspondiente.

Articulo 5. Retiro de curso.
El estudiante podra retirar un curso dentro de un plazo maximo de 6 semanas despues de
iniciado el semestre, siempre que cuente con la autorizacion escrita del coordinador de su
carrera.

Articulo 9. Asistencia.
Para tener derecho a presentar el examen final de un curso, el estudiante debe acreditar un
minimo de 80% de asistencia a las sesiones de clase.
""",
    "becas_y_beneficios.pdf": """Becas y Beneficios Estudiantiles - UVG Altiplano (documento de ejemplo)

Beca de Excelencia Academica.
Cubre hasta el 50% del valor de la colegiatura. Para mantenerla, el estudiante debe conservar
un indice academico minimo de 85 puntos y se renueva semestre a semestre.

Beca Deportiva.
Cubre hasta el 30% del valor de la colegiatura para estudiantes que representen oficialmente
a la universidad en competencias deportivas interuniversitarias.

Beneficio de pronto pago.
El estudiante que pague su colegiatura dentro de los primeros 10 dias del mes obtiene un 5%
de descuento sobre el monto correspondiente.
""",
    "seguro_estudiantil.pdf": """Seguro Estudiantil - UVG Altiplano (documento de ejemplo)

Cobertura.
Todo estudiante inscrito cuenta con un seguro medico basico que cubre accidentes ocurridos
dentro del campus universitario durante el horario academico.

Exclusiones.
El seguro no cubre enfermedades preexistentes ni accidentes ocurridos fuera de las
instalaciones del campus.

Procedimiento de reporte.
Para hacer valida la cobertura, el estudiante debe reportar el incidente a la Clinica
Estudiantil dentro de las 24 horas siguientes a haber ocurrido.
""",
}


def generate() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for filename, text in DOCUMENTS.items():
        document = pymupdf.open()
        page = document.new_page()
        page.insert_text((72, 72), text, fontsize=11)
        destination = OUTPUT_DIR / filename
        document.save(destination)
        document.close()
        print(f"Generado: {destination}")


if __name__ == "__main__":
    generate()
