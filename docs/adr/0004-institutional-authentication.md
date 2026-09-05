# ADR-0004: Autenticación institucional simple (correo `@uvg.edu.gt`), sin SSO

**Estado:** Aceptado

**Fecha:** 2026-09-02

## Contexto

El asistente responde sobre normativa, beneficios y seguros asociados a estudiantes; dejar el acceso completamente abierto no es defendible para un sistema institucional, pero implementar una integración SSO real con el proveedor de identidad de UVG requiere coordinación institucional (acceso a un IdP, credenciales de integración, aprobación de TI) que está fuera del control de un equipo de tesis de una persona con 3 semanas de plazo.

## Decisión

Se implementa un módulo de autenticación propio dentro del backend: registro/login con correo institucional (`@uvg.edu.gt`) y contraseña (hash, nunca texto plano), con sesión emitida por el propio sistema. No se integra con el proveedor de identidad institucional de UVG.

## Alternativas consideradas

| Alternativa | Ventajas | Desventajas | Por qué se descartó |
|---|---|---|---|
| SSO institucional real (SAML/OIDC contra el IdP de UVG) | Máxima coherencia con la identidad institucional real; ningún estudiante crea una contraseña nueva | Depende de que UVG exponga y autorice el uso de su proveedor de identidad; requiere coordinación externa al equipo de tesis, con riesgo de bloqueo total del proyecto si no se obtiene a tiempo | Riesgo de bloqueo inaceptable dado el plazo de 3 semanas; no es una decisión que el equipo pueda garantizar por sí solo |
| Sin autenticación (acceso abierto) | Cero tiempo de implementación | Sin trazabilidad por usuario, sin historial de conversación por cuenta, y sin control de acceso a un sistema que trata información institucional sensible | Contradice NFR-04 (seguridad) y el objetivo de "diseño empresarial" |
| Autenticación propia con validación de dominio institucional (elegida) | Controlable enteramente por el equipo, sin dependencias externas; suficiente para demostrar el patrón de autenticación y autorización (rol `admin` vs `estudiante`) en la arquitectura | No es la identidad "oficial" de UVG; un estudiante podría registrarse con cualquier corrreo que termine en `@uvg.edu.gt` sin verificación de que existe realmente (no hay verificación de correo en el MVP, ver `07-backlog.md`) | — |

## Consecuencias

**Positivas:**
- El sistema controla completamente su ciclo de autenticación, sin riesgo de bloqueo por terceros.
- Permite implementar y demostrar el puerto `AuthPort` y el control de acceso por rol (`estudiante` / `admin`) requerido por el panel administrativo.

**Negativas / trade-offs aceptados:**
- No hay verificación real de que el correo pertenezca a un estudiante activo de UVG (se documenta como limitación conocida, no como descuido, en `09-risk-register.md`).
- Es responsabilidad del equipo implementar correctamente el hash de contraseñas y el manejo de sesión (mitigado por NFR-04).

## Cómo se ajusta a las restricciones del proyecto

Esta decisión evita una dependencia externa que el equipo no controla (coordinación con TI de UVG) dentro de un plazo de 3 semanas, sin renunciar al requisito de tener control de acceso razonable para un sistema institucional. No modifica el alcance funcional definido por el asesor, que no especifica ningún mecanismo de autenticación.
