# shared/exceptions

Jerarquía de excepciones de dominio, independiente de cualquier librería externa:

- `DomainError` (base)
- `NotFoundError`
- `VerificationFailedError`
- `InvalidCredentialsError`
- `UnauthorizedError`

Regla: los adaptadores capturan excepciones específicas de su tecnología (p. ej. `anthropic.APIError`, `sqlalchemy.exc.IntegrityError`) y las traducen a una excepción de esta jerarquía antes de propagarlas hacia `application`. Ni `domain` ni `application` conocen excepciones de librerías externas — de lo contrario, cambiar de proveedor también obligaría a cambiar el manejo de errores del núcleo del negocio (ver `docs/04-software-architecture.md`, sección 4).
