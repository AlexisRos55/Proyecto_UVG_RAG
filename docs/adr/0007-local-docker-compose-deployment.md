# ADR-0007: Docker Compose local como único objetivo de despliegue

**Estado:** Aceptado

**Fecha:** 2026-09-02

## Contexto

El asesor exige Docker y Docker Compose como mecanismo de empaquetado. Falta definir dónde se ejecuta ese Docker Compose: en infraestructura propia de UVG Altiplano, en un servicio cloud gestionado por el equipo, o localmente en el equipo del desarrollador. El proyecto tiene un plazo de 3 semanas y un solo desarrollador con ~1 hora diaria disponible.

## Decisión

El objetivo de despliegue para esta versión del proyecto es exclusivamente una demo local ejecutada mediante `docker compose up` en la máquina del equipo de desarrollo, usada para la defensa de tesis. No se despliega en infraestructura de UVG ni en un proveedor cloud.

## Alternativas consideradas

| Alternativa | Ventajas | Desventajas | Por qué se descartó |
|---|---|---|---|
| Infraestructura propia de UVG Altiplano | Escenario más realista de cara a una eventual adopción institucional | Depende de que la universidad provea y configure un servidor, y de coordinación con su equipo de TI — fuera del control y del plazo del equipo de tesis | Riesgo de bloqueo total del proyecto si la infraestructura no está disponible a tiempo |
| VPS o cloud público gestionado por el equipo | Acceso remoto real, demostrable desde cualquier lugar | Costo recurrente (contradice el presupuesto personal limitado) y superficie de ataque adicional (exposición pública) que el equipo tendría que asegurar sin tiempo dedicado a ello | Añade riesgo de seguridad y costo sin necesidad real para el objetivo de la tesis (defensa ante un tribunal presencial o remoto controlado) |
| Docker Compose local (elegida) | Sin costo recurrente, sin dependencias externas, control total del entorno de demostración, cumple igualmente el requisito de "empaquetado reproducible" del asesor | No demuestra un despliegue accesible públicamente ni bajo carga real | — |

## Consecuencias

**Positivas:**
- Cero riesgo de dependencia externa fuera del control del equipo durante las 3 semanas de desarrollo.
- Sigue cumpliendo el requisito literal del asesor: el sistema se empaqueta y ejecuta con Docker y Docker Compose.

**Negativas / trade-offs aceptados:**
- Los NFR de disponibilidad, backup y seguridad de red se redactan para un entorno de demo controlado (ver `03-non-functional-requirements.md`), no para un entorno productivo — se documenta explícitamente para que no se interprete como omisión.
- Si la universidad decide adoptar el sistema después de la tesis, el despliegue en infraestructura real es trabajo futuro no cubierto por esta versión.

## Cómo se ajusta a las restricciones del proyecto

Es la decisión más directamente alineada con el plazo de 3 semanas y el hecho de que el equipo es un solo desarrollador: elimina toda dependencia de terceros (UVG, un proveedor cloud) para poder cumplir la fecha de defensa de tesis.
