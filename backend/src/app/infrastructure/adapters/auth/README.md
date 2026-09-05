# infrastructure/adapters/auth

Implementación concreta de `AuthPort`: autenticación institucional simple con correo `@uvg.edu.gt` y contraseña, sin integración SSO (ver [ADR-0004](../../../../../../docs/adr/0004-institutional-authentication.md)).

Previsto: `InstitutionalAuthAdapter` — valida credenciales contra `PostgresUserRepository`, aplica hash de contraseña (no texto plano, ver NFR-04 en `docs/03-non-functional-requirements.md`), y emite/valida el token de sesión usado por el middleware de la API.
